# Research composite — what was tried, blocked, and open (2026-10-13)

Single index for **this unit** (Telia F1 / GCNT-X, **23.1.b**). Detailed evidence stays in linked findings; this file only records **status** and **gaps** that were easy to lose in chat.

## Bottom line

| Goal | Status |
| --- | --- |
| Decrypt saved `export_config` | **BLOCKED** — needs per-device `RIP_ID_RANDOM_KEY_B` ([hardware-key blocker](f1-hardware-key-blocker-2026-10-12.md)) |
| Root / shell via UART Linux console | **REFUTED** on this unit — Clash denies serial root ([UART interaction](f1-uart-interaction-2026-10-12.md)) |
| Auth bypass / key via Homeware :80 | **REFUTED** for mapped reads — boundaries + aggressive pass ([management-auth-boundaries](management-auth-boundaries-2026-10-12.md), [aggressive pass](f1-aggressive-software-pass-2026-10-12.md)) |
| BOOT-P on LAN wire | **VERIFIED** — requests, boot name **`GCNT-X`**, no server ([BOOT-P LAN](f1-bootp-lan-2026-10-13.md)) |
| BOOT-P **answer** from PC | **NOT TRIED** — tool ready: `scripts/f1-bootp-reply.ps1` |
| Signed RBI recovery / flash | **NOT TRIED** — no suitable 23.1.b Type-2 image in repo; 19.x flash **dangerous** ([gcnt-x-root-path](gcnt-x-root-path.md)) |

---

## Software (:80 and parallel ports)

| Work | Outcome | Canonical doc |
| --- | --- | --- |
| Normal admin SRP, export, `getbanksize`, session poll | Works | [software-pass-live-access](software-pass-live-access.md) |
| Unauth `getbanksize` / `scheduleReboot` / `export_config` | Login HTML only | [hidden-action boundary](f1-hidden-action-boundary-2026-10-12.md) |
| 119× rip/debug/action GET probe | No new JSON; **503** after | [hardware-key blocker](f1-hardware-key-blocker-2026-10-12.md) |
| Aggressive injection/SSRF (~40 cases) + stacked 49152/CUPS/8080 | No RCE/SSRF/key; **503** | [aggressive pass](f1-aggressive-software-pass-2026-10-12.md) |
| Gap pass: sched oracle, blind SSRF, offline export header | Done; no exploit | [gap pass](f1-gap-attack-pass-2026-10-12.md) |
| Gap pass: full auth matrix | **Abandoned** — duplicates boundaries; script **retired** (catalog only) | same |
| `f1_ipping_host_probe.py` (newline vs duplicate `ipAddress`) | **Never ran** — login stayed **503** in wait loop | [ipping host](f1-ipping-host-2026-10-12.md), `tried.md` |
| Multipart `import_config` / real `.rbi` upload | **Not sent** (brick risk) | [aggressive pass](f1-aggressive-software-pass-2026-10-12.md) |
| Stored XSS via device rename + second session | **Not sent** | same |
| `POST system_reboot` tooling | Script exists; not part of recovery track | `scripts/f1_system_reboot.py` |
| Session cookie reuse | Script exists; reduces SRP bursts | `scripts/f1_session_store.py` |

**Operational:** nginx **503** is sticky per client after bursts; prefer **no** stacked live scripts when UI is yellow. Physical reboot clears penalty faster than waiting.

---

## CUPS :631 / WFA :49152

| Work | Outcome | Doc |
| --- | --- | --- |
| IPP read matrix, Get-Jobs, policy probes | Reads OK; no queue create | [CUPS policy](f1-cups-ipp-policy-2026-10-12.md) |
| WFA SOAP, SUBSCRIBE, NOTIFY, M2 NACK | Measured; no enrollment exploit | [49152](f1-wfa-wlanconfig-49152-2026-10-12.md) |

---

## UART / boot / hardware

| Work | Outcome | Doc |
| --- | --- | --- |
| Boot log review (4.19.235, UBI, eripv2 messages) | No key possession | [boot log](f1-boot-log-2026-10-12.md) |
| `b` → BOOT-P, no Ethernet | `no active_port set` | [UART interaction](f1-uart-interaction-2026-10-12.md) |
| `b` → BOOT-P, Ethernet up, **no PC server** | `BOOTP Reply timeout` (UART) | same |
| Windows PC on LAN, **pktmon** + **Wireshark** listen | 17× BOOTREQUEST, file **`GCNT-X`**, no Offer | [BOOT-P LAN](f1-bootp-lan-2026-10-13.md) |
| `f1-bootp-reply.ps1` on Windows | **Prepared, not executed** | `scripts/f1-bootp-reply.ps1`, [BOOT-P LAN](f1-bootp-lan-2026-10-13.md) |
| Enter / `id` / Ctrl+J on Linux console | No shell; logviewer: serial denied | [UART interaction](f1-uart-interaction-2026-10-12.md) |
| Top-side PCB photo (`CN1`, `TEST_CN20`, `ANT*` vs `4G-ANT*`) | Documented | [board visual](f1-board-visual-2026-10-12.md) |
| Owner removed/reseated Wi‑Fi coax | **Not electrically tested** — reseat on **`ANT0`–`ANT3`**, not `4G-ANT*` | [board visual](f1-board-visual-2026-10-12.md) |

Private captures: `artifacts/bootp/2026-10-13/`, `artifacts/uart/2026-10-12/`, `artifacts/management/aggressive-*`, `gap-attack-*`.

---

## Crypto / offline

| Work | Outcome | Doc |
| --- | --- | --- |
| `THENC`/`GW` envelope + decrypt tooling | Format OK; **no RandB** | [config export decrypt](f1-config-export-decrypt-2026-10-12.md) |
| 71 OSCK / boot-log derivations on 19.x RBI | All `bad_osck` | [rbi-crypto-attempt3](rbi-crypto-attempt3.md) |
| `r2secr` 4.1.52 ko build | No match to **4.19.235** unit | [r2secr-build](r2secr-build-2026-10-12.md) |
| Telia `rgw` 19.5.1062 fetch | **403** | [hardware-key blocker](f1-hardware-key-blocker-2026-10-12.md) |

---

## Explicitly not tried (still the real queue)

1. **BOOT-P reply** — PC answers with `GCNT-X`, UART should show TFTP failure (no RBI).
2. **`f1_ipping_host_probe.py`** — one run when `/login.lp` is **200** (not during 503).
3. **Technicolor recovery server + signed GCNT-X RBI** — only after (1); wrong image bricks.
4. **Hardware key path** — `/proc/rip/0108` or eripv2 dump after root; NAND/JTAG/`TEST_CN20` map not done.
5. **Import/upload / stored XSS** — only with accepted brick/lab risk.

---

## Tools added this pass (not all exercised on device)

| Script | Role | Live used? |
| --- | --- | --- |
| `f1_pacing.py` | Login poll / gaps | Yes (gap/aggressive era) |
| `f1_gap_attack_pass.py` | **Retired** catalog | Was; now no LAN I/O |
| `f1_bootp-reply.ps1` | BOOTP OFFER, boot file `GCNT-X` | **No** |
| `f1_aggressive_software_pass.py` | Injection battery | Yes (evening 2026-10-12) |
| `f1_session_store.py` | Cookie reuse | Helper only |
| `f1_system_reboot.py` | `system_reboot` POST | Available, not recovery-critical |

---

## Evidence index (private)

| Path | Contents |
| --- | --- |
| `artifacts/bootp/2026-10-13/wan.pcapng` | Full Wireshark BOOT-P |
| `artifacts/bootp/2026-10-13/f1-bootp-2026-10-13.{txt,etl}` | pktmon |
| `artifacts/management/aggressive-20261012T191851Z/` | Aggressive pass |
| `artifacts/management/gap-attack-*` | Partial gap runs |
| `artifacts/ui/readonly-control-*` | Exports |
| `artifacts/secrets/f1-admin.*` | Credentials (gitignored) |
