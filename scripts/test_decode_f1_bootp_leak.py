import unittest

from decode_f1_bootp_leak import decode_boot_file_field, walk_vendor_specific


class DecodeBootFileFieldTests(unittest.TestCase):
    def test_single_string_spec_conformant(self) -> None:
        field = b"GCNT-X" + b"\x00" * (128 - 6)
        result = decode_boot_file_field(field)
        self.assertEqual(result.strings, ["GCNT-X"])

    def test_two_strings_matches_captured_f1_bytes(self) -> None:
        # Exact bytes from artifacts/bootp/2026-10-13/wan.pcapng frame 277,
        # offset 0x96 in the raw hexdump (the bootp.file field).
        field = b"GCNT-X\x00" + b"23KN/0/TL" + b"\x00" * (128 - 6 - 1 - 9)
        result = decode_boot_file_field(field)
        self.assertEqual(result.strings, ["GCNT-X", "23KN/0/TL"])

    def test_all_zero_field_yields_no_strings(self) -> None:
        result = decode_boot_file_field(b"\x00" * 128)
        self.assertEqual(result.strings, [])

    def test_embedded_nonzero_run_without_trailing_null_still_captured(self) -> None:
        # Guards against silently dropping a run that isn't null-terminated
        # (e.g. truncated capture) -- should still surface what's there.
        field = b"ABC" + b"\x00" * 10 + b"DEF"
        result = decode_boot_file_field(field)
        self.assertEqual(result.strings, ["ABC", "DEF"])


class WalkVendorSpecificTests(unittest.TestCase):
    def test_clean_tlv_walks_fully(self) -> None:
        # tag=0x01 len=2 val=AB ; tag=0x02 len=1 val=C ; End
        blob = bytes([0x01, 0x02]) + b"AB" + bytes([0x02, 0x01]) + b"C" + bytes([0xFF])
        out = walk_vendor_specific(blob)
        self.assertEqual(out, [(0, b"AB"), (4, b"C")])

    def test_overrunning_length_stops_walk_without_raising(self) -> None:
        # tag=0x01 claims len=200 but buffer is far shorter -- must not crash
        # or fabricate bytes; this is exactly the shape of the captured F1
        # option-43 blob when walked from offset 0 instead of its true start.
        blob = bytes([0x01, 0xC8]) + b"short"
        out = walk_vendor_specific(blob)
        self.assertEqual(out, [])

    def test_skip_prefix_honored(self) -> None:
        blob = b"XX" + bytes([0x01, 0x01]) + b"A" + bytes([0xFF])
        out = walk_vendor_specific(blob, skip_prefix=2)
        self.assertEqual(out, [(2, b"A")])

    def test_captured_f1_vendor_blob_does_not_walk_cleanly_as_tlv(self) -> None:
        # Real bytes from frame 277's option 43 (55 bytes). Documented in
        # the finding as evidence AGAINST a well-formed vendor schema here --
        # walking from offset 2 (after literal "ST" prefix) should produce
        # at most one or two entries before a length byte overruns, not a
        # clean full walk to an End marker.
        blob = bytes.fromhex(
            "53540504820603000007400832323432414438414e00000000000000090000"
            "0a0000000000000000000000000b00000000000000000cff"
        )
        out = walk_vendor_specific(blob, skip_prefix=2)
        # Must not raise, and must not claim to have reached 0xFF cleanly
        # with a fully-consumed, sensible-looking option set.
        total_consumed = sum(2 + len(v) for _, v in out)
        self.assertLess(total_consumed, len(blob) - 2)


if __name__ == "__main__":
    unittest.main()
