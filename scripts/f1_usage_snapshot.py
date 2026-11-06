#!/usr/bin/env python3
"""Read-only F1 usage snapshot for the router dashboard.

One SSH to root@192.168.1.1. Writes gitignored
artifacts/ui/router-usage-latest.json and the canvas sidecar the
dashboard already has open. Does not change router config.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
JSON_PATH = REPO / "artifacts" / "ui" / "router-usage-latest.json"
CANVAS_DATA = Path(
    "/Users/nils/.cursor/projects/Users-nils-genesis/canvases/router-usage.canvas.data.json"
)
PASSWORD_PATH = REPO / "artifacts" / "secrets" / "f1-root.password"
ASKPASS = "/tmp/f1ask/askpass.sh"
HOST = "root@192.168.1.1"

IDLE_NEEDLES = (
    "airties",
    "cloud-comm",
    "cloud_comm",
    "cwmpd",
    "datausage",
    "mosquitto",
)
ABSENT_CHECKS = (
    ("obuspa", ("obuspa",)),
    ("miniupnp", ("miniupnp",)),
    ("F-Secure", ("f-secure", "fsecure")),
    ("sense", ("__sense__",)),
    ("mosquitto", ("mosquitto",)),
    ("airties", ("airties",)),
    ("cloud-comm", ("cloud-comm", "cloud_comm")),
    ("cwmpd", ("cwmpd",)),
    ("datausage", ("datausage",)),
)

REMOTE = r"""
echo @@LOAD
cat /proc/loadavg
echo @@MEM
cat /proc/meminfo
echo @@NET
cat /proc/net/dev
echo @@DF
df -k
echo @@UP
cat /proc/uptime
echo @@CPU1
grep '^cpu ' /proc/stat
sleep 1
echo @@CPU2
grep '^cpu ' /proc/stat
echo @@PROCS
for d in /proc/[0-9]*; do
  [ -r "$d/status" ] || continue
  pid=${d##*/}
  comm=$(cat "$d/comm" 2>/dev/null) || continue
  comm=$(printf '%s' "$comm" | tr '\n' ' ')
  rss=$(awk '/^VmRSS:/{print $2; exit}' "$d/status" 2>/dev/null)
  [ -n "$rss" ] || rss=0
  cmd=$(tr '\0' ' ' < "$d/cmdline" 2>/dev/null)
  if printf '%s' "$cmd" | grep -q -i airties; then
    comm=airties
  fi
  printf '%s %s %s\n' "$pid" "$rss" "$comm"
done
echo @@TOP
top -b -n 2 -d 1 </dev/null 2>/dev/null || true
"""


def seed_snapshot() -> dict:
    """20:42 local report. Traffic bytes are the rounded totals, not a counter read."""
    gib = 1024**3
    mib = 1024**2
    return {
        "ok": True,
        "error": None,
        "errorAt": None,
        "kind": "seed",
        "readAt": "2026-11-06T20:42:00+01:00",
        "readAtLabel": "6 Nov 2026, 20:42",
        "uptimeSec": 73 * 60,
        "load1": 0.12,
        "load5": 0.18,
        "load15": 0.23,
        "cpuPct": 4.0,
        "memTotalMib": 483.0,
        "memUsedMib": 392.0,
        "memAvailableMib": 92.0,
        "slabMib": 104.0,
        "processRssMib": None,
        "overlayFreeMib": 85.0,
        "traffic": [
            {
                "name": "WAN eth4",
                "inBytes": int(round(1.54 * gib)),
                "outBytes": 258 * mib,
            },
            {
                "name": "LAN br-lan",
                "inBytes": 257 * mib,
                "outBytes": int(round(2.23 * gib)),
            },
        ],
        "topRam": [
            {"name": "Airties", "rssMib": 16.0, "cpuPct": None, "idle": True},
            {"name": "cloud-comm", "rssMib": 6.3, "cpuPct": None, "idle": True},
            {"name": "wlan_mgr", "rssMib": 5.0, "cpuPct": None, "idle": False},
            {"name": "datausaged + notifier", "rssMib": 3.9, "cpuPct": None, "idle": True},
            {"name": "cwmpd", "rssMib": 3.7, "cpuPct": None, "idle": True},
            {"name": "mosquitto ×2", "rssMib": 3.7, "cpuPct": None, "idle": True},
        ],
        "topCpu": [],
        "idle": [
            {"name": "Airties", "rssMib": 16.0, "cpuPct": None, "idle": True},
            {"name": "cloud-comm", "rssMib": 6.3, "cpuPct": None, "idle": True},
            {"name": "cwmpd", "rssMib": 3.7, "cpuPct": None, "idle": True},
            {"name": "datausaged + notifier", "rssMib": 3.9, "cpuPct": None, "idle": True},
            {"name": "mosquitto ×2", "rssMib": 3.7, "cpuPct": None, "idle": True},
        ],
        "notRunning": ["obuspa", "miniupnp", "F-Secure", "sense"],
        "sourceNote": (
            "Reported snapshot, 20:42 local, uptime 1h 13m. "
            "Traffic figures were already rounded; average rate is those totals divided by uptime. "
            "Per-process CPU was not in that snapshot."
        ),
    }


def _section(text: str, name: str) -> str:
    marker = f"@@{name}"
    if marker not in text:
        return ""
    rest = text.split(marker, 1)[1]
    # Next marker at line start.
    lines = []
    for line in rest.splitlines()[1:]:
        if line.startswith("@@"):
            break
        lines.append(line)
    return "\n".join(lines).strip()


def parse_meminfo(text: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, raw = line.split(":", 1)
        bits = raw.split()
        if bits and bits[0].isdigit():
            out[key.strip()] = int(bits[0])
    return out


def parse_netdev(text: str) -> dict[str, tuple[int, int]]:
    out: dict[str, tuple[int, int]] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        name, rest = line.split(":", 1)
        name = name.strip()
        cols = rest.split()
        if len(cols) < 9 or not cols[0].isdigit():
            continue
        out[name] = (int(cols[0]), int(cols[8]))
    return out


def parse_df(text: str) -> list[tuple[str, int]]:
    rows: list[tuple[str, int]] = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 6 or parts[0] == "Filesystem":
            continue
        pct_i = next((i for i, part in enumerate(parts) if part.endswith("%")), None)
        if pct_i is None or pct_i < 1:
            continue
        try:
            avail = int(parts[pct_i - 1])
        except ValueError:
            continue
        mount = " ".join(parts[pct_i + 1 :])
        rows.append((mount, avail))
    return rows


def pick_overlay_kib(rows: list[tuple[str, int]]) -> int | None:
    overlay = [(mount, avail) for mount, avail in rows if "overlay" in mount]
    if not overlay:
        return None
    exact = [avail for mount, avail in overlay if mount == "/overlay"]
    if exact:
        return exact[0]
    return overlay[0][1]


def parse_cpu_line(line: str) -> tuple[int, int] | None:
    parts = line.split()
    if len(parts) < 5 or parts[0] != "cpu":
        return None
    nums = [int(part) for part in parts[1:]]
    idle = nums[3]
    return sum(nums), idle


def cpu_busy_pct(first: tuple[int, int], second: tuple[int, int]) -> float | None:
    total = second[0] - first[0]
    idle = second[1] - first[1]
    if total <= 0:
        return None
    return round(100.0 * (total - idle) / total, 1)


def parse_proc_block(text: str) -> list[tuple[str, int, str]]:
    rows = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 3 or not parts[0].isdigit():
            continue
        try:
            rss = int(parts[1])
        except ValueError:
            continue
        rows.append((parts[0], rss, " ".join(parts[2:])))
    return rows


def parse_top_cpu(text: str) -> dict[str, float]:
    """Pid to CPU percent from the last top screen."""
    lines = text.splitlines()
    header_at = None
    pid_idx = cpu_idx = None
    for index, line in enumerate(lines):
        parts = line.split()
        if "PID" not in parts:
            continue
        cpu_at = next((i for i, part in enumerate(parts) if "CPU" in part.upper()), None)
        if cpu_at is None:
            continue
        header_at = index
        pid_idx = parts.index("PID")
        cpu_idx = cpu_at
    if header_at is None or pid_idx is None or cpu_idx is None:
        return {}
    found: dict[str, float] = {}
    for line in lines[header_at + 1 :]:
        parts = line.split()
        if not parts:
            continue
        if "PID" in parts and any("CPU" in part.upper() for part in parts):
            break
        if len(parts) <= max(pid_idx, cpu_idx) or not parts[pid_idx].isdigit():
            continue
        try:
            found[parts[pid_idx]] = float(parts[cpu_idx].rstrip("%"))
        except ValueError:
            continue
    return found


def _is_kernel_thread(comm: str) -> bool:
    return comm.startswith("[") and comm.endswith("]")


def _idle_match(comm: str) -> bool:
    folded = comm.lower()
    return any(needle in folded for needle in IDLE_NEEDLES)


def _sense_running(comms: list[str]) -> bool:
    for comm in comms:
        folded = comm.lower()
        if folded == "sense" or folded.startswith("sense_") or folded.startswith("sense-"):
            return True
    return False


def _absent(comms: list[str]) -> list[str]:
    folded = [comm.lower() for comm in comms]
    missing = []
    for label, needles in ABSENT_CHECKS:
        if label == "sense":
            if not _sense_running(comms):
                missing.append(label)
            continue
        if not any(any(needle in comm for needle in needles) for comm in folded):
            missing.append(label)
    return missing


def _mib(kib: float) -> float:
    return round(kib / 1024.0, 1)


def parse_snapshot(text: str, read_at: datetime) -> dict:
    load_line = _section(text, "LOAD").splitlines()
    if not load_line or len(load_line[0].split()) < 3:
        raise ValueError("loadavg missing")
    load_bits = load_line[0].split()
    mem = parse_meminfo(_section(text, "MEM"))
    if "MemTotal" not in mem:
        raise ValueError("meminfo missing")
    total = mem["MemTotal"]
    available = mem.get("MemAvailable", mem.get("MemFree", 0))
    slab = mem.get("Slab", 0)
    net = parse_netdev(_section(text, "NET"))
    overlay_kib = pick_overlay_kib(parse_df(_section(text, "DF")))
    up_line = _section(text, "UP").splitlines()
    if not up_line:
        raise ValueError("uptime missing")
    uptime = float(up_line[0].split()[0])
    cpu1 = parse_cpu_line(next((line for line in _section(text, "CPU1").splitlines() if line.startswith("cpu ")), ""))
    cpu2_text = _section(text, "CPU2")
    cpu2 = parse_cpu_line(next((line for line in cpu2_text.splitlines() if line.startswith("cpu ")), ""))
    if cpu1 is None or cpu2 is None:
        raise ValueError("cpu sample missing")
    cpu_pct = cpu_busy_pct(cpu1, cpu2)
    proc_rows = parse_proc_block(_section(text, "PROCS"))
    if not proc_rows:
        raise ValueError("process sample missing")
    top_cpu_by_pid = parse_top_cpu(_section(text, "TOP"))

    processes = []
    rss_sum = 0
    for pid, rss, comm in proc_rows:
        if _is_kernel_thread(comm):
            continue
        rss_sum += max(rss, 0)
        cpu = top_cpu_by_pid.get(pid)
        processes.append(
            {
                "name": comm,
                "pid": pid,
                "rssMib": _mib(rss),
                "cpuPct": cpu,
                "idle": _idle_match(comm) and (cpu is None or cpu < 1.0),
            }
        )
    counts: dict[str, int] = {}
    for row in processes:
        counts[row["name"]] = counts.get(row["name"], 0) + 1
    for row in processes:
        if counts[row["name"]] > 1:
            row["name"] = f"{row['name']} {row['pid']}"
        del row["pid"]

    top_ram = sorted(processes, key=lambda row: row["rssMib"], reverse=True)[:8]
    ranked_cpu = [row for row in processes if row["cpuPct"] is not None and row["cpuPct"] > 0]
    top_cpu = sorted(ranked_cpu, key=lambda row: (row["cpuPct"], row["rssMib"]), reverse=True)[:8]
    idle = [row for row in processes if row["idle"]]
    idle.sort(key=lambda row: row["rssMib"], reverse=True)
    comms = [row[2] for row in proc_rows]

    traffic = []
    for iface, label in (("eth4", "WAN eth4"), ("br-lan", "LAN br-lan")):
        if iface not in net:
            continue
        rx, tx = net[iface]
        traffic.append({"name": label, "inBytes": rx, "outBytes": tx})

    used_kib = max(total - available, 0)
    return {
        "ok": True,
        "error": None,
        "errorAt": None,
        "kind": "ssh",
        "readAt": read_at.isoformat(timespec="seconds"),
        "readAtLabel": read_at.strftime("%-d %b %Y, %H:%M"),
        "uptimeSec": int(uptime),
        "load1": float(load_bits[0]),
        "load5": float(load_bits[1]),
        "load15": float(load_bits[2]),
        "cpuPct": cpu_pct,
        "memTotalMib": _mib(total),
        "memUsedMib": _mib(used_kib),
        "memAvailableMib": _mib(available),
        "slabMib": _mib(slab),
        "processRssMib": _mib(rss_sum),
        "overlayFreeMib": _mib(overlay_kib) if overlay_kib is not None else None,
        "traffic": traffic,
        "topRam": top_ram,
        "topCpu": top_cpu,
        "idle": idle,
        "notRunning": _absent(comms),
        "sourceNote": (
            "Read-only SSH to root@192.168.1.1. "
            "CPU is a one-second /proc/stat delta. Process CPU is top's second sample. "
            "Average rate is the interface byte counter divided by uptime. "
            "Process memory is the sum of VmRSS. Kernel slab is MemInfo Slab."
        ),
    }


def fail_snapshot(previous: dict, error: str, when: datetime) -> dict:
    out = dict(previous)
    out["ok"] = False
    out["error"] = error[:300]
    out["errorAt"] = when.isoformat(timespec="seconds")
    return out


def load_previous() -> dict | None:
    if not JSON_PATH.is_file():
        return None
    try:
        data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if isinstance(data, dict) and "readAt" in data:
        return data
    return None


def write_outputs(snapshot: dict) -> None:
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    _atomic_json(JSON_PATH, snapshot)
    existing: dict = {}
    if CANVAS_DATA.is_file():
        try:
            loaded = json.loads(CANVAS_DATA.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                existing = loaded
        except (OSError, json.JSONDecodeError):
            existing = {}
    existing["usage"] = snapshot
    _atomic_json(CANVAS_DATA, existing)


def _atomic_json(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _password() -> str:
    if not PASSWORD_PATH.is_file():
        raise RuntimeError("password file is missing")
    password = PASSWORD_PATH.read_text(encoding="utf-8").rstrip("\r\n")
    if not password:
        raise RuntimeError("password file is empty")
    return password


def _redact(text: str, password: str) -> str:
    if password and password in text:
        text = text.replace(password, "[redacted]")
    return text


def ssh_read(password: str) -> str:
    if not os.path.isfile(ASKPASS):
        raise RuntimeError("askpass helper is missing")
    last_error = "SSH failed"
    for batch in (True, False):
        env = os.environ.copy()
        env["F1PW"] = password
        env["SSH_ASKPASS"] = ASKPASS
        env["SSH_ASKPASS_REQUIRE"] = "force"
        env["DISPLAY"] = "none"
        cmd = [
            "ssh",
            "-o",
            "PreferredAuthentications=password",
            "-o",
            "PubkeyAuthentication=no",
            "-o",
            "IdentitiesOnly=yes",
            "-o",
            "NumberOfPasswordPrompts=1",
            "-o",
            "ConnectTimeout=8",
            "-o",
            "StrictHostKeyChecking=accept-new",
            "-o",
            "LogLevel=ERROR",
        ]
        if batch:
            cmd.extend(["-o", "BatchMode=yes"])
        cmd.extend([HOST, REMOTE])
        try:
            result = subprocess.run(
                cmd,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                env=env,
                timeout=35,
                start_new_session=True,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("SSH timed out") from exc
        stderr = _redact(result.stderr.decode("utf-8", "replace").strip(), password)
        stdout = result.stdout.decode("utf-8", "replace")
        if result.returncode == 0 and "@@MEM" in stdout:
            return stdout
        last_error = stderr.splitlines()[0] if stderr else f"SSH exited {result.returncode}"
        last_error = _redact(last_error, password)
        # BatchMode often refuses askpass. Retry once without it. Do not retry a timeout.
        if not batch:
            break
        if "timed out" in last_error.lower() or "timeout" in last_error.lower():
            break
    raise RuntimeError(last_error)


def main() -> int:
    when = datetime.now().astimezone()
    previous = load_previous() or seed_snapshot()
    try:
        password = _password()
        text = ssh_read(password)
        snapshot = parse_snapshot(text, when)
    except Exception as exc:
        message = str(exc) or exc.__class__.__name__
        snapshot = fail_snapshot(previous, message, when)
    write_outputs(snapshot)
    if snapshot.get("ok"):
        print(f"ok {snapshot['readAtLabel']} cpu={snapshot['cpuPct']}% ram={snapshot['memUsedMib']}/{snapshot['memTotalMib']} MiB")
        return 0
    print(f"ssh-failed {snapshot.get('error')}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
