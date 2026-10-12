#!/usr/bin/env python3
"""Parse WPS GetDeviceInfo evidence, or make one explicit --live information read.

GetDeviceInfo may allocate transient WPS registration state. This tool never
sends M2, a PIN, credentials, registrar selection, subscriptions, or completion.
Raw XML/base64/WPS values stay in ignored private artifacts.
"""
import argparse
import base64
import binascii
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SERVICE = 'urn:schemas-wifialliance-org:service:WFAWLANConfig:1'
SOAP = ('<?xml version="1.0"?>'
        '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
        's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
        '<s:Body><u:GetDeviceInfo xmlns:u="' + SERVICE + '"/>'
        '</s:Body></s:Envelope>').encode()


def parse_tlvs(data):
    attributes = []
    values = {}
    offset = 0
    while offset < len(data):
        if len(data) - offset < 4:
            raise ValueError('truncated WPS attribute header')
        kind, length = struct.unpack_from('!HH', data, offset)
        offset += 4
        if length > len(data) - offset:
            raise ValueError('truncated WPS attribute value')
        value = data[offset:offset + length]
        attributes.append({'type': f'0x{kind:04x}', 'length': length})
        values.setdefault(kind, []).append(value)
        offset += length
    for kind in (0x104a, 0x1022, 0x101a, 0x1032):
        if len(values.get(kind, [])) > 1:
            raise ValueError('duplicate critical WPS attribute')
    version = values.get(0x104a, [b''])[0]
    message = values.get(0x1022, [b''])[0]
    nonce = values.get(0x101a, [b''])[0]
    public_key = values.get(0x1032, [b''])[0]
    return {'wps_bytes': len(data), 'attributes': attributes,
            'version_byte': version[0] if len(version) == 1 else None,
            'message_type_byte': message[0] if len(message) == 1 else None,
            'm1_core_structure': (version == b'\x10' and message == b'\x04'
                                  and len(nonce) == 16 and len(public_key) == 192)}


def parse_soap(body):
    root = ET.fromstring(body)
    if root.tag != '{http://schemas.xmlsoap.org/soap/envelope/}Envelope':
        raise ValueError('expected SOAP 1.1 envelope')
    infos = [e for e in root.iter() if e.tag.split('}')[-1] == 'NewDeviceInfo']
    faults = [e for e in root.iter() if e.tag.split('}')[-1] == 'Fault']
    if faults:
        codes = [e.text for e in root.iter() if e.tag.split('}')[-1] == 'errorCode']
        return {'soap_fault': True, 'upnp_error_code': int(codes[0])
                if len(codes) == 1 and (codes[0] or '').isdigit() else None}
    if len(infos) != 1:
        raise ValueError('expected exactly one NewDeviceInfo element')
    if not any(e.tag == '{' + SERVICE + '}GetDeviceInfoResponse' for e in root.iter()):
        raise ValueError('expected WFA GetDeviceInfoResponse')
    encoded = ''.join((infos[0].text or '').split())
    decoded = base64.b64decode(encoded, validate=True)
    return {'soap_fault': False, **parse_tlvs(decoded)}


def live():
    os.umask(0o077)
    directory = ROOT / 'artifacts/management' / ('wps-info-' + time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()))
    directory.mkdir(parents=True, exist_ok=False)
    (directory / 'request.private.xml').write_bytes(SOAP)
    rows = []
    # Positive transport/description control first, then exactly one action.
    for index, path in enumerate(('/wps_scpd.xml', '/wps_control'), 1):
        if index > 1:
            time.sleep(3)
        prefix = directory / f'response-{index:02d}'
        cmd = ['curl', '--noproxy', '*', '--silent', '--show-error', '--connect-timeout', '4',
               '--max-time', '12', '--max-filesize', '1048576', '--dump-header',
               str(prefix) + '.headers.private', '--output', str(prefix) + '.body.private',
               '--write-out', '%{http_code}']
        if index == 2:
            cmd += ['--header', 'Content-Type: text/xml; charset="utf-8"',
                    '--header', 'SOAPAction: "' + SERVICE + '#GetDeviceInfo"',
                    '--data-binary', '@' + str(directory / 'request.private.xml')]
        cmd.append('http://192.168.2.1:49152' + path)
        result = subprocess.run(cmd, capture_output=True)
        file = Path(str(prefix) + '.body.private')
        body = file.read_bytes() if file.exists() else b''
        row = {'request': index, 'path': path, 'status': int(result.stdout.strip() or b'0'),
               'curl_exit': result.returncode, 'bytes': len(body),
               'sha256': hashlib.sha256(body).hexdigest()}
        rows.append(row)
        (directory / 'summary.json').write_text(json.dumps(rows, indent=2) + '\n')
        if result.returncode or row['status'] == 503:
            print(json.dumps(row)); print('Stopped; private evidence: ' + str(directory))
            return 1
        if index == 1 and row['status'] != 200:
            print(json.dumps(row)); print('Description control failed; no action sent')
            return 1
        if index == 1:
            try:
                description = ET.fromstring(body)
                valid = (description.tag == '{urn:schemas-upnp-org:service-1-0}scpd'
                         and any(e.tag.split('}')[-1] == 'name' and e.text == 'GetDeviceInfo'
                                 for e in description.iter()))
            except ET.ParseError:
                valid = False
            if not valid:
                print(json.dumps(row)); print('Description content failed; no action sent')
                return 1
        if index == 2:
            try:
                row.update(parse_soap(body))
            except (ValueError, ET.ParseError, binascii.Error):
                row['parse_error'] = True
        (directory / 'summary.json').write_text(json.dumps(rows, indent=2) + '\n')
        print(json.dumps(row), flush=True)
    print('Private evidence: ' + str(directory))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--soap-response', type=Path)
    args = parser.parse_args()
    if args.live == bool(args.soap_response):
        parser.error('choose exactly one of --live or --soap-response')
    if args.live:
        return live()
    print(json.dumps(parse_soap(args.soap_response.read_bytes()), indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
