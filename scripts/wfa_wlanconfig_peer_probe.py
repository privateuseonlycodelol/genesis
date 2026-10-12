#!/usr/bin/env python3
"""One GetDeviceInfo peer, then bounded PutMessage state probes on :49152.

Allocates a single WPS peer via GetDeviceInfo, sends one parseable but
state-invalid PutMessage (M1 with matching enrollee nonce while peer expects M2),
then one no-peer PutMessage control. No PIN, M2/M2D completion, registrar
subscription, or event SUBSCRIBE. Nonces and raw WPS bytes stay private.
"""
import argparse
import base64
import binascii
import hashlib
import json
import os
import struct
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import wfa_wlanconfig_probe as surface
import wps_device_info as wps

HOST = surface.HOST
PORT = surface.PORT
SERVICE = surface.SERVICE
GET_DEVICE_SOAP = wps.SOAP
PAUSE = 3


def wps_tlv(kind, value):
    return struct.pack("!HH", kind, len(value)) + value


def enrollee_nonce_from_get_device_info(body):
    parsed = wps.parse_soap(body)
    if parsed.get("soap_fault"):
        raise ValueError("GetDeviceInfo returned SOAP fault")
    root = ET.fromstring(body)
    infos = [e for e in root.iter() if e.tag.split("}")[-1] == "NewDeviceInfo"]
    if len(infos) != 1:
        raise ValueError("expected one NewDeviceInfo")
    payload = base64.b64decode("".join((infos[0].text or "").split()), validate=True)
    values = {}
    offset = 0
    while offset < len(payload):
        kind, length = struct.unpack_from("!HH", payload, offset)
        offset += 4
        value = payload[offset : offset + length]
        offset += length
        values.setdefault(kind, []).append(value)
    nonce = values.get(0x101a, [None])[0]
    if nonce is None or len(nonce) != 16:
        raise ValueError("missing enrollee nonce in M1")
    return nonce


def wrong_state_m1(nonce):
    """Parseable WPS shell: Version + M1 type + enrollee nonce (wrong in RECV_M2)."""
    return wps_tlv(0x104a, b"\x10") + wps_tlv(0x1022, b"\x04") + wps_tlv(0x101a, nonce)


def put_message_inner(b64_payload):
    return (
        f'<u:PutMessage xmlns:u="{SERVICE}">'
        f"<NewInMessage>{b64_payload}</NewInMessage></u:PutMessage>"
    )


def post_put_message(directory, index, probe, note, inner_xml, pause):
    body_file = directory / f"request-{index:02d}.private.xml"
    body_file.write_bytes(surface.soap_body("PutMessage", inner_xml))
    row = {
        "probe": probe,
        "method": "POST",
        "url": f"http://{HOST}:{PORT}/wps_control",
        "headers": (
            'Content-Type: text/xml; charset="utf-8"',
            f'SOAPAction: "{SERVICE}#PutMessage"',
        ),
        "body_file": body_file,
        "note": note,
    }
    return surface.curl_step(directory, index, row, pause)


def live():
    os.umask(0o077)
    directory = ROOT / "artifacts" / "management" / (
        "wfa-peer-" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    )
    directory.mkdir(parents=True, exist_ok=False)
    rows = []
    index = 0

    index += 1
    (directory / "request-get-device-info.private.xml").write_bytes(GET_DEVICE_SOAP)
    row = {
        "probe": "GetDeviceInfo",
        "method": "POST",
        "url": f"http://{HOST}:{PORT}/wps_control",
        "headers": (
            'Content-Type: text/xml; charset="utf-8"',
            f'SOAPAction: "{SERVICE}#GetDeviceInfo"',
        ),
        "body_file": directory / "request-get-device-info.private.xml",
        "note": "allocates one UPnP WPS peer (M1)",
    }
    summary, exit_code, status = surface.curl_step(directory, index, row, False)
    rows.append(summary)
    surface._write_summary(directory, rows)
    print(json.dumps(summary), flush=True)
    if exit_code or status == 503 or status != 200:
        return 1, directory

    body = (directory / "response-01.body.private").read_bytes()
    try:
        nonce = enrollee_nonce_from_get_device_info(body)
        wps_meta = wps.parse_soap(body)
    except (ValueError, ET.ParseError, binascii.Error) as error:
        print(f"GetDeviceInfo parse failed: {error}", flush=True)
        return 1, directory
    summary["enrollee_nonce_sha256"] = hashlib.sha256(nonce).hexdigest()
    summary["m1_message_type"] = wps_meta.get("message_type_byte")
    surface._write_summary(directory, rows)
    print(json.dumps({k: summary[k] for k in summary if k != "sha256"}), flush=True)

    wrong = wrong_state_m1(nonce)
    b64_wrong = base64.b64encode(wrong).decode()
    index += 1
    summary, exit_code, status = post_put_message(
        directory,
        index,
        "PutMessage-wrong-M1-matched-nonce",
        "parseable M1 with enrollee nonce while peer expects M2",
        put_message_inner(b64_wrong),
        True,
    )
    summary["wps_in_bytes"] = len(wrong)
    summary["wps_in_sha256"] = hashlib.sha256(wrong).hexdigest()
    rows.append(summary)
    surface._write_summary(directory, rows)
    print(json.dumps(summary), flush=True)
    if exit_code or status == 503:
        return 1, directory

    index += 1
    summary, exit_code, status = post_put_message(
        directory,
        index,
        "PutMessage-no-peer-control",
        "one-byte NewInMessage after peer teardown",
        put_message_inner("AA=="),
        True,
    )
    rows.append(summary)
    surface._write_summary(directory, rows)
    print(json.dumps(summary), flush=True)
    if exit_code or status == 503:
        return 1, directory

    print("Completed peer-state probe; private evidence: " + str(directory), flush=True)
    return 0, directory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    return live()[0]


if __name__ == "__main__":
    raise SystemExit(main())
