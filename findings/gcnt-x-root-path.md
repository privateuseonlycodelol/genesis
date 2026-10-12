# GCNT-X (19.x) community root / flash path — lab reference only

**Bold warning:** The user’s **live** router is **Telia F1 GCNT-X firmware 23.1.b**. **Do not flash** this 19.x RBI (`REFERENCE-GCNT-X-19.x-DO-NOT-FLASH.rbi`) or downgrade via bank tricks on that unit — **brick / downgrade-lock risk** per [hack-technicolor #321](https://github.com/hack-technicolor/hack-technicolor/issues/321). This document describes what the community reported for **19.x-era** lab hardware matching **GCNT-X / EWA1330**, not an actionable path on **23.1.b**.

---

## Preconditions (19.x lab context)

- Hardware: **Technicolor EWA1330**, board mnemonic **GCNT-X**, Telia **F1** (Lithuania/Sweden reports in #321).
- Firmware generation: **Homeware / OpenWrt 19.5.x** branch (issue threads reference `19.5.1062`, `19.5.0990`, etc.).
- **GCNT-X OSCK** for PC decrypt is **not** published in the hack-technicolor repository (unlike **GCNT-R**). Root/extract paths assume either on-router `bli_unseal` or a future shared OSCK.
- Telia builds: **no** `tch-exploit` / Type-2 “easy root” recipe confirmed for this ISP SKU in #321.

## Bank switch (~14 seconds) — local upgrade menu

From [#321](https://github.com/hack-technicolor/hack-technicolor/issues/321) (Telia **F1 / F1X** specific):

1. Power on the router, wait **exactly 14 seconds**, power off (on/off button).
2. Repeat **two more times** (third boot: wait 14 s again).
3. After the third cycle, **Local Upgrade** may appear under **System information → Configuration**.
4. If it does not appear, repeat a **fourth** 14 s cycle.

Reported effects on 19.x units:

- Exposes operator-style local RBI upload (still **signed** — wrong image rejected).
- Some users saw **both banks** settle on older **19.5.0990** after cycles (downgrade side effect) — **not** guaranteed on **23.1.b**.

**23.1.b note:** Downgrade locks and Vantiva/Telia changes may make this menu useless or dangerous on the current production build. Treat as **historical 19.x** only.

## BOOTP recovery (generic Technicolor)

From [hack-technicolor Recovery](https://hack-technicolor.readthedocs.io/en/stable/Recovery/) — applies when the gateway is in **BOOTP** mode (serial/Ethernet), not normal boot:

- Host runs a BOOTP/TFTP server; device accepts **correctly signed** RBI for its board mnemonic.
- Signature checked **before** flash; modified RBI rejected.
- Used for unbrick / Type-2 recovery on **other** boards with known Type-2 RBIs — **GCNT-X Type-2 / rootable RBI** is **not** established in the public repo.

## SSH / `tchroot` (reported on rooted 19.x)

Issue #321 (paraphrased):

- Service listens on **VLAN** interfaces (ISP-specific VLAN — contributors used mirrored WAN / correct VLAN to reach dropbear).
- SSH username reported: **`tchroot`** (password not consistently published; other accounts like `tadmin` / Telia remote passwords discussed — treat as sensitive, rotate on real networks).
- Enabling dropbear on **LAN** after root follows standard Homeware overlay pattern (see [Upgrade](https://hack-technicolor.readthedocs.io/en/stable/Upgrade/) `uci set dropbear...` block).

**Without root:** SSH is not available; #321 documents failed attempts and rate-limited login on later firmware.

## Safe in-place upgrade (once rooted)

From hack-technicolor **Safe Firmware Upgrade** (rooted gateway):

```bash
# On router: unpack RBI to bank image
cat /tmp/new.rbi | (bli_parser && bli_unseal | dd bs=4 skip=1 seek=1 of=/tmp/new.bin)
# Then mtd write to booted bank (see full guide — preserves overlay plan)
```

On Mac/PC: **Decrypt_RBI_Firmware_Utility** or OSCK + same crypto chain, then `binwalk -e`.

## What does **not** work (Telia GCNT-X, per #321)

- Flashing random 19.4 RBIs from ACS mirrors without signature match.
- Assuming **logviewer** hex (`4d17f88a54003ce68362bbf7b1c70d1d`) is OSCK or SSH key.
- **`tch-exploit`** on Telia 19.5+ builds (closed/unavailable for this SKU).
- Using this 19.x reference path on a **23.1.b** production F1 — **NO** (see warning above).

## Mapping to this repo

| Goal | 19.x lab hardware | User’s 23.1.b F1 |
|------|-------------------|------------------|
| Decrypt reference RBI offline | Needs **GCNT-X OSCK** | Same |
| Extract squashfs | After decrypt | Need 23.1.b RBI capture first |
| Read shipped **`/etc/cups/cupsd.conf`** | From extracted rootfs or rooted `cat` | **Not obtained**; LAN IPP behavior mapped without it ([f1-cups-ipp-policy-2026-10-12.md](f1-cups-ipp-policy-2026-10-12.md)) |
| Root | VLAN/SSH/`tchroot` reports + unknown exploit surface | **Not actionable** from public docs alone |
| Bank switch 14 s | Reported for local upgrade UI | **Do not rely on** for 23.1.b |

Further offline work: `findings/gcnt-x-19x-deep.md`, WAN capture `findings/wan-pcap.md`.
