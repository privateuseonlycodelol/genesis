#!/usr/bin/env python3
"""Unit tests for scripts/generate_f1_overlay.py."""

import stat
import tempfile
import unittest
from pathlib import Path

from scripts.generate_f1_overlay import (
    CLASH_ACCESS_CONTROL_LUA_CONTENT,
    CLASH_CONFIG_CONTENT,
    DROPBEAR_CONFIG_CONTENT,
    INITD_TRIAGE_CONTENT,
    INITTAB_CONTENT,
    OBUSPA_RETRIEVER_CONTENT,
    PASSWD_CONTENT,
    RC_LOCAL_CONTENT,
    RESTRICTED_SHELL_WRAPPER,
    TRIAGE_SCRIPT_CONTENT,
    generate_overlay_staging,
)


class TestGenerateF1Overlay(unittest.TestCase):
    def test_default_generation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir)
            res = generate_overlay_staging(target)
            self.assertIn("bank_1", res)
            self.assertIn("bank_1/upper", res)
            self.assertIn("bank_2", res)
            self.assertIn("bank_2/upper", res)
            self.assertIn("root", res)
            self.assertIn("root/upper", res)

            # Check work directories
            self.assertTrue((target / "bank_1" / "work").is_dir())
            self.assertTrue((target / "bank_2" / "work").is_dir())
            self.assertTrue((target / "work").is_dir())

            # Check upper directory file in bank_2
            bank2_upper = target / "bank_2" / "upper"
            self.assertTrue((bank2_upper / "bin" / "restricted_shell").is_file())
            self.assertTrue((bank2_upper / "etc" / "rc.d" / "S99triage").is_file())

            # Check files in bank_2 (active bank)
            bank2_dir = target / "bank_2"
            inittab = bank2_dir / "etc" / "inittab"
            passwd = bank2_dir / "etc" / "passwd"
            shadow = bank2_dir / "etc" / "shadow"
            rclocal = bank2_dir / "etc" / "rc.local"
            clash = bank2_dir / "etc" / "config" / "clash"
            dropbear = bank2_dir / "etc" / "config" / "dropbear"

            self.assertTrue(inittab.is_file())
            self.assertEqual(inittab.read_text(), INITTAB_CONTENT)
            self.assertEqual(oct(stat.S_IMODE(inittab.stat().st_mode)), "0o644")

            self.assertTrue(passwd.is_file())
            self.assertEqual(passwd.read_text(), PASSWD_CONTENT)

            self.assertTrue(shadow.is_file())
            # Default is empty password
            self.assertTrue(shadow.read_text().startswith("root::18000"))
            self.assertEqual(oct(stat.S_IMODE(shadow.stat().st_mode)), "0o600")

            self.assertTrue(rclocal.is_file())
            self.assertEqual(rclocal.read_text(), RC_LOCAL_CONTENT)
            self.assertEqual(oct(stat.S_IMODE(rclocal.stat().st_mode)), "0o755")

            self.assertTrue(clash.is_file())
            self.assertEqual(clash.read_text(), CLASH_CONFIG_CONTENT)

            self.assertTrue(dropbear.is_file())
            self.assertEqual(dropbear.read_text(), DROPBEAR_CONFIG_CONTENT)

            triage = bank2_dir / "root" / "triage.sh"
            self.assertTrue(triage.is_file())
            self.assertEqual(triage.read_text(), TRIAGE_SCRIPT_CONTENT)
            self.assertEqual(oct(stat.S_IMODE(triage.stat().st_mode)), "0o755")

            # Check restricted_shell override in bin/restricted_shell
            rs = bank2_dir / "bin" / "restricted_shell"
            self.assertTrue(rs.is_file())
            self.assertEqual(rs.read_text(), RESTRICTED_SHELL_WRAPPER)
            self.assertEqual(oct(stat.S_IMODE(rs.stat().st_mode)), "0o755")

            # Check init.d and rc.d triage services
            initd = bank2_dir / "etc" / "init.d" / "triage"
            rcd = bank2_dir / "etc" / "rc.d" / "S99triage"
            self.assertTrue(initd.is_file())
            self.assertEqual(initd.read_text(), INITD_TRIAGE_CONTENT)
            self.assertEqual(oct(stat.S_IMODE(initd.stat().st_mode)), "0o755")
            self.assertTrue(rcd.is_file())
            self.assertEqual(rcd.read_text(), INITD_TRIAGE_CONTENT)
            self.assertEqual(oct(stat.S_IMODE(rcd.stat().st_mode)), "0o755")

            # Check obuspa_retriever.sh shadow hook
            obuspa = bank2_dir / "usr" / "share" / "transformer" / "scripts" / "obuspa_retriever.sh"
            self.assertTrue(obuspa.is_file())
            self.assertEqual(obuspa.read_text(), OBUSPA_RETRIEVER_CONTENT)
            self.assertEqual(oct(stat.S_IMODE(obuspa.stat().st_mode)), "0o755")

            # Check clash-access-control.lua override
            lua_acl = bank2_dir / "usr" / "lib" / "lua" / "clash-access-control.lua"
            self.assertTrue(lua_acl.is_file())
            self.assertEqual(lua_acl.read_text(), CLASH_ACCESS_CONTROL_LUA_CONTENT)
            self.assertEqual(oct(stat.S_IMODE(lua_acl.stat().st_mode)), "0o644")

            # Check Technicolor 80_rtfd_restore persistence files
            persist_dir = target / "rtfd_persistent_files"
            self.assertTrue(persist_dir.is_dir())
            self.assertTrue((persist_dir / "passwd").is_file())
            self.assertTrue((persist_dir / "shadow").is_file())
            self.assertTrue((persist_dir / "restricted_shell").is_file())
            self.assertTrue((persist_dir / "clash-access-control.lua").is_file())
            conf_file = target / "rtfd_persistent_filelist.conf"
            self.assertTrue(conf_file.is_file())
            conf_text = conf_file.read_text()
            self.assertIn("/etc/passwd etc", conf_text)
            self.assertIn("/etc/shadow etc", conf_text)
            self.assertIn("/bin/restricted_shell bin", conf_text)
            self.assertIn("/usr/lib/lua/clash-access-control.lua usr/lib/lua", conf_text)

            # Check OpenWrt 80_mount_root and 82_ispconfig_restore archives
            self.assertTrue((target / "sysupgrade.tgz").is_file())
            self.assertTrue((target / "ispconfig-bank_1.tgz").is_file())
            self.assertTrue((target / "ispconfig-bank_2.tgz").is_file())

    def test_custom_password_and_hash(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir)
            generate_overlay_staging(target, password="testpassword123")
            shadow = (target / "bank_2" / "etc" / "shadow").read_text()
            self.assertNotIn("root::", shadow)
            self.assertIn("root:$6$", shadow)

        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir)
            generate_overlay_staging(target, root_hash="$6$mycustomhash$12345")
            shadow = (target / "bank_2" / "etc" / "shadow").read_text()
            self.assertTrue(shadow.startswith("root:$6$mycustomhash$12345:18000"))

    def test_no_root_mirror(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir)
            res = generate_overlay_staging(target, mirror_to_root=False)
            self.assertIn("bank_1", res)
            self.assertIn("bank_2", res)
            self.assertNotIn("root", res)
            self.assertFalse((target / "etc").exists())
            self.assertTrue((target / "bank_1" / "etc").exists())
            self.assertTrue((target / "bank_2" / "etc").exists())


if __name__ == "__main__":
    unittest.main()
