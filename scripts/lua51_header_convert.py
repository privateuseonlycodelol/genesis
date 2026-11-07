#!/usr/bin/env python3
"""Convert Telia F1 (32-bit) Lua 5.1 precompiled chunks to 64-bit-host format.

The F1 (OpenWrt 21.02, arm 32-bit) Lua 5.1.5 runtime emits chunks with
sizeof(size_t)=4 and a non-standard integral flag byte (0x04) in the header.
A 64-bit host luac 5.1.5 expects sizeof(size_t)=8 and integral flag 0.

This rewrites every string size field (header source + constant strings +
debug names) from 4-byte to 8-byte size_t and fixes the header, producing a
chunk a stock 64-bit luac 5.1.5 can `luac -l -l` list.

Usage: lua51_header_convert.py <in.lua> <out.luac>
"""
import struct
import sys


class R:
    def __init__(self, data):
        self.d = data
        self.p = 0

    def b(self):
        v = self.d[self.p]
        self.p += 1
        return v

    def i32(self):
        v = struct.unpack_from("<I", self.d, self.p)[0]
        self.p += 4
        return v

    def raw(self, n):
        v = self.d[self.p:self.p + n]
        self.p += n
        return v

    def str4(self):
        n = self.i32()
        if n == 0:
            return None
        return self.raw(n)


class W:
    def __init__(self):
        self.b = bytearray()

    def b_(self, v):
        self.b.append(v)

    def i32(self, v):
        self.b += struct.pack("<I", v)

    def raw(self, v):
        self.b += v

    def str8(self, v):
        if v is None:
            self.i32(0)
            self.b += b"\x00" * 4
        else:
            self.i32(len(v))
            self.b += b"\x00" * 4
            self.b += v


def conv_func(r, w):
    w.str8(r.str4())            # source (top-level only in 5.1; nested carry it too)
    w.i32(r.i32())              # linedefined
    w.i32(r.i32())              # lastlinedefined
    w.b_(r.b())                 # nups
    w.b_(r.b())                 # numparams
    w.b_(r.b())                 # is_vararg
    w.b_(r.b())                 # maxstacksize
    n = r.i32()                 # instruction count
    w.i32(n)
    w.raw(r.raw(4 * n))
    n = r.i32()                 # constant count
    w.i32(n)
    for _ in range(n):
        tag = r.b()
        # Telia F1 uses Lua 5.1.5 + LNUM patch: integral constants are
        # int32 with tag 9 (8 bytes: value + zero pad); doubles use
        # stock tag 3; strings tag 4; boolean tag 1; nil tag 0.
        if tag == 9:            # int32 number -> re-emit as stock double
            w.b_(3)
            val = struct.unpack("<i", r.raw(4))[0]
            w.raw(struct.pack("<d", float(val)))
        elif tag == 0:          # nil
            w.b_(0)
        elif tag == 1:          # boolean
            w.b_(1)
            w.b_(r.b())
        elif tag == 3:          # number (8-byte double, stock encoding)
            w.b_(3)
            w.raw(r.raw(8))
        elif tag == 4:          # string
            w.b_(4)
            w.str8(r.str4())
        else:
            raise ValueError(f"constant tag {tag} at {r.p:#x}")
    n = r.i32()                 # prototype count
    w.i32(n)
    for _ in range(n):
        conv_func(r, w)
    n = r.i32()                 # line info count
    w.i32(n)
    w.raw(r.raw(4 * n))
    n = r.i32()                 # local var count
    w.i32(n)
    for _ in range(n):
        w.str8(r.str4())
        w.i32(r.i32())          # startpc
        w.i32(r.i32())          # endpc
    n = r.i32()                 # upvalue name count
    w.i32(n)
    for _ in range(n):
        w.str8(r.str4())


def main():
    src = sys.argv[1]
    dst = sys.argv[2]
    data = open(src, "rb").read()
    r = R(data)
    hdr = r.raw(12)
    assert hdr[:4] == b"\x1bLua" and hdr[4] == 0x51, "not a Lua 5.1 chunk"
    assert hdr[8] == 4, "source chunk not 32-bit size_t"
    w = W()
    w.raw(hdr[:8] + bytes([8, hdr[9], hdr[10], 0]))  # size_t=8, integral=0
    conv_func(r, w)
    assert r.p == len(data), f"trailing bytes: read {r.p} of {len(data)}"
    open(dst, "wb").write(bytes(w.b))
    print(f"converted {src} -> {dst} ({len(data)} -> {len(w.b)} bytes)")


if __name__ == "__main__":
    main()
