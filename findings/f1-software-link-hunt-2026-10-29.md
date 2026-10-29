# Software Link & Firmware Acquisition Architecture (2026-10-29)

## Executive Summary

An investigation was conducted to determine how the official software link (firmware download URL) for the Telia F1 / Vantiva GCNT-X (EWA1330) gateway on build `23.1.b` can be discovered, and whether any firmware links exist in local artifacts, logs, captures, or vendor infrastructure.

**Key Findings:**
1. **The Web UI has no remote software link (VERIFIED):** Static AST analysis via REA (`analyze_javascript_application`, evidence `ev_a62a9c86...`) and manual code review of `system-config-min.js`, `device-min.js`, and HTML modals confirm that the web GUI implements **no remote update check or URL retrieval**. The upgrade path is exclusively a local file upload (`#file-upgradefw` accepting `.rbi`, `.fw`, `.pkgtb` POSTed to `action=upgradefw`).
2. **Device syslog does not record firmware URLs (VERIFIED):** Analysis of the 596 exported router log rows (`artifacts/exports/2026-10-28-export-log-modal-once/response.bin`) confirms no CWMP, ACS, or `.rbi` download entries. The only recurring management process is `/usr/share/transformer/scripts/obuspa_retriever.sh` executed by `crond` every 60 seconds.
3. **Telia update distribution switched from static to dynamic token-based URLs (VERIFIED / REPORTED):**
   - Older 17.x–19.4 firmwares were hosted statically at `https://rgw.teliacompany.com:7547/<filename>.rbi` and `http://acs.telia.lt:8888/TCH/<filename>.rbi`. 21 candidate filenames for 23.1.b on port 7547 all returned `404 Not Found` (while control file `1940507x4581025.rbi` returned `206 Partial Content`).
   - Starting with 19.5, Telia migrated to dynamic, ephemeral tokenized URLs:
     `https://rgw.teliacompany.com:7577/cpe-r/p/<8-char-token>/<filename>.rbi`
     (verified from community traffic captures in hack-technicolor #321). Requests to port 7577 without a valid session token return `403 Forbidden`. The 8-character token ($62^8 \approx 2.18 \times 10^{14}$ space) is generated per-device on demand by the ACS during an encrypted TR-069/USP session over VLAN 254 (`vlan_mgmt`).
4. **Acquiring the raw RBI does not bypass decryption (DERIVED):** Even if an official 23.1.b RBI URL is intercepted, Technicolor RBIs are encrypted containers (OSCK). Offline trials (71 attempts documented in `findings/rbi-crypto-attempt3.md`) demonstrate that OSCK cannot be derived without a live device memory dump (`r2secr`). Physical flash extraction yields the already-decrypted rootfs directly.

---

## Technical Details & Evidence

### 1. Web UI Reverse Engineering via REA

Using REA's `analyze_javascript_application` on `artifacts/ui-grab-20261012T042131Z/files`:
- **Evidence ID:** `ev_a62a9c8613b5d5a45b8a0ed11b52545ffdff20269d19f15ae08cee421084b049`
- **Scope:** 220 relevant UI files, 24 parsed JavaScript files, 246,422 visited AST nodes.
- **Findings:**
  - `system-config-min.js:14-18`: Implements `wait_for_upgradefw()`, querying `action=getbanksize` and `action=upgradefwstatus`.
  - The upgrade handler binds `.upgradefw` click event to an `<input type="file" id="file-upgradefw">`.
  - Validates file extensions client-side against `["rbi", "fw", "pkgtb"]`.
  - Dispatches multipart form data to `/gateway.lp` with `action=upgradefw` and `CSRFtoken`.
  - **Verdict:** There is no client-side API call or configuration variable containing an external firmware repository URL or OTA software link.

### 2. Live Device Log Export Analysis

- **Artifact:** `artifacts/exports/2026-10-28-export-log-modal-once/response.bin` (71,954 bytes, 596 syslog lines).
- **Process Breakdown:**
  - `crond`: 199 invocations.
  - `restricted_shell`: 199 invocations logging `User root is connecting through Crontab...` paired with `/usr/share/transformer/scripts/obuspa_retriever.sh`.
  - `netifd`: Periodic DHCP renewals on `wan` (`Switching to renewing` / `Switching to bound` to CGNAT `100.77.193.145` every 15 minutes).
  - `trafficmon-ubus`: Hourly sweeps monitoring interfaces `wan`, `mgmt`, `voip`, and `iptv`.
- **Verdict:** No TR-069 (`cwmpd`) or USP (`obuspa`) session events, server URLs, or file transfer requests are written to user-accessible syslog.

### 3. Telia Firmware Host Architecture & Enumeration Limits

| Host & Port | URI Pattern | Auth / Access | Status on 23.1.b |
| :--- | :--- | :--- | :--- |
| `rgw.teliacompany.com:7547` | `/<filename>.rbi` | Public / None | **VERIFIED 404** (21 candidate names tried; 19.4 control returns 206) |
| `acs.telia.lt:8888` | `/TCH/<filename>.rbi` | IP / Host restriction | **INCONCLUSIVE** (TCP connects, no HTTP reply within 15 s) |
| `rgw.teliacompany.com:7575` | `/ACS-server/ACS` | CWMP TLS Client Cert | Management endpoint (not a file host) |
| `rgw.teliacompany.com:7577` | `/cpe-r/p/<token>/<filename>` | 8-character session token | **VERIFIED 403** without token; token generated dynamically by ACS |

In issue #321 comment 24, contributor `pierretu` captured the exact URLs pushed during an update of an EWA1331 unit:
```text
https://rgw.teliacompany.com:7577/cpe-r/p/tZLIYj9o/EWA1331_EWA1330_gcnt_x_19.5.1062_4581010_unified.rbi
https://rgw.teliacompany.com:7577/cpe-r/p/mHwA0Rb9/mapag.sts
https://rgw.teliacompany.com:7577/cpe-r/p/sW5UAZFd/NsecondGenTechSsh.sts
https://rgw.teliacompany.com:7577/cpe-r/p/inrJ7MN4/TechnicolorSyslog.sts
https://rgw.teliacompany.com:7577/cpe-r/p/i1SQxgUr/pmfOff.sts
```
Because each update file uses a distinct 8-character pseudo-random token in `/cpe-r/p/<token>/`, the download link cannot be discovered by static URL guessing. It is delivered dynamically inside the encrypted management session between Telia's ACS/USP controller and the router.

### 4. Forum Intelligence & ACS Cryptographic Hardening

A survey of European telecom forums (SweClockers Sweden, Il Punto Tecnico Italy, Telia Finland Yhteisö) and community repositories revealed the following critical operational facts:

1. **Serial-Targeted Rollouts (REPORTED, Telia Finland Community):**
   - In thread `yhteiso.telia.fi/kiinteae-netti-8/...-38013`, Telia service engineers confirmed that F1 / F1x gateway updates are deployed selectively based on **device serial numbers** queued in the ACS database. Users cannot manually request or trigger firmware downloads from the UI or external links.
2. **Mutual TLS (mTLS) Prevents ACS Emulation & MitM (VERIFIED / REPORTED):**
   - The Homeware CWMP daemon configuration (`/etc/config/cwmpd`, confirmed by `NI-Pro` in hack-technicolor #321) enforces strict mutual authentication:
     ```uci
     config single_config 'cwmpd_config'
             option state '1'
             option upgradesmanaged '1'
             option ssl_verifypeer '1'
             option enforce_https '1'
             option ssl_clientcert '/proc/rip/011a.cert'
             option ssl_clientkey 'engine:keystore:/proc/keys/0x11A'
             option interface 'mgmt'
     ```
   - Both client and server certificates are strictly verified:
     - The client certificate is read from the Broadcom eRIP flash partition (`/proc/rip/011a.cert`).
     - The client private key is protected by the SoC hardware keystore engine (`engine:keystore:/proc/keys/0x11A`).
   - This explains why attempts to spoof the ACS via local DNS redirection / fake GenieACS instances (a method previously attempted on TIM HUB+ DGA4331 routers on Il Punto Tecnico topic 84353) terminate immediately with `SSL connect failed`.
3. **Web UI Gaps vs. Shell Security (REPORTED, SweClockers Sweden):**
   - Discussions on SweClockers (`trad/368817`) by Swedish researcher `wuseman` confirmed that although hidden administrative modals (`modals/easymesh-configuration-modal-newEM.lp`) allow changing DNS parameters, the underlying backend remains protected by `restricted_shell` and `clash-access-control` (`User root has no serial access`), preventing privilege escalation from the browser alone.

---

## 4 Viable Vectors to Acquire the Software Link or Firmware

Given that static URL guessing is architecturally ineffective, the following four vectors represent the only technically viable methods to acquire the 23.1.b software link or firmware:

### Vector 1: Passive WAN Interception (Network Capture)
- **Concept:** Place an inline network tap or transparent dual-NIC Ethernet bridge (e.g. Linux `br0` on two gigabit interfaces) on the WAN port between the ONT/wall socket and the F1 router.
- **Mechanism:** During boot or periodic inform intervals, monitor outbound traffic on both untagged WAN and 802.1Q tagged VLAN 254 (`vlan_mgmt`).
- **Target Data:**
  - DNS lookups for Telia ACS/firmware hosts.
  - HTTP/HTTPS GET requests to `:7577` containing the `/cpe-r/p/<token>/<filename>` URI.
- **Constraints / Risks:**
  - Using a managed switch mirror port (like the TP-Link TL-SG108E tested previously) corrupted DHCP frames and broke internet connectivity (`findings/f1-internet-outage-2026-10-28.md`). A dedicated passive hardware tap or non-interfering Linux bridge is required.
  - If Telia pushes a firmware upgrade, capturing the download will also flash the router.

### Vector 2: Physical Hardware Read of Parallel SLC NAND (Recommended)
- **Concept:** Read the onboard KIOXIA **TC58NVG2S0HTAI0** parallel NAND flash chip (TSOP-48, 3.3V) directly using an external programmer.
- **Why this beats the software link:**
  - The software link only yields an **encrypted `.rbi` container**, which cannot be decrypted without extracting the OSCK from runtime memory.
  - In contrast, the NAND flash contains the **unencrypted running rootfs** (`rootfs1` / `rootfs2` SquashFS), the signed kernel/FIT image, and the bootloader already unpacked.
- **Hardware needed:** A universal programmer supporting parallel NAND TSOP-48 (e.g. XGecu T48 / TL866II Plus with TSOP-48 socket adapter) or an in-circuit clip with the SoC held in reset.

### Vector 3: Formal GPL Source Code Request to Vantiva (Open Source Compliance)
- **Concept:** The Linux kernel (4.1.52), BusyBox, dnsmasq, hostapd, and related network packages used in build `23.1.b.0448` are licensed under GNU GPLv2.
- **Action:** Submit an official GPL source code request to Vantiva's compliance desk:
  - **Email:** `contact-ch.opensource@vantiva.com` (published in Vantiva's official `EWA1330TCS_19.4_external-1.pdf`).
  - **Requested Item:** Complete corresponding source code and BSP configuration for **Vantiva GCNT-X (EWA1330 / EWA1331) firmware build `23.1.b.0448`**.
- **Yield:** Broadcom BCA driver headers, kernel patches, partition layouts, and device tree sources.

### Vector 4: Operator & Research Community Collaboration
- **Concept:** Community researchers (e.g. `pierretu`, `wuseman`, `NI-Pro`) on GitHub issue #321 and Swedish forums (SweClockers) actively track Telia firmware releases.
- **Action:** Inquire in open research channels if any user on Telia Sweden or Lithuania with an active fiber connection captured the `23.1.b.0448` update payload or retains an offline copy of the unified RBI.

---

## What Was Not Shown

- No working 23.1.b download link was discovered in public web searches or static URL probing.
- No live update session was intercepted in current captures.
- No OSCK decryption key for 23.1.b was obtained.
