import unittest

from h323_ras_cons_trigger import (
    build_registration_confirm,
    build_spill_trigger,
    inspect_expected_layout,
    inspect_spill_layout,
)


class RasConsPacketTests(unittest.TestCase):
    def test_valid_ttl_control_has_post_open_padding(self):
        packet = build_registration_confirm(trigger=False, ttl=30)
        self.assertEqual(len(packet), 27)
        self.assertEqual(packet[-10:], bytes.fromhex("05c00000001d00000000"))
        inspect_expected_layout(packet, trigger=False)

    def test_truncated_trigger_stays_at_one_byte_open_type_end(self):
        packet = build_registration_confirm(trigger=True)
        self.assertEqual(len(packet), 19)
        self.assertEqual(packet[-2:], bytes.fromhex("01c0"))
        inspect_expected_layout(packet, trigger=True)

    def test_spill_trigger_keeps_ttl_bytes_outside_declared_open_type(self):
        packet = build_spill_trigger(ttl=30)
        control = build_registration_confirm(trigger=False, ttl=30)
        self.assertEqual(len(packet), len(control))
        self.assertEqual(packet[-10:], bytes.fromhex("01c00000001d00000000"))
        inspect_spill_layout(packet, ttl=30)


if __name__ == "__main__":
    unittest.main()
