#!/usr/bin/env python3
"""Generate a staging filesystem tree for the Telia F1 / GCNT-X rootfs_data overlay.

Homeware partitions rootfs_data by active bank (HOMEWARE_CONFIG_ON_ACTIVE_BANK).
This tool generates the exact overlay layout for both bank_1 and bank_2 containing:
  - etc/inittab: directs console activation to /bin/ash --login (bypasses restricted_shell/clash)
  - etc/passwd: ensures root has /bin/ash shell
  - etc/shadow: sets root password (empty by default for passwordless UART console entry)
  - etc/rc.local: launches fallback background telnet daemon on LAN port 23
  - etc/config/dropbear: enables SSH with password authentication on LAN
  - etc/config/clash: explicitly permits root access on serial interface

Pure Python, offline, no device contact.
"""

from __future__ import annotations

import argparse
import os
import secrets
import stat
import subprocess
import sys
from pathlib import Path

# Template files
INITTAB_CONTENT = """\
::sysinit:/etc/init.d/rcS S boot
::shutdown:/etc/init.d/rcS K shutdown
::askconsole:/bin/ash --login
"""

PASSWD_CONTENT = """\
root:x:0:0:root:/root:/bin/ash
daemon:*:1:1:daemon:/var:/bin/false
ftp:*:55:55:ftp:/home/ftp:/bin/false
network:*:101:101:network:/var:/bin/false
nobody:*:65534:65534:nobody:/var:/bin/false
"""

RC_LOCAL_CONTENT = """\
#!/bin/sh
# F1 recovery overlay startup script
if command -v busybox >/dev/null 2>&1; then
    busybox telnetd -l /bin/ash -p 23 &
fi
exit 0
"""

DROPBEAR_CONFIG_CONTENT = """\
config dropbear
\toption PasswordAuth 'on'
\toption RootPasswordAuth 'on'
\toption Port '22'
\toption Interface 'lan'
"""

CLASH_CONFIG_CONTENT = """\
config clash 'core'
\toption enabled '0'

config access 'serial'
\toption user 'root'
\toption enabled '1'
"""


def build_shadow_content(root_hash: str = "") -> str:
    """Generate /etc/shadow content. Empty hash allows passwordless root login."""
    return f"""\
root:{root_hash}:18000:0:99999:7:::
daemon:*:0:0:99999:7:::
ftp:*:0:0:99999:7:::
network:*:0:0:99999:7:::
nobody:*:0:0:99999:7:::
"""


def populate_bank_tree(base_dir: Path, shadow_hash: str = "") -> list[Path]:
    """Populate an overlay root tree (e.g. base_dir/etc/...)."""
    etc_dir = base_dir / "etc"
    config_dir = etc_dir / "config"
    etc_dir.mkdir(parents=True, exist_ok=True)
    config_dir.mkdir(parents=True, exist_ok=True)

    files_created = []

    # inittab (0644)
    p_inittab = etc_dir / "inittab"
    p_inittab.write_text(INITTAB_CONTENT, encoding="utf-8")
    os.chmod(p_inittab, 0o644)
    files_created.append(p_inittab)

    # passwd (0644)
    p_passwd = etc_dir / "passwd"
    p_passwd.write_text(PASSWD_CONTENT, encoding="utf-8")
    os.chmod(p_passwd, 0o644)
    files_created.append(p_passwd)

    # shadow (0600)
    p_shadow = etc_dir / "shadow"
    p_shadow.write_text(build_shadow_content(shadow_hash), encoding="utf-8")
    os.chmod(p_shadow, 0o600)
    files_created.append(p_shadow)

    # rc.local (0755)
    p_rclocal = etc_dir / "rc.local"
    p_rclocal.write_text(RC_LOCAL_CONTENT, encoding="utf-8")
    os.chmod(p_rclocal, 0o755)
    files_created.append(p_rclocal)

    # config/dropbear (0644)
    p_dropbear = config_dir / "dropbear"
    p_dropbear.write_text(DROPBEAR_CONFIG_CONTENT, encoding="utf-8")
    os.chmod(p_dropbear, 0o644)
    files_created.append(p_dropbear)

    # config/clash (0644)
    p_clash = config_dir / "clash"
    p_clash.write_text(CLASH_CONFIG_CONTENT, encoding="utf-8")
    os.chmod(p_clash, 0o644)
    files_created.append(p_clash)

    return files_created


def generate_overlay_staging(
    target_dir: Path,
    password: str | None = None,
    root_hash: str | None = None,
    banks: tuple[str, ...] = ("bank_1", "bank_2"),
    mirror_to_root: bool = True,
) -> dict[str, list[Path]]:
    """Generate the full overlay staging tree with bank subdirectories and permissions."""
    target_dir = target_dir.resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    # Compute shadow hash
    if root_hash:
        final_hash = root_hash
    elif password:
        # Standard SHA-512 crypt via openssl (portable across Python versions)
        res = subprocess.run(
            ["openssl", "passwd", "-6", password],
            capture_output=True,
            text=True,
            check=True,
        )
        final_hash = res.stdout.strip()
    else:
        final_hash = ""  # Blank password

    created: dict[str, list[Path]] = {}

    for bank in banks:
        bank_path = target_dir / bank
        created[bank] = populate_bank_tree(bank_path, shadow_hash=final_hash)

    if mirror_to_root:
        created["root"] = populate_bank_tree(target_dir, shadow_hash=final_hash)

    return created


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--out",
        "-o",
        type=Path,
        default=Path("artifacts/firmware/overlay_staging"),
        help="Target directory for staging tree (default: artifacts/firmware/overlay_staging)",
    )
    parser.add_argument(
        "--password",
        help="Plaintext root password (will be hashed with SHA-512 crypt)",
    )
    parser.add_argument(
        "--hash",
        dest="root_hash",
        help="Raw password hash for root in /etc/shadow",
    )
    parser.add_argument(
        "--no-root-mirror",
        action="store_true",
        help="Do not populate the top-level directory, only bank_1 and bank_2 subdirectories",
    )
    args = parser.parse_args()

    out_dir = args.out.resolve()
    results = generate_overlay_staging(
        target_dir=out_dir,
        password=args.password,
        root_hash=args.root_hash,
        mirror_to_root=not args.no_root_mirror,
    )

    total_files = sum(len(fl) for fl in results.values())
    print(f"[+] Successfully generated {total_files} overlay files across {len(results)} hierarchies:")
    for section, files in results.items():
        print(f"  [{section}] ({len(files)} files)")
        for f in files:
            rel = f.relative_to(out_dir)
            mode = oct(stat.S_IMODE(f.stat().st_mode))
            print(f"    - {rel} (mode {mode})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
