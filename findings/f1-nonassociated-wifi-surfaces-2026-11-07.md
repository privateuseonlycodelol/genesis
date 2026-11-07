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
- The four parsers opened in the first pass use find-IE helpers with length bounds and guarded reads. That pass reported no `memcpy` relocation inside the probe-request processor. The later relocation walk supersedes that for this function: it has eight `memcpy` sites, and the SSID-length ones are clamped (see below). The scan and public-action parsers were not re-walked.
- All 22 `bcm_copy_tlv`/`bcm_copy_tlv_safe` call sites (mapped via relocations) are in **IE writer** functions (`wlc_*_write_*_ie`, e.g. `wlc_11u_write_qos_map_ie`, `wlc_fbt_write_ft_ie`, `wlc_wds_write_multiap_ie`) — building **outgoing** frames, not parsing attacker input.
- 794 `memcpy` CALL26 relocation sites exist module-wide across 8,329 functions; a length-trust pattern (attacker IE length feeding a fixed-buffer copy) was **not found in the audited subset**, but the module is far too large for a permissive "no vulnerability" claim — this is a first-pass class assessment, not an audit verdict.

## Live PMF/SAE state (VERIFIED)

First read was cut off when the lab Mac lost the router. Re-read 2026-11-07 05:13 local, read-only SSH, uptime 36 min, no radio frames sent. This supersedes the earlier "wl0 second BSS is SAE" note: SAE is `wl0.2`, the backhaul, and `wl0.1` is another PSK client BSS.

From `/tmp/wl0_hapd.conf` and `/tmp/wl1_hapd.conf` (password and PSK lines counted, not printed):

- `wl0` and `wl0.1`: `wpa_key_mgmt=WPA-PSK`, `ieee80211w=1` (**PMF optional**), SSID `Telia-C66283`. Deauth/disassociation spoofing is not reliably blocked on these BSSes.
- `wl0.2`: `wpa_key_mgmt=SAE`, SSID `BH-C66283`, `ieee80211w=2` (**PMF required**), `sae_require_mfp=1`, **`sae_anti_clogging_threshold=5`**, `sae_sync=5`, `sae_groups=19 20 21`, **`sae_pwe=0`** (hunt-and-peck). A cleartext `sae_password` line exists (root-readable only; value not reproduced).
- `wl1` and `wl1.1`: `wpa_key_mgmt=WPA-PSK`, `ieee80211w=1` (PMF optional), SSID `Telia-C66283`.
- `wl ver`: `17.10.251.7305` (r), FWID `01-73359306`, built Jan 6 2025. Same version string as the ROM `wl.ko` audit. `acsd2` was running (pid 6823). No `afcd` and no `wpa_supplicant` in the process list.
- Channels at that read: `wl0`/`wl0.1` `36/160` (5180 MHz); `wl1` channel 11 (2462 MHz). `hostapd_cli status` on the `wl0` process: client BSSes had one station each; `BH-C66283` had zero.
- Consequences (DERIVED): the four PSK BSSes remain exposed to classic unauthenticated deauth DoS (still not sent; it would drop the lab client). The backhaul SAE BSS has anti-clogging at threshold 5. Commit cost was not measured. Hunt-and-peck is the Dragonblood timing class in principle (REPORTED class; not measured here).

## What stayed blocked

- **Single-frame SAE/auth probes and deauth-vs-PMF**: not sent. This Mac has no monitor-mode injection path that stays on our BSS only, and a deauth would drop the lab client that the SSH session is using. Anti-clog cost is still unmeasured.
- The mid-pass reachability loss (Mac roamed to gateway 10.128.128.128 while a DPP radio attempt reconfigured the F1) is historical. The 05:13 re-read above is the live state after recovery.

## DPP outside the onboarding window (VERIFIED read-only + ROM disassembly)

Same 05:13 SSH session, then a second read-only sweep. No `dpp_listen`, `dpp_chirp`, or `dpp_auth_init` was issued.

- `nvram` `wl0_dpp_role`, `wl1_dpp_role`, and `dpp_started` were empty. `wl0_mode` and `wl1_mode` were `ap`.
- `hostapd_cli dpp_bootstrap_info` and `dpp_configurator_get_key` for ids 0–8 on `wl0` and `wl1` all returned FAIL. Nothing was enrolled. `wps_pbcd` was running (pid 6902) with the role gate unset, which the earlier plumbing demo showed skips the `system()` site.

ROM `usr/sbin/hostapd` (sha256 `875f3bad42fa1addf2d10bf4f466f2f520c4b5be8b9ab85e6c7e5c1b19adf00d`, ARM, stripped) handles DPP public action frames and then drops them when no bootstrap object matches:

- Authentication Request path at `0xe80c0`: loads attribute id `0x1001`, requires a 32-byte value, calls `0xd61dc`, and `beq`s to `0xe86e8` when the returned pointer is null. `0xe86e8` logs `No matching own bootstrapping key found - ignore message` and returns. Attribute `0x1001` is hostapd's initiator bootstrap-key hash (DERIVED from that constant plus this control flow).
- Presence Announcement path at `0xe7e70`: if an exchange object is already stored at the context `+0x14`, it logs `Ignore Presence Announcement during ongoing Authentication` and returns. Otherwise it loads attribute id `0x1002`, requires 32 bytes, calls `0xd632c`, and `beq`s to `0xe86c0` (`No matching bootstrapping information found`) when the lookup is null. Only a hit continues into `0xd8cc4`.
- A second Presence Announcement site (`cmp` against frame type 13 at `0xecd58`) drops the frame when the word at `[bss+8]+0x72c` is nonzero and bit 1 is clear (`tst` / `beq` to `0xeda78`), logging `Ignore Presence Announcement … on Non Fronthaul BSS`. A zero word skips that drop. The live value of that word was not read.

**DERIVED:** with an empty bootstrap list, an unassociated DPP Authentication Request or chirp is parsed far enough to hash-match and then ignored. It does not start an exchange, so it does not reach `wps_pbcd`'s connector applier. That is the outside-onboarding state on this unit right now. It is not a test of a user-opened onboarding window, and no over-the-air frame was sent.

## SAE commit handling (DERIVED from the running binary; no frame sent)

hostapd is `driver=nl80211`. SAE commit crypto is in that binary, not in `wl.ko` (`wl -i wl0.2 cap` includes `sae`; the module's SAE symbol is `wlc_akm_is_sae_h2e_enabled`, a capability check).

ROM hostapd, same sha256 as above:

- `sae_anti_clogging_threshold` is `strtol` base 10, stored at `conf+0x600` (`0x1db64`). The auth path loads that word. If it is greater than the count of SAE states 1 and 2 (plus a second list at `hapd+0x8bc`), execution continues into commit processing (`bhi` to `0x105ea8`). If the count has reached the threshold, it falls through to the `SAE: Request anti-clogging token` log at `0x106504`, unless register `sl` is nonzero, which also continues the commit. The live conf sets the key to 5. What `sl` represents was not tied to a field. The on-air status code was not observed.
- A group that is not enabled hits `SAE: Proposed group %u not enabled in the current configuration` and then `mov r0, #0x4d` (`0x85a14`). `0x4d` is 77, the 802.11 "finite cyclic group not supported" status. The live enabled groups are 19, 20, and 21.

**Why no frame was sent (BLOCKED).** One directed authentication frame to `8a:b5:3c:c6:52:85` would not be processed by a neighboring AP, but this lab cannot emit it. `sudo -n` on the Mac asks for a password, so there is no monitor interface. The router has no monitor netdev. `wl1` channel list is 1–13, and the SAE BSS is on channel 36, so the 2.4 GHz radio cannot address it. An AP transmit does not re-enter that AP's receive path. No authentication frame was transmitted.

## Probe-request SSID copies and the challenge IE (VERIFIED in wl.ko)

`wlc_probresp_recv_process_prbreq` (`0x3a9690`, 0x14d8 bytes) has eight `memcpy` relocations. The copies that take the probe SSID length byte (`ldrb` of IE offset 1) compare it with 32 and `csel` the smaller value before the copy (`0x3a9948`, `0x3a9c80`, `0x3aa024`). Two further copies reject a length above 44 (`cmp` / `b.hi` at `0x3aa268` and `0x3aa518`) instead of copying it. Two later copies use a stack byte at `sp+0x11c` / `sp+0xec` whose producer was not fully traced.

`wlc_auth_parse_chlng_ie` at `0x284640` does `memcpy` of the IE length byte with no `min` in that function, and only after a parsed word equals 1 and the word at `+4` equals 3. Those constants match shared-key authentication algorithm 1, transaction 3 (DERIVED). A SAE commit uses algorithm 3, which fails the first compare and returns without copying. The sibling at `0x2a3780` stores a pointer and does not copy. Destination size for the shared-key copy was not measured, and no shared-key frame was sent.

## Scan and action parsers (VERIFIED in wl.ko, 2026-11-07 follow-up)

Relocation walk of the functions named in the surface table. No frame was sent.

- `wlc_recv_scan_parse_bcn_prb` (`0x3f6d00`, 0x438 bytes) and `wlc_recv_scan_parse` (`0x3f8000`, 0x4bc bytes) have **no** `memcpy` relocation. The beacon/probe-response path calls `bcm_find_tlv`, `wlc_iem_parse_frame`, and the MBSSID helpers. A direct "copy IE length into a fixed buffer" site is not in these two functions.
- `wlc_recv_ext_csa_action` (`0x3069b0`) is a single `ret`. An extended CSA action frame is not parsed by this symbol.
- `wlc_recv_public_csa_action` and `wlc_recv_public_coex_action` have no `memcpy`. Public CSA uses `bcm_find_tlv_min_bodylen`. Coex uses `bcm_find_tlv`.
- `wlc_recv_csa_action` has one `memcpy` at `0x306090`. Immediately before it, `len+6` is compared with `end-cursor` and a `b.gt` skips the copy when the span is too small. The copied count is `len & 0xff`.
- `wlc_multibssid_recv_nontransmitted_ssid_bssid` (called from the scan parser) has no `memcpy`; it calls `bcm_find_tlv` seven times.
- `wlc_multibssid_recv_preprocess_bcn` (`0x3845a0`) allocates with `osl_mallocz`. The main buffer size is argument 4 minus 12 (`0x384698`). The running output offset at `sp+0x68` is stored as zero before the walk (`0x3847b0`). Three copies are bounded by that allocation:
  - `0x3847c8`: an element is not consumed when `IE_len+2` is greater than the remaining allocation (`cmp` / `b.gt`).
  - `0x3849b8`: copy length is `(IE_len+2)` masked to 8 bits, and the copy is skipped when that exceeds allocation minus offset (`b.lo`).
  - `0x384cd4`: copy length is `IE_len+2`, skipped when that exceeds allocation minus offset (`b.hi`).
  - `0x384ad8`: the input remainder is initialized to the allocation size (`0x384a90`), and the loop copies an element only after `remainder >= IE_len+2`. The sum copied cannot exceed the allocation.
- The multiple-BSSID element path (tag `0x47`, `0x384b98`) allocates the sum of two length bytes and then copies argument-1-masked-to-8-bits plus the second length byte. Those two lengths were not shown to be the allocation size. No overflow was established. No beacon was sent.

## SAE frame send, second look (BLOCKED)

`iw` on the device is 4.1. Its authenticate command is `dev <devname> auth <SSID> <bssid> <type:open|shared> <freq>`. It has no SAE commit type. The phy reports "Device supports SAE with AUTHENTICATE command" and allows a managed vif beside the APs (`#{ AP } <= 8, #{ managed } <= 4`), but this `iw` cannot build the commit, and no vif was added. `wl pkteng`, `wl send_frame`, and `wl sae` are unsupported. `wl auth` and `wl monitor` with no argument printed `0` (getters). Afterwards hostapd on `wl0` was still `ENABLED` on channel 36 with the same station counts, uptime 50 min. No authentication frame was transmitted.

## Highest-value follow-ups

1. The tag-`0x47` allocation in `wlc_multibssid_recv_preprocess_bcn` (`w27+w28`) is the one copy pair whose length is still a different register from the allocation size.
2. Deauth-vs-PMF on a PMF-optional BSS from an injector that is not the lab client's only link.
3. One SAE commit (unknown group, then a supported group) from a host whose `iw` can send SAE authenticate, aimed at `BH-C66283` / `wl0.2` only. This device's `iw` 4.1 cannot.

**No packets were sent to the radios. No router state was changed.** The 05:13 session was read-only SSH (`wl ver`, `nvram get` of the DPP role keys, `hostapd_cli status` / bootstrap queries).

Evidence: driver modules in the ROM tree (gitignored); symbol dump `/tmp/wl_syms.txt` + full disassembly `/tmp/wl_full.asm` (ephemeral, regenerable via `nm wl.ko` / `objdump -d wl.ko`).
