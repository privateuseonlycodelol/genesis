#!/bin/bash
# Capture a router UART with macOS Screen. Run this from Terminal.app, which
# provides Screen the real PTY it needs (the embedded Genesis terminal may not).
set -eu
umask 077

device="${1:-/dev/cu.usbserial-0001}"
if [ "${1:-}" = "--help" ]; then
  echo "Usage: bash scripts/f1-boot-capture.command [serial-device]  (from repo root)"
  echo "Default: /dev/cu.usbserial-0001 at 115200 baud; log is saved on Desktop."
  exit 0
fi
if [ ! -c "$device" ]; then
  echo "Serial device not found: $device" >&2
  echo "Connect the USB adapter; list ports with: ls /dev/cu.*" >&2
  exit 1
fi

stamp="$(date +%Y%m%d-%H%M%S)"
logfile="$HOME/Desktop/router-boot-$stamp-$$.log"
screenrc="$HOME/.f1boot-$stamp-$$.screenrc"
printf 'startup_message off\ndeflog on\nlogfile %s\nlogfile flush 1\n' "$logfile" > "$screenrc"
trap 'rm -f "$screenrc"' EXIT HUP INT TERM

echo "Saving UART output to: $logfile"
echo "Start or power-cycle the router after Screen opens."
echo "Exit: Ctrl+A, then K, then Y. Do not detach with Ctrl+A, D."
echo "Wiring: router TX to adapter RX; adapter TX to router RX; GND to GND; leave 3.3V disconnected."
/usr/bin/screen -c "$screenrc" -L -S "f1boot-$stamp-$$" "$device" 115200
