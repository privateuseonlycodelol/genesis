import unittest

from analyze_f1_bootp_xid import (
    M32,
    Sample,
    carry_predicted_in,
    carry_window,
    predicted_carry_offset,
    timer_from_xid,
    timer_residuals,
    uboot_default_base,
)

# Captured GCNT-X BOOTREQUEST frames from artifacts/bootp/2026-10-13/wan.pcapng
# (tshark frame.time_epoch, bootp.id). MAC is the U-Boot "Using MAC Address" value.
MAC = "00:1e:e3:76:83:61"
FRAME_277 = Sample(1791853797.522093200, 0xE376C3AE)
FRAME_396 = Sample(1791853825.287597300, 0xE3773024)


class UBootBaseTests(unittest.TestCase):
    def test_base_from_mac_octets_2_to_5(self) -> None:
        # e3<<24 + 76<<16 + 83<<8 + 61 (hand computed)
        self.assertEqual(uboot_default_base(MAC), 0xE3768361)

    def test_base_rejects_short_mac(self) -> None:
        with self.assertRaises(ValueError):
            uboot_default_base("00:1e:e3:76:83")


class TimerTests(unittest.TestCase):
    def test_timer_from_xid_wraps_modulo_2_32(self) -> None:
        self.assertEqual(timer_from_xid(0x00000010, 0xFFFFFFF0), 0x20)

    def test_timer_from_xid_plain(self) -> None:
        self.assertEqual(timer_from_xid(0xE376C3AE, 0xE3768361), 0x404D)


class TimerResidualTests(unittest.TestCase):
    def test_real_capture_pair_advances_at_1khz(self) -> None:
        rows = timer_residuals([FRAME_277, FRAME_396], uboot_default_base(MAC))
        self.assertEqual(rows[0].timer_ms, 16461)
        self.assertEqual(rows[1].timer_ms, 44227)
        # 27.765 s of wall clock vs 27766 ms of xid timer: within tshark resolution
        self.assertLess(abs(rows[1].residual_ms), 2.0)

    def test_negative_control_random_jitter_is_inconsistent(self) -> None:
        base = uboot_default_base(MAC)
        # xid jumps by 1000 ms per second of wall clock, but one sample is 5 s off
        samples = [Sample(float(i), (base + 1000 * i + (5000 if i == 3 else 0)) % M32) for i in range(6)]
        rows = timer_residuals(samples, base)
        self.assertGreater(max(abs(r.residual_ms) for r in rows), 2.0)

    def test_synthetic_1khz_counter_is_consistent(self) -> None:
        base = uboot_default_base(MAC)
        samples = [Sample(100.0 + i * 0.25, (base + 500 + 250 * i) % M32) for i in range(8)]
        rows = timer_residuals(samples, base)
        self.assertTrue(all(abs(r.residual_ms) < 1e-6 for r in rows))


class CarryTests(unittest.TestCase):
    def test_real_high_half_change_is_predicted_by_base(self) -> None:
        # Frames 361 and 367 straddle the e376 -> e377 change (timer values 30220 and 32221).
        before, after = Sample(0.0, 0xE376F96D), Sample(2.0, 0xE377013E)
        base = uboot_default_base(MAC)
        window = carry_window([before, after], base)
        self.assertEqual(window, (30220, 32221))
        self.assertTrue(carry_predicted_in(*window, predicted_carry_offset(base)))

    def test_negative_control_window_without_boundary(self) -> None:
        base = uboot_default_base(MAC)
        # Window 35000..37000 ms contains no multiple of 65536 offset from 31903.
        self.assertFalse(carry_predicted_in(35000, 37000, predicted_carry_offset(base)))

    def test_no_carry_returns_none(self) -> None:
        base = uboot_default_base(MAC)
        self.assertIsNone(carry_window([FRAME_277, Sample(0.0, 0xE376C3B0)], base))


if __name__ == "__main__":
    unittest.main()
