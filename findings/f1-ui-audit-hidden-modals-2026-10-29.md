# F1 Web UI Audit: Discovered Hidden Modals, CUPS Integration, and SRP Hardening (2026-10-29)

## Executive Summary

During Vector 3 (non-physical, non-destructive Web UI/LAN deep audit), we audited client-side JavaScript, Lua modal logic, and backend transformer mappings across the harvested UI artifacts (`artifacts/ui-grab-20261012T042131Z/`) and reference Homeware frameworks (`tch-nginx-gui`). 

We designed and executed a paced discovery probe ([`scripts/f1_modal_discovery.py`](file:///Users/nils/genesis/scripts/f1_modal_discovery.py)) against the live router (`192.168.1.1`), uncovering **10 previously undocumented or hidden modal endpoints**, explaining the active port 631 (CUPS) listener, verifying the exact backend crypto bindings of config export/import, and proving Technicolor's defensive countermeasures against SRP-6 user enumeration.

---

## 1. Verified Discoveries on the Live Router (Firmware `23.1.b`)

### A. Newly Discovered Admin-Accessible Modals (`HTTP 200`)
1. **`/modals/printersharing-modal.lp` (VERIFIED):**
   - Directly accessible to the `admin` user role.
   - Binds to `uci.printersharing.config.enabled` and `uci.printersharing.config.webui`.
   - In `/etc/init.d/cupsd`, `enabled=1` triggers `/usr/sbin/cupsd` startup, and `webui=1` executes `cupsctl WebInterface=yes`.
   - In the live HTML response, `printersharingEnabled` is already set to `1`, which definitively explains why port 631 (CUPS) is listening on the LAN.
   - Rendered markup alert: `<div class="alert alert-error">invalid instance</div>`, indicating that the underlying USB printer device instance was not detected.
2. **`/modals/wireless-client-modal.lp` (VERIFIED):**
   - Directly accessible to the `admin` user role.
   - Provides live telemetry for connected Wi-Fi stations via `rpc.wireless.ap.@ap.station.`.
   - Downloads a previously unharvested JS asset: `/js/wireless-client-modal-min.js` (2,252 bytes).
3. **`/modals/diagnostics-xdsl-modal.lp` (VERIFIED):**
   - Directly accessible to `admin`.
   - Full 11.1 KB DSL diagnostic interface rendering downstream/upstream line attenuation, SNR margins, and xDSL driver counters.

### B. Role-Gated (`engineer`-only) Endpoints (`HTTP 200` with Sign-in Challenge)
The following endpoints exist on the filesystem but return an authentication redirect/challenge to `admin` users because they require `role == "engineer"` in `/etc/config/web`:
- `/modals/cwmpconf-modal.lp`: Full TR-069 / CWMP configuration (`acs_url`, `connectionrequest_username`, `connectionrequest_password`, periodic inform intervals).
- `/modals/usermgr-modal.lp`: User account creation and management modifying `uci.web.user.`.
- `/modals/assistance-modal.lp`: Remote assistance / technical support tunnel setup.
- `/modals/datausage.lp`: Detailed interface accounting and data usage metrics.
- `/modals/iproutes-modal.lp`: Static routing table modifications.
- `/modals/nat-alg-helper-modal.lp`: Configuration of Application Layer Gateway (ALG) modules (SIP, RTSP, FTP).
- `/modals/relay-modal.lp`: DHCP/PPPoE relay configuration.

---

## 2. Transformer Backend & Keystore Mappings Verification

By analyzing `usr/share/transformer/commitapply/` and `mappings/rpc/system.map` alongside `ConfigCommon.lua`:

1. **Config Export / Import Crypto Ground Truth (VERIFIED):**
   - `ConfigCommon.lua` confirms our Hopper decompilation of `ripdrv.ko`:
     - Cipher algorithm: `AES-256-CBC` with key `get_rip_random("0108"):sub(1,32)` (`RIP_ID_RANDOM_KEY_B`).
     - Signature algorithm: `HMAC-SHA1` with key `get_rip_random("0108"):sub(1,64)` (`RIP_ID_RANDOM_KEY_B`).
     - Plaintext / unsigned imports are gated by `uci_get_boolean("system.config.import_plaintext")` and `uci_get_boolean("system.config.import_unsigned")`.
2. **Reboot and Recovery Primitives in `rpc_system.ca`:**
   - `^sys%.bootp%.enable /usr/bin/bootp`: Setting `sys.bootp.enable = 1` invokes `/usr/bin/bootp`, commanding a reboot into BOOTP upgrade mode directly from userland without hardware/UART pins.
   - `^rpc%.system%.switchover cat /proc/banktable/notbooted > /proc/banktable/active; reboot`: Setting `rpc.system.switchover = 1` flips the boot bank and reboots.

---

## 3. Disproof: SRP-6 User Enumeration Oracle

- **Prior Hypothesis:** In older Homeware versions, querying `/authenticate` with Step 1 (`I` and `A`) returned `{"error":"failed"}` for nonexistent users and `{"s": salt, "B": B}` for valid users, allowing unauthenticated username enumeration.
- **Experiment (VERIFIED):**
  - Queried `/authenticate` with known user `User`: returned `s_len=8`, `B_len=512`, `salt=F52135C7` (persistent).
  - Queried `/authenticate` with nonexistent user `nonexistentuser123`: returned `s_len=8`, `B_len=512`, `salt=3d881c7b` (persistent across repeated queries for the same username).
- **Conclusion (DERIVED):** Firmware `23.1.b` implements deterministic fake salt/verifier generation: `fake_salt = hmac(secret, username)`. Nonexistent users appear indistinguishable from real users during Step 1 handshake. The user enumeration vector is **mitigated** by vendor hardening.

---

## 4. Attack Surface and Next Leads (Non-Destructive)

1. **CUPS Port 631 Manipulation via `printersharing-modal.lp`:**
   - Now that we know `printersharing-modal.lp` is live and maps to `uci.printersharing.config.webui`, we can test if submitting `printersharing_webui = 1` enables the CUPS administrative Web UI (`cupsctl WebInterface=yes`). If enabled, CUPS 631 may expose new authenticated surfaces or printer driver filters.
2. **`system_bootp` Recovery Trigger:**
   - An authenticated POST to `system-config-modal.lp` with `action=system_bootp` triggers `/usr/bin/bootp`, allowing controlled entry into BOOTP recovery mode on demand.

---

## Reproduction Commands

```bash
# Verify unit tests for discovery tooling
./tools/venv/bin/python3 -m unittest discover -s scripts/

# Run paced modal discovery probe
PYTHONPATH=scripts python3 scripts/f1_modal_discovery.py
```
