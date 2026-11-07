# Non-associated WiFi attack surfaces — wl driver audit, PMF/SAE live state — 2026-11-07

Attacker model: an **unassociated** peer with a radio in range of the F1 (GCNT-X, fw 23.1.b, wl driver 17.10.251.7305). No WiFi credentials, no association, no DHCP. Surface inventory and first-pass audit; live radio probes were blocked this pass (see end).

## Driver architecture (VERIFIED)

- Driver modules in the ROM copy at `lib/modules/4.19.235/extra/`: `wl.ko` (12,457,862 B, ELF aarch64, **not stripped** — SHA recorded in evidence), `dhd.ko` (1,950,982 B), `hnd.ko`, `wlshared.ko`, `wfd.ko`. Live `lsmod`: `wl` 8.9 MB resident, `dhd`, `wlshared`, `hnd`, `bcmlibs`, `bcm_knvram`, `wfd` all loaded; `cfg80211` binds `wl,dhd`.
- `wl.ko` version string **`17.10.251.7305`** — the BCM9685x-era wl 17.10 branch.
- **Full 802.11 stack is kernel-side**: 12,777 symbols with **5,275 `wlc_*`** (Broadcom 802.11 core) — this is not a firmware-only dongle; the frame parsing is in the auditable module. Split-MAC confirmed for auth: `wl_cfg80211_add_monitor_if`, `wl_cfg80211_recv_mgmt_frame`, `dhd_mon_if_*` — management frames are also forwarded to hostapd 2.10 via a monitor interface (its WPS parser was closed by the exhaustion pass; SAE commit crypto is hostapd's).

## Pre-association kernel-side parse surface (VERIFIED symbol addresses)

Frames an unassociated peer can send that reach kernel-side parser code:

| Surface | Symbol (addr) | Notes |
| --- | --- | --- |
| Probe requests (any client, any time) | `wlc_probresp_recv_process_prbreq` (0x3a9690) | AP-side probe-request processor; ~0x14c4 bytes |
| Scan result parsing (beacons/probe responses from fake APs — reachable because acsd2/afcd run background scans) | `wlc_recv_scan_parse` (0x3f8000), `wlc_recv_scan_parse_bcn_prb` (0x3f6d00), escan handlers `wl_escan_handler` (0x1edd50), `wlc_recv_scan_parse_handle_prb_resp_escan` | 2,696 insns walked |
| Public action frames (category 4 — coex/CSA/DPP family) | `wlc_recv_public_coex_action` (0x39d220), `wlc_recv_public_csa_action` (0x3040c0), `wlc_recv_csa_action` (0x304820), `wlc_recv_ext_csa_action` (0x3069b0), `wlc_recv_frameaction_specmgmt` (0x254890) | sendable pre-association |
| Auth-frame IE parse | `wlc_auth_parse_chlng_ie` (0x2a3780, 0x284640) | challenge-text IE in auth frames |
| MBO/OCE IE parse | `wlc_mbo_parse_ie` (0x1b7ee0) | parsed from received frames |
| mgmt forwarding | `wl_cfg80211_recv_mgmt_frame` (0x1dbac0) | split to hostapd |

## First-pass bug-class assessment (DERIVED)

- **HS2.0 scan IE parse is a stub** in this build: `wlc_hs20_scan_parse_ie` (0x33f8f0) is ~12 instructions that only set a capability flag bit — no IE walk, no copies. Not a surface.
- The four parsers opened this pass (`wlc_probresp_recv_process_prbreq`, `wlc_recv_scan_parse_bcn_prb`, `wlc_recv_public_coex_action`, `wlc_recv_csa_action`) all use the **post-2016 hardened pattern**: find-IE helper calls with length bounds, guarded reads (`cbz`/null checks after helpers), few bulk copies. Zero direct `memcpy` import calls inside the scan and action parsers; only 4 inlined 8-byte `ldp/stp` pairs in 2,696 scan-parser instructions.
- All 22 `bcm_copy_tlv`/`bcm_copy_tlv_safe` call sites (mapped via relocations) are in **IE writer** functions (`wlc_*_write_*_ie`, e.g. `wlc_11u_write_qos_map_ie`, `wlc_fbt_write_ft_ie`, `wlc_wds_write_multiap_ie`) — building **outgoing** frames, not parsing attacker input.
- 794 `memcpy` CALL26 relocation sites exist module-wide across 8,329 functions; a length-trust pattern (attacker IE length feeding a fixed-buffer copy) was **not found in the audited subset**, but the module is far too large for a permissive "no vulnerability" claim — this is a first-pass class assessment, not an audit verdict.

## Live PMF/SAE state (VERIFIED, captured before this pass lost router connectivity)

From the live hostapd configs on the device:

- `wl0` main BSS: `wpa_key_mgmt=WPA-PSK`, `ieee80211w=1` (**PMF optional**) — deauth/disassociation spoofing is *not* reliably blocked on this BSS.
- `wl0` second BSS (SAE/WPA3): `wpa_key_mgmt=SAE`, `ieee80211w=2` (**PMF required**), `sae_require_mfp=1`, **`sae_anti_clogging_threshold=5`** (anti-clogging active at threshold 5), `sae_sync=5`, `sae_groups=19 20 21`, **`sae_pwe=0`** (hunt-and-peck only — the mode the Dragonblood-class timing side channels target). A cleartext `sae_password` line exists in the live conf (root-readable only; value not reproduced here).
- `wl1`: `wpa_key_mgmt=WPA-PSK`, `ieee80211w=1` (PMF optional).
- Consequences (DERIVED): the PMF-optional BSSes remain exposed to classic unauthenticated deauth DoS (deferred test); the SAE BSS has anti-clogging (threshold 5) but the commit-processing cost is still attacker-influenceable pre-association, and H&P mode makes the timing side-channel class applicable in principle (REPORTED class; not measured here).

## What was blocked this pass

- **Live driver version confirmation (`wl ver`) and scanning-daemon state**: the router became unreachable from the lab Mac mid-pass (ping 100% loss; the Mac roamed to a foreign network with gateway 10.128.128.128) — consistent with the concurrent DPP agent's radio reconfiguration taking the F1's Wi-Fi down. No interference attempted, per coordination constraints.
- **Single-frame SAE/auth probes**: blocked twice over — no path to the router, and macOS raw 802.11 injection requires monitor mode with sudo (password required). Not sent.
- **Deferred on purpose until the DPP agent completes**: deauth-vs-PMF characterization on the PMF-optional BSSes, and any DPP responder/chirp listening probe outside the onboarding window.

## Highest-value follow-ups

1. The probe-request processor and scan parsers, audited in depth (multi-day) against attacker-length patterns — the surface map above is the entry-point inventory.
2. Deauth-vs-PMF test on the PMF-optional BSSes once radios are free.
3. SAE commit-cost measurement (anti-clog threshold behavior) from a Linux injection box.

**No packets were sent to the radios this pass. No router state was changed.**

Evidence: driver modules in the ROM tree (gitignored); symbol dump `/tmp/wl_syms.txt` + full disassembly `/tmp/wl_full.asm` (ephemeral, regenerable via `nm wl.ko` / `objdump -d wl.ko`).
