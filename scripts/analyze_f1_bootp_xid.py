"""Check the GCNT-X BOOTREQUEST transaction id against U-Boot's default xid formula.

Offline only. Reads a tshark export of already-captured frames and reports
whether the xid behaves like the upstream U-Boot default (net/bootp.c, default
path, not CONFIG_BOOTP_RANDOM_XID):

    xid = htonl( (MAC[2]<<24) + (MAC[3]<<16) + (MAC[4]<<8) + MAC[5] + get_timer(0) )

Two checks:
  1. Timer check: xid minus the MAC-derived base should advance with wall-clock
     time at 1 kHz (get_timer is in ms). Residual is reported per frame.
  2. Carry check: the high 16 bits of the xid should change exactly when the
     timer crosses the point where the low 16 bits of the base overflow.

Neither check proves the device runs this code. Both only test whether the
captured values are consistent with it.

Export the input with (the epoch column is frame.time_epoch):

    tshark -r <capture.pcapng> -Y 'bootp && eth.src==<mac> && bootp.type==1' \
        -T fields -e frame.time_epoch -e bootp.id > requests.tsv

Usage:
    python3 scripts/analyze_f1_bootp_xid.py --mac 00:1e:e3:76:83:61 requests.tsv
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

M32 = 2**32
TIMER_TOLERANCE_MS = 2.0  # tshark prints epoch with 0.1 ms resolution; allow a little slack


def uboot_default_base(mac: str) -> int:
    """Return the MAC-derived part of the upstream U-Boot default xid (host order)."""
    octets = [int(x, 16) for x in mac.split(":")]
    if len(octets) != 6:
        raise ValueError(f"expected 6 MAC octets, got {mac!r}")
    return ((octets[2] << 24) + (octets[3] << 16) + (octets[4] << 8) + octets[5]) % M32


def timer_from_xid(xid: int, base: int) -> int:
    """Timer value in ms implied by an xid, modulo 2**32."""
    return (xid - base) % M32


@dataclass
class Sample:
    epoch: float
    xid: int


@dataclass
class TimerRow:
    epoch: float
    xid: int
    timer_ms: int
    residual_ms: float  # (timer - timer0) - (epoch - epoch0) * 1000


def timer_residuals(samples: list[Sample], base: int) -> list[TimerRow]:
    if not samples:
        return []
    t0 = timer_from_xid(samples[0].xid, base)
    e0 = samples[0].epoch
    rows = []
    for s in samples:
        timer = timer_from_xid(s.xid, base)
        delta_timer = (timer - t0) % M32
        rows.append(TimerRow(s.epoch, s.xid, timer, delta_timer - (s.epoch - e0) * 1000.0))
    return rows


def carry_window(samples: list[Sample], base: int) -> tuple[int, int] | None:
    """Return the (lo, hi) timer window in which the xid high half changes, if any.

    The window is the pair of consecutive samples where the xid high 16 bits
    differ. Returns None if the high half never changes in the samples.
    """
    for a, b in zip(samples, samples[1:]):
        if (a.xid >> 16) != (b.xid >> 16):
            return timer_from_xid(a.xid, base), timer_from_xid(b.xid, base)
    return None


def predicted_carry_offset(base: int) -> int:
    """Timer value (ms, mod 0x10000) at which (base + timer) crosses a 0x10000 boundary."""
    return (0x10000 - (base & 0xFFFF)) % 0x10000


def carry_predicted_in(lo: int, hi: int, offset: int) -> bool:
    """True if some timer value t with t % 0x10000 == offset satisfies lo < t <= hi."""
    return (hi - offset) // 0x10000 > (lo - offset) // 0x10000


def load_tsv(path: str) -> list[Sample]:
    samples = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            epoch, xid = line.split("\t")[:2]
            samples.append(Sample(float(epoch), int(xid, 16)))
    return samples


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mac", required=True, help="client MAC (the U-Boot 'Using MAC Address' value)")
    ap.add_argument("tsv", help="tshark export: frame.time_epoch <tab> bootp.id")
    args = ap.parse_args(argv)

    base = uboot_default_base(args.mac)
    samples = load_tsv(args.tsv)
    rows = timer_residuals(samples, base)
    print(f"base (MAC-derived, host order) = {base:08x}; frames = {len(rows)}")
    for r in rows:
        print(f"epoch={r.epoch:.4f} xid={r.xid:08x} timer_ms={r.timer_ms:10d} residual_ms={r.residual_ms:+.2f}")
    max_abs = max((abs(r.residual_ms) for r in rows), default=0.0)
    print(f"max |residual| = {max_abs:.2f} ms (tolerance {TIMER_TOLERANCE_MS} ms)")
    print(f"timer advances at 1 kHz: {'consistent' if max_abs <= TIMER_TOLERANCE_MS else 'NOT consistent'}")

    window = carry_window(samples, base)
    offset = predicted_carry_offset(base)
    if window is None:
        print("carry: high half never changes in these samples; no carry check possible")
    else:
        lo, hi = window
        inside = carry_predicted_in(lo, hi, offset)
        print(f"carry window (timer ms) = ({lo}, {hi}]; predicted boundary offset = {offset} mod 65536: "
              f"{'inside window' if inside else 'outside window'}")
    return 0 if max_abs <= TIMER_TOLERANCE_MS else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
