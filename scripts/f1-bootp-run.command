#!/bin/bash
# Mac-side driver for one BOOT-P/TFTP run. Order matters:
#   1. start UART capture detached in a screen session (boot log is recorded before any reboot)
#   2. you start scripts/f1-bootp-tftp-combined-test.ps1 on the Windows PC and wait for "Listening"
#   3. optionally reboot the router through the admin UI (scripts/f1_system_reboot.py)
#   4. you attach to the screen session and press b at "Press b to enter BOOT-P"
#
# The reboot is OFF unless you pass --reboot-live AND --password-file. Without --reboot-live
# this script never logs in to the router. The password file is yours; create it outside the repo.
#
# Usage (from repo root):
#   bash scripts/f1-bootp-run.command                       # capture only; power-cycle by hand
#   bash scripts/f1-bootp-run.command --reboot-live --password-file ~/.f1-admin-password
#   bash scripts/f1-bootp-run.command --help
set -eu
umask 077

reboot_live=0
password_file=""
device="/dev/cu.usbserial-0001"
while [ $# -gt 0 ]; do
  case "$1" in
    --reboot-live) reboot_live=1 ;;
    --password-file) password_file="${2:?--password-file needs a path}"; shift ;;
    --device) device="${2:?--device needs a path}"; shift ;;
    --help|-h) sed -n '2,13p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done

if [ "$reboot_live" -eq 1 ] && [ -z "$password_file" ]; then
  echo "--reboot-live needs --password-file" >&2
  exit 2
fi
if [ ! -c "$device" ]; then
  echo "Serial device not found: $device" >&2
  echo "Connect the USB adapter; list ports with: ls /dev/cu.*" >&2
  exit 1
fi

here="$(cd "$(dirname "$0")" && pwd)"
stamp="$(date +%Y%m%d-%H%M%S)"
logfile="$HOME/Desktop/router-boot-$stamp-$$.log"
screenrc="$HOME/.f1boot-$stamp-$$.screenrc"
session="f1boot-$stamp-$$"
printf 'startup_message off\ndeflog on\nlogfile %s\nlogfile flush 1\n' "$logfile" > "$screenrc"

# Step 1: UART capture, detached so the reboot step can run in this shell.
/usr/bin/screen -c "$screenrc" -L -dmS "$session" "$device" 115200
rm -f "$screenrc"
echo "UART capture running in screen session: $session"
echo "  log: $logfile"
echo "  watch/press keys: screen -r $session   (detach: Ctrl+A, D)"
echo "  stop capture:     screen -S $session -X quit"
echo

# Step 2: wait for the Windows side.
read -r -p "Start the Windows script now. Press Enter here once it prints 'Listening BOOTP/udp67'... " _
echo

# Step 3: optional reboot.
if [ "$reboot_live" -eq 1 ]; then
  echo "Rebooting router via admin UI (scripts/f1_system_reboot.py)..."
  if ! python3 "$here/f1_system_reboot.py" --password-file "$password_file"; then
    echo "Reboot failed; power-cycle the router by hand, then press b in the screen session." >&2
    exit 1
  fi
  echo "Reboot requested. Watch for 'Press b to enter BOOT-P' in the screen session."
else
  echo "Reboot skipped (no --reboot-live). Power-cycle the router by hand now."
fi
echo
echo "When the router prints 'Press b to enter BOOT-P', attach and press b:"
echo "  screen -r $session"
