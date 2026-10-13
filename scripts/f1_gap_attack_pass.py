#!/usr/bin/env python3
"""Closed gap catalog — does not probe the router.

The live phases this file used to run are already recorded. Re-sending them
only burns the nginx 503 budget. This entrypoint prints that catalog and exits.

Closed (do not repeat):
  auth       session / banksize / scheduleReboot / export / QR auth boundaries
  sched      scheduleReboot oracle after schedulerebootset
  blind_ssrf gateway.lp action=URL callback listener
  services   :80 / :631 / :8080 / :49152 reachability
  offline    THENC export header on a saved envelope

Still open, in other scripts:
  scripts/f1_ipping_host_probe.py
"""
from __future__ import annotations

import json

# phase, status, where the result lives
CLOSED = (
    (
        "auth",
        "closed",
        "findings/management-auth-boundaries-2026-10-12.md",
        "findings/f1-hidden-action-boundary-2026-10-12.md",
        "findings/f1-wireless-qrcode-context-2026-10-12.md",
    ),
    (
        "sched",
        "closed",
        "findings/f1-gap-attack-pass-2026-10-12.md",
    ),
    (
        "blind_ssrf",
        "closed",
        "findings/f1-gap-attack-pass-2026-10-12.md",
        "findings/f1-aggressive-software-pass-2026-10-12.md",
    ),
    (
        "services",
        "closed",
        "findings/management-auth-boundaries-2026-10-12.md",
    ),
    (
        "offline",
        "closed",
        "scripts/inspect_config_export_header.py",
        "findings/f1-gap-attack-pass-2026-10-12.md",
    ),
)

OPEN_ELSEWHERE = (
    "scripts/f1_ipping_host_probe.py",
)


def catalog() -> dict:
    return {
        "retired": True,
        "live_requests": False,
        "closed": [
            {"phase": row[0], "status": row[1], "evidence": list(row[2:])}
            for row in CLOSED
        ],
        "open_elsewhere": list(OPEN_ELSEWHERE),
    }


def main() -> int:
    print(json.dumps(catalog(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
