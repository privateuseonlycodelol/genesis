#!/usr/bin/env python3
"""Paced, unauthenticated CUPS write-side IPP policy probe on the owned F1.

Purpose: with the CORRECT CUPS opcode map (0x4003 = CUPS-Add-Modify-Printer,
0x4005 = CUPS-Get-Classes, 0x400A = CUPS-Set-Default, 0x0008 = Cancel-Job, ...),
probe state-changing operations against NONEXISTENT resources. Policy checks
vs. resource lookups produce distinguishable status codes (forbidden vs
not-found), which maps the auto-created policy's anonymous write-tail without
changing device state.

No credentials, no cookies. Every target is a nonexistent printer/job. Output
is metadata + raw responses to a private artifacts dir.
"""
import struct
import time
from pathlib import Path
import http.client

HOST = "192.168.1.1"
PORT = 631
PACING_SEC = 3.0
OUT = Path(__file__).resolve().parents[1] / "artifacts" / "cups-writeside-2026-11-07"
OUT.mkdir(parents=True, exist_ok=True)

URI = f"ipp://{HOST}:{PORT}/printers/genesis-nonexistent-probe"
URI_ROOT = f"ipp://{HOST}:{PORT}/"

IPP_TAG_OPERATION, IPP_TAG_END = 0x01, 0x03
IPP_TAG_CHARSET, IPP_TAG_LANGUAGE, IPP_TAG_URI = 0x47, 0x48, 0x45
IPP_TAG_INTEGER, IPP_TAG_KEYWORD, IPP_TAG_NAME = 0x21, 0x44, 0x42

STATUS = {
    0x0000: "successful-ok", 0x0400: "client-error-bad-request",
    0x0401: "client-error-forbidden", 0x0403: "client-error-not-found",
    0x0404: "client-error-not-found-alt", 0x0405: "client-error-not-possible",
    0x0406: "client-error-not-found-cups", 0x0408: "client-error-request-value",
    0x0409: "client-error-not-found-resource", 0x0410: "client-error-not-found-destination",
    0x0500: "server-error-internal", 0x0501: "server-error-operation-not-supported",
    0x0503: "server-error-version-not-supported",
}


def sattr(tag, name, value):
    nb, vb = name.encode(), str(value).encode()
    return bytes([tag]) + struct.pack(">H", len(nb)) + nb + struct.pack(">H", len(vb)) + vb


def iattr(name, value):
    nb = name.encode()
    return bytes([IPP_TAG_INTEGER]) + struct.pack(">H", len(nb)) + nb + struct.pack(">Hi", 4, int(value))


def build(op, attrs=(), rid=0x2468ace0):
    parts = [b"\x01\x01", struct.pack(">H", op), struct.pack(">I", rid),
             bytes([IPP_TAG_OPERATION]),
             sattr(IPP_TAG_CHARSET, "attributes-charset", "utf-8"),
             sattr(IPP_TAG_LANGUAGE, "attributes-natural-language", "en")]
    for name, value, tag in attrs:
        parts.append(iattr(name, value) if tag == IPP_TAG_INTEGER else sattr(tag, name, value))
    parts.append(bytes([IPP_TAG_END]))
    return b"".join(parts)


# Correct CUPS/IPP opcodes (public cups/ipp.h, stable since 1.x):
PROBES = [
    # (label, opcode, attrs)  -- all targets nonexistent
    ("Cancel-Job(job-id=999)", 0x0008, (("printer-uri", URI, IPP_TAG_URI), ("job-id", 999, IPP_TAG_INTEGER))),
    ("Hold-Job(job-id=999)", 0x000C, (("printer-uri", URI, IPP_TAG_URI), ("job-id", 999, IPP_TAG_INTEGER))),
    ("Release-Job(job-id=999)", 0x000D, (("printer-uri", URI, IPP_TAG_URI), ("job-id", 999, IPP_TAG_INTEGER))),
    ("Cancel-Jobs(all)", 0x0033, (("printer-uri", URI, IPP_TAG_URI),)),  # IPP_OP_CANCEL_JOBS
    ("Pause-Printer", 0x0010, (("printer-uri", URI, IPP_TAG_URI),)),
    ("Resume-Printer", 0x0011, (("printer-uri", URI, IPP_TAG_URI),)),
    ("Purge-Jobs", 0x0012, (("printer-uri", URI, IPP_TAG_URI),)),
    ("Set-Printer-Attributes", 0x0013, (("printer-uri", URI, IPP_TAG_URI), ("printer-location", "x", IPP_TAG_KEYWORD))),
    ("Validate-Job", 0x0004, (("printer-uri", URI, IPP_TAG_URI),)),
    ("Create-Job", 0x0005, (("printer-uri", URI, IPP_TAG_URI),)),
    ("CUPS-Add-Modify-Printer(no device-uri)", 0x4003, (("printer-uri", URI, IPP_TAG_URI),)),
    ("CUPS-Delete-Printer", 0x4004, (("printer-uri", URI, IPP_TAG_URI),)),
    ("CUPS-Get-Classes(real)", 0x4005, (("requested-attributes", "printer-state", IPP_TAG_KEYWORD),)),
    ("CUPS-Add-Modify-Class", 0x4006, (("printer-uri", URI_ROOT + "classes/genesis-nonexistent-probe", IPP_TAG_URI),)),
    ("CUPS-Delete-Class", 0x4007, (("printer-uri", URI_ROOT + "classes/genesis-nonexistent-probe", IPP_TAG_URI),)),
    ("CUPS-Accept-Jobs", 0x4008, (("printer-uri", URI, IPP_TAG_URI),)),
    ("CUPS-Reject-Jobs", 0x4009, (("printer-uri", URI, IPP_TAG_URI),)),
    ("CUPS-Set-Default", 0x400A, (("printer-uri", URI, IPP_TAG_URI),)),
    ("CUPS-Move-Job", 0x400D, (("printer-uri", URI, IPP_TAG_URI), ("job-id", 999, IPP_TAG_INTEGER),
                                ("job-printer-uri", URI + "-other", IPP_TAG_URI))),
    ("CUPS-Authenticate-Job", 0x400E, (("printer-uri", URI, IPP_TAG_URI), ("job-id", 999, IPP_TAG_INTEGER))),
    ("CUPS-Get-PPDs(real, never probed)", 0x400C, ()),
    ("CUPS-Get-Document(job 999)", 0x4027, (("printer-uri", URI, IPP_TAG_URI), ("job-id", 999, IPP_TAG_INTEGER),
                                             ("document-number", 1, IPP_TAG_INTEGER))),
]


def main():
    print(f"probing {len(PROBES)} ops against {HOST}:{PORT}, {PACING_SEC}s pacing")
    results = []
    for i, (label, op, attrs) in enumerate(PROBES):
        body = build(op, attrs)
        try:
            conn = http.client.HTTPConnection(HOST, PORT, timeout=10)
            conn.request("POST", "/", body=body,
                         headers={"Content-Type": "application/ipp", "Content-Length": str(len(body))})
            resp = conn.getresponse()
            rbody = resp.read()
            conn.close()
        except Exception as e:
            print(f"  [{i+1}/{len(PROBES)}] {label}: ERROR {e}")
            results.append((label, op, -1, f"error: {e}"))
            time.sleep(PACING_SEC)
            continue
        status = struct.unpack(">H", rbody[2:4])[0] if len(rbody) >= 4 else -1
        # crude message text extraction
        msg = ""
        try:
            j = rbody.index(b"attributes-natural-language\x00") if b"attributes-natural-language" in rbody else -1
            text = rbody[rbody.index(b"status-message"):] if b"status-message" in rbody else rbody
            msg = text[40:120].decode("latin1", "replace").split("\x00")[0]
        except Exception:
            pass
        sname = STATUS.get(status, f"unknown-{status:#x}")
        print(f"  [{i+1}/{len(PROBES)}] {label}: HTTP {resp.status} IPP {sname} {msg!r}")
        results.append((label, op, status, msg))
        (OUT / f"probe-{op:04x}.bin").write_bytes(rbody)
        time.sleep(PACING_SEC)
    # summary table
    print("\npolicy interpretation (forbidden=policy-denied; not-found/bad-request=policy passed, resource missing):")
    for label, op, status, msg in results:
        verdict = "POLICY-DENIED" if status == 0x0401 else ("policy-passed" if status in (0x0400, 0x0403, 0x0404, 0x0405, 0x0406, 0x0408, 0x0409, 0x0410, 0x0500) else f"check:{status:#x}")
        print(f"  {label:45s} {verdict}")
    Path(OUT / "summary.txt").write_text("\n".join(f"{l}\t{o:#x}\t{s:#x}\t{m}" for l, o, s, m in results))


if __name__ == "__main__":
    main()
