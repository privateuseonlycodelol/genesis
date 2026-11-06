#!/usr/bin/env python3
"""Execute web management triage via authenticated session on Telia F1 / GCNT-X.

Extracts live diagnostics, system telemetry, and administrative configuration
from the running web management interface (port 80) using the active admin session.
Paced requests to prevent nginx 503 rate-limiting.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from f1_session_store import ensure_admin_session  # noqa: E402

PASSWORD_FILE = ROOT / "artifacts" / "secrets" / "f1-admin.password"
BASE = "http://192.168.1.1"

DIAGNOSTIC_TARGETS = [
    ("session_status", "/gateway.lp?auto_update=true&getSessionStatus=true", "GET"),
    ("schedule_reboot", "/gateway.lp?action=scheduleReboot", "GET"),
    ("bank_size", "/modals/system-config-modal.lp?action=getbanksize", "GET"),
    ("system_info", "/modals/system-info-modal.lp", "GET"),
    ("broadband", "/modals/broadband-modal.lp", "GET"),
    ("devices", "/modals/device-modal.lp", "GET"),
    ("diag_connection", "/modals/diagnostics-connection-modal.lp", "GET"),
    ("diag_network", "/modals/diagnostics-network-modal.lp", "GET"),
    ("diag_igmpproxy", "/modals/diagnostics-igmpproxy-modal.lp", "GET"),
    ("diag_ping", "/modals/diagnostics-ping-modal.lp", "GET"),
    ("time_management", "/modals/time-management-modal.lp?getNTP=true&auto_update=true", "GET"),
    ("cwmp_conf", "/modals/cwmpconf-modal.lp", "GET"),
    ("user_mgr", "/modals/usermgr-modal.lp", "GET"),
    ("printer_sharing", "/modals/printersharing-modal.lp", "GET"),
    ("content_sharing", "/modals/contentsharing-modal.lp", "GET"),
    ("vpn_server", "/modals/l2tp-ipsec-server-modal.lp", "GET"),
]


def clean_html_text(html: str) -> str:
    """Extract readable key-value or label text from HTML snippet."""
    text = re.sub(r"<script.*?</script>", "", html, flags=re.DOTALL | re.I)
    text = re.sub(r"<style.*?</style>", "", text, flags=re.DOTALL | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def run_triage(base: str, pace_sec: float = 2.0, out_dir: Path | None = None) -> dict[str, dict]:
    if out_dir is None:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        out_dir = ROOT / "artifacts" / "triage" / f"web-admin-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    password = PASSWORD_FILE.read_text().strip()
    client, how = ensure_admin_session(password, base=base)
    del password
    print(f"[*] Admin session established ({how}) on {base}")

    results = {}
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(client.jar))

    for label, path, method in DIAGNOSTIC_TARGETS:
        url = base + path
        print(f"[*] Fetching [{label}] from {path}...")
        req = urllib.request.Request(url, method=method)
        req.add_header("Referer", base + "/gateway.lp")
        try:
            with opener.open(req, timeout=15) as resp:
                code = resp.getcode()
                headers = dict(resp.headers)
                data = resp.read()
        except urllib.error.HTTPError as err:
            code = err.code
            headers = dict(err.headers)
            data = err.read()
        except Exception as e:
            code = -1
            headers = {}
            data = str(e).encode()

        raw_path = out_dir / f"{label}.raw"
        raw_path.write_bytes(data)

        # Attempt JSON parse or text extraction
        parsed_json = None
        text_summary = ""
        try:
            parsed_json = json.loads(data.decode("utf-8"))
        except Exception:
            text_summary = clean_html_text(data.decode("utf-8", errors="replace"))

        results[label] = {
            "path": path,
            "status": code,
            "content_type": headers.get("Content-Type", ""),
            "bytes": len(data),
            "json": parsed_json,
            "text_preview": text_summary[:1000] if text_summary else "",
        }
        print(f"    Status {code}, {len(data)} bytes ({headers.get('Content-Type', '')})")
        time.sleep(pace_sec)

    summary_file = out_dir / "triage_summary.json"
    summary_file.write_text(json.dumps(results, indent=2), encoding="utf-8")
    client.save_jar()
    print(f"[+] Web management triage completed. Saved to {out_dir}")
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=BASE, help="Router base URL")
    parser.add_argument("--pace", type=float, default=2.0, help="Pacing sleep between requests (seconds)")
    args = parser.parse_args()

    results = run_triage(base=args.base, pace_sec=args.pace)
    print("\n--- Diagnostic Findings Summary ---")
    for label, info in results.items():
        st = info["status"]
        if info["json"]:
            print(f"[{label}] (HTTP {st}): JSON {info['json']}")
        else:
            first_line = info["text_preview"].splitlines()[0] if info["text_preview"] else "empty"
            print(f"[{label}] (HTTP {st}): {first_line[:80]}...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
