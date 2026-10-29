import unittest

from f1_printersharing_webui_toggle import build_post_fields


class BuildPostFieldsTests(unittest.TestCase):
    def test_enabled_is_sent_as_passed_not_forced(self):
        # Regression: the POST used to hardcode printersharing_enabled=1.
        self.assertEqual(
            build_post_fields("0", "1", "")["printersharing_enabled"],
            "0",
        )
        self.assertEqual(
            build_post_fields("1", "0", "")["printersharing_enabled"],
            "1",
        )

    def test_webui_value_is_sent(self):
        self.assertEqual(build_post_fields("1", "0", "")["printersharing_webui"], "0")
        self.assertEqual(build_post_fields("1", "1", "")["printersharing_webui"], "1")

    def test_csrf_only_when_present(self):
        self.assertNotIn("CSRFtoken", build_post_fields("1", "1", ""))
        self.assertEqual(build_post_fields("1", "1", "tok")["CSRFtoken"], "tok")

    def test_rejects_invalid_values(self):
        for enabled, webui in [("", "1"), ("1", ""), ("2", "1"), ("1", "yes"), ("true", "0")]:
            with self.subTest(enabled=enabled, webui=webui):
                with self.assertRaises(ValueError):
                    build_post_fields(enabled, webui, "")


if __name__ == "__main__":
    unittest.main()
