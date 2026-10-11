# WAN capture analysis — `wan.pcapng`

**Analyzed:** 2026-10-11T06:05:00Z (worker re-check; local +0200)

## Sources

| Source | Status |
| --- | --- |
| **Cloud upload** (chat attachment) | Present for parent coordinator only — **not** on this worker filesystem. Parent run analyzes that file separately. |
| **`~/genesis/artifacts/captures/wan.pcapng`** | Present but **invalid** (see below). |

## Local `artifacts/captures/` inventory

| File | Size | mtime (local) | Type / frames |
| --- | ---: | --- | --- |
| `wan.pcapng` | 335 B | 2026-10-11 08:01 | **HTML 404**, **0** tshark frames |
| `want.pcapng` | 5,347,036 B | 2026-10-11 07:02 | pcapng, **49,846** frames / 266.7 s |
| `f1-reboot.pcapng` | 1,708 B | 2026-10-11 05:39 | pcapng, 8 frames |

## `wan.pcapng` on Mac — transfer failed

**Status:** The file at `artifacts/captures/wan.pcapng` is **not** a packet capture.

| Check | Result |
| --- | --- |
| `file` | `HTML document text, ASCII text` |
| Body | Python `http.server` **404 File not found** (`Error code: 404` / `Message: File not found.`) |
| `tshark -r wan.pcapng` | *The file isn't a capture file in a format TShark understands.* |
| Frame count | **0** |

The PC `curl` saved the HTTP error page, not `wan.pcapng` from disk (same failure as earlier 07:56 pull; file grew only by mtime refresh, still 335 B).

**Fix before re-analysis here**

1. On Windows, confirm **`wan.pcapng` on disk** is megabytes, not hundreds of bytes.
2. Serve from the directory that **contains** that file (`python -m http.server 8000`).
3. Browser-list `http://<PC-IP>:8000/` and confirm **`wan.pcapng`** appears.
4. `curl -o ~/genesis/artifacts/captures/wan.pcapng http://<PC-IP>:8000/wan.pcapng`
5. Verify: `file wan.pcapng` → **pcapng**, then re-run `./scripts/verify_mirror_pcap.sh artifacts/captures/wan.pcapng`.

## `verify_mirror_pcap.sh` on local `wan.pcapng`

| Step | Result |
| --- | --- |
| `./scripts/verify_mirror_pcap.sh artifacts/captures/wan.pcapng` | **Aborts** under `set -e`: `count_frames` returns empty (non-pcap input); no `findings/mirror-test.md` update for `wan.pcapng` |
| Effective verdict | **No mirror analysis possible** — zero decodable frames, F1 MAC **0** |

*(For comparison, the same script on `want.pcapng` prints **MIRROR OK** heuristically; manual review still shows mirror aimed at LAN — see `findings/want-pcap.md`.)*

## Until a valid `wan.pcapng` lands locally

- **Mirror evidence on disk:** only **`want.pcapng`** (~4.4 min SG108E mirror, 06:40–06:44 +0200).
- **Firmware strings / RBI URLs:** none in `want.pcapng`; F1 seen only as DHCP hostname `Telia F1-CP2242AD8AN` and 24 DHCP Discovers (details in `findings/want-pcap.md`).
- **Next step:** re-aim mirror + recapture, or rely on parent’s analysis of the **cloud-uploaded** WAN pcap if that file is the real capture.

## Verdict (local `wan.pcapng` only)

| Check | Result |
| --- | --- |
| Valid capture | **No** — HTML 404 stub |
| Mirror / WAN / firmware URL | **N/A** on this path |

**Summary:** Local `wan.pcapng` is still a failed HTTP download. Tshark and `verify_mirror_pcap.sh` cannot analyze it. Use the cloud upload (parent) or re-transfer a real pcapng; until then, `want.pcapng` remains the only usable mirror capture in `artifacts/captures/`.
