# Vantiva GPL Source Code Request: Formal Dispatch Specification (2026-10-29)

## Purpose

Document the formal open-source compliance request for the complete corresponding source code of GPL/LGPL components running on the **Telia F1 / Vantiva GCNT-X (EWA1330)** on build **`23.1.b.0448-7241017-20260223134332`**.

This route carries **zero hardware risk**, incurs zero cost, operates entirely out-of-band/asynchronously, and directly compels the delivery of the complete Linux kernel, U-Boot, device tree, and OpenWrt/Homeware build manifests under the terms of the GNU General Public License (GPL-2.0 / LGPL-2.1).

---

## 1. Compliance Channel Identification

- **Official Compliance Contact:** **`contact-ch.opensource@vantiva.com`**
  - **Status:** **VERIFIED** via official Vantiva Connected Home Open Source Compliance documentation.
  - **Entity:** Vantiva S.A. (formerly Technicolor Connected Home).
  - **Purpose:** Designated compliance mailbox for processing written requests for corresponding source code under GPL v2 / v3 and LGPL v2.1.
- **Secondary / ISP Contact:** Telia Company AB Product Compliance / Legal Department (Solna, Sweden).

---

## 2. Device & Firmware Identification Baseline

To ensure the compliance desk cannot reject or stall the request due to missing technical parameters, the request contains exact, verified board and build identifiers:

| Identifier | Verified Value | Evidence Reference |
| :--- | :--- | :--- |
| **Commercial Product Name** | Telia F1 (or Telia Router F1) | Device chassis / Web GUI |
| **Manufacturer Model** | Vantiva / Technicolor **GCNT-X** (Marketing: **EWA1330 / EWA1330TCS**) | Web GUI & PCB marking |
| **Board Revision** | **`AP-BCM114-00001 REV 1.0`** | Physical PCB silkscreen |
| **SoC / Architecture** | Broadcom BCM68560 / BCM68580 series (ARMv8 64-bit) | Boot log (`4.19.235`, `aarch64`) |
| **Firmware Build** | **`23.1.b.0448-7241017-20260223134332`** | UI version string & boot log |
| **Target Kernel** | **Linux 4.19.235** (including BSP patches, `.config`, and DTS) | Boot log L818 |
| **Target Bootloader** | **U-Boot 2019.07** | Boot log L512 |
| **Target Open-Source Userland** | BusyBox, CUPS, iptables, dnsmasq, iproute2, OpenSSL, etc. | Running process tree |

---

## 3. Formal Request Email Template

**To:** `contact-ch.opensource@vantiva.com`  
**Subject:** Formal GPL Source Code Request – Vantiva GCNT-X (EWA1330 / Telia F1) – Firmware 23.1.b

```text
Dear Vantiva Open Source Compliance Team,

Under the terms of the GNU General Public License (GPLv2, GPLv3) and the GNU Lesser General Public License (LGPLv2.1), I am formally requesting a copy of the complete, corresponding machine-readable source code for the open-source software distributed on the following device:

Device Details:
- Manufacturer: Vantiva (formerly Technicolor Connected Home)
- Product Name: Telia F1 / Telia Router F1
- Hardware Model: GCNT-X (EWA1330 / EWA1330TCS)
- Board Revision: AP-BCM114-00001 REV 1.0
- Installed Firmware Version: 23.1.b.0448-7241017-20260223134332
- Kernel Version: Linux 4.19.235
- Bootloader: U-Boot 2019.07

Specifically, this request includes:
1. Complete source code for the Linux kernel 4.19.235, including all architecture, SoC, and board-level patches, Device Tree Source files (.dts / .dtsi), and the target kernel configuration (.config).
2. Complete source code and board configurations for U-Boot 2019.07.
3. Complete source code for all GPL/LGPL-licensed user-space packages distributed in this firmware release (including BusyBox, CUPS, iptables, dnsmasq, etc.).
4. The build scripts, Makefiles, and package manifest/configuration files necessary to generate the open-source binaries from source.

Please provide a link to download the source archives, or advise on any nominal media fee if distributed via physical media.

Thank you for your assistance and ongoing commitment to open-source compliance.

Sincerely,
[Your Name / Contact Information]
```

---

## 4. Information Gain Assessment

### What Delivery Provides:
1. **The Exact Device Tree (`.dts` / `.dtsi`):** Complete physical memory mapping, peripheral register offsets, Broadcom crypto engine base addresses, and pinmux configurations.
2. **Broadcom Kernel BSP Drivers:** Full C source code for the Broadcom NAND controller, dm-crypt / dm-verity hooks, and storage layer.
3. **Build Recipes & Package Manifests:** OpenWrt / Homeware package configurations, revealing every compiled utility and configuration file template.
4. **CUPS & Network Daemons:** Exact build flags and compilation options for `cupsd`, validating memory limits and feature sets.

### What Delivery Does NOT Provide (Proprietary / Out-of-Scope under GPL):
1. Proprietary Broadcom binary blobs (e.g., closed-source Wi-Fi PHY blobs, `libr2secr.so`, `/bin/rip`).
2. Per-device secrets or encryption keys (no OSCK, no L598 AES key, no Telia mTLS client certificates).
3. Proprietary Vantiva Homeware management code (e.g., closed Lua scripts, GUI binary modules).

---

## 5. Strategic Recommendation

- **Dispatch Immediate:** Send the email above to `contact-ch.opensource@vantiva.com`.
- **Concurrency:** This request runs completely in the background without tying up bench time, equipment, or live device testing.
