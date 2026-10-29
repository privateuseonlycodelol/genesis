#!/usr/bin/env python3
"""Paced discovery probe of potential hidden Homeware modals."""
from __future__ import annotations

import time
import re
from pathlib import Path
from f1_session_store import ensure_admin_session
from f1_secrets import read_password_file

CANDIDATES = [
    "applications-modal.lp",
    "assistance-modal.lp",
    "asterisk-profile-modal.lp",
    "bridge-grouping-modal.lp",
    "certificates-list-modal.lp",
    "command-log-read-modal.lp",
    "customdns-modal.lp",
    "cwmpconf-modal.lp",
    "datausage.lp",
    "diagnostics-leds-modal.lp",
    "diagnostics-tcpdump-modal.lp",
    "diagnostics-xdsl-graphics-modal.lp",
    "diagnostics-xdsl-modal.lp",
    "dosprotect-modal.lp",
    "dumaos-modal.lp",
    "dyndns-modal.lp",
    "easy-mesh-configuration.lp",
    "eco-modal.lp",
    "fast-cache-option-modal.lp",
    "hostmap-modal.lp",
    "iproutes-modal.lp",
    "log-connections-modal.lp",
    "log-routingtable-modal.lp",
    "lte-doctor.lp",
    "lte-modal.lp",
    "mmpbx-service-modal.lp",
    "mmpbx-profile-modal.lp",
    "modem-stats-modal.lp",
    "modgui-modal.lp",
    "mwan-modal.lp",
    "nat-alg-helper-modal.lp",
    "nfc-modal.lp",
    "openvpn-server-modal.lp",
    "port-mirror-modal.lp",
    "printersharing-modal.lp",
    "qos-classify-modal.lp",
    "qos-queue-modal.lp",
    "relay-modal.lp",
    "speedservice-modal.lp",
    "system-cron-modal.lp",
    "system-init-modal.lp",
    "tailscale-modal.lp",
    "tod_dnd-modal.lp",
    "tod_wireless-modal.lp",
    "traffic-monitor.lp",
    "upnp-modal.lp",
    "usermgr-modal.lp",
    "wifi-extender-status.lp",
    "wifi-nurse-modal.lp",
    "wireguard-modal.lp",
    "wireless-client-modal.lp",
    "wireless-modal.lp",
    "wizard-modal.lp",
    "wol-modal.lp",
]

def main():
    pw = read_password_file("artifacts/secrets/f1-admin.password")
    client, how = ensure_admin_session(pw, base="http://192.168.1.1")
    print(f"Session established ({how})")

    results = []
    for cand in CANDIDATES:
        time.sleep(0.3)
        path = f"/modals/{cand}"
        try:
            code, body = client._open(client.base + path)
            title = ""
            m = re.search(r"<h2[^>]*>(.*?)</h2>", body.decode("utf-8", errors="replace"), re.I | re.S)
            if m:
                title = m.group(1).strip()
            elif b"<title>" in body:
                m2 = re.search(r"<title>(.*?)</title>", body.decode("utf-8", errors="replace"), re.I | re.S)
                if m2:
                    title = f"Title: {m2.group(1).strip()}"
            results.append((cand, code, len(body), title))
            if code == 200:
                print(f"[FOUND] {cand} -> HTTP {code} ({len(body)} B) title='{title}'")
        except Exception as e:
            results.append((cand, -1, 0, str(e)))

    print("\nSummary of discovered endpoints:")
    found = [r for r in results if r[1] == 200]
    for r in found:
        print(f"  {r[0]}: {r[3]}")

if __name__ == "__main__":
    main()
