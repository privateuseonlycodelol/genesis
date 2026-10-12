#!/bin/bash
# Capture UART output with macOS cu, recording the terminal session with script.
set -eu
umask 077
if [ "${1:-}" = "--help" ]; then
  echo "Usage: bash f1-boot-capture.command [serial-device]"
  echo "Default: /dev/cu.usbserial-0001 at 115200 baud; logs go to Desktop."
  exit 0
fi
device="${1:-/dev/cu.usbserial-0001}"
if [ ! -c "$device" ]; then
  echo "Serial device not found: $device" >&2
  echo "Connect the USB adapter; list ports with: ls /dev/cu.*" >&2
  exit 1
fi
if [ ! -x /usr/bin/cu ] || [ ! -x /usr/bin/script ]; then
  echo "This capture helper needs macOS /usr/bin/cu and /usr/bin/script." >&2
  exit 1
fi
mkdir -p "$HOME/Desktop"
stamp="$(date +%Y%m%d-%H%M%S)"
logfile="$HOME/Desktop/router-boot-$stamp-$$.log"
echo "Saving UART output to: $logfile"
echo "macOS will ask for your administrator password to open the serial port."
echo "Start the router after the serial connection opens. Blank output before boot is normal."
echo "Exit cu by typing !. at the start of a blank line."
echo "Wiring: router TX to adapter RX; GND to GND; leave 3.3V disconnected."
exec /usr/bin/script -q "$logfile" /usr/bin/sudo /usr/bin/cu -E '!' -l "$device" -s 115200
