# F1 WAN outage after switch and mirror changes (2026-10-28)

## Result

After the SG108E port-mirror setup and the Mac capture attempts, the F1 lost its internet connection. On the F1's status page, the WAN link is up but it has no IP address.

**Cause (owner tests, 2026-10-28):** the switch's Port Mirror setting breaks the F1's WAN connection. With the wall cable direct to the F1, the internet works. With the switch in the path and mirroring on, it fails. With the switch in the path and mirroring off, it works. The ISP is not the cause. The mirror's exact trigger is not yet isolated (see the sections below).

*At the time of the first pass, the switch was not yet ruled out; the later sections are the test that ruled it in.*

## Setup (as described by the owner, REPORTED unless noted)

- ISP handoff (wall) → SG108E port 1.
- SG108E port 2 → F1 WAN port.
- SG108E port 3 → Mac USB Ethernet adapter (`en10`, AX88179B).
- F1 LAN gateway: `192.168.1.1` (VERIFIED from the F1 status page). The repo's other notes give `192.168.2.1` for the F1; that difference is not resolved here.
- SG108E management: `192.168.0.1` (VERIFIED, see below).

## Verified facts

- **F1 status page** (`http://192.168.1.1`, text pasted by owner): firmware `23.1.B`. Broadband: "Ethernet Connected". Internet Access: "DHCP Connecting". No WAN IP shown.
- **SG108E port statistics** (page text pasted by owner): ports 1, 2, and 3 are `Enabled`, `1000Full`. Port 1 RxGood 14,227,032, RxBad 0. Port 2 TxGood 2,403,729, RxGood 682,710. Port 3 RxBad 1. Ports 4–8 link down.
- **SG108E mirror configuration** (screenshot, owner): Port Mirror `Enable`, Mirroring Port `Port 3`, Mirrored Port 1 Ingress `Enable` and Egress `Enable`, ports 2–8 `Disable`. Setting saved before the port-mirror test. Earlier the mirrored port was Port 2; changed to Port 1 on 2026-10-28.
- **Mac `en10` state**: IPv4 was turned off with `networksetup -setv4off` (output `IPv4 off for: AX88179B`). A later `ifconfig` showed only the IPv6 link-local address. Later a manual address `192.168.0.50/24` was added with `ifconfig`. Before that, DHCP on this port gave the Mac a `100.77.x.x` address. (Address not recorded here.)
- **Switch reachable from the Mac**: with `en10` at `192.168.0.50/24`, `ping 192.168.0.1` replied (2 ms, 0% loss), `http://192.168.0.1/` returned HTTP 200, and ARP mapped `192.168.0.1` to the switch's MAC.
- **Mac internet**: the Mac's default route was `en0` on an iPhone hotspot (`172.20.10.x`). `https://example.com` returned HTTP 200 over that route. This doesn't test the F1 path.
- **Passive captures on `en10`** (IPv4 off): 37, 23, and 30 frames in roughly 9 seconds. A 15-second capture had 36 frames: switch-origin broadcasts (`Realtek` protocol) from the switch MAC, DHCP messages with source `192.168.0.1` and hostname `TL-SG108E`, one frame from an unidentified source MAC, and mDNS from the Mac. No TCP and no frame from an F1 WAN MAC. No positive-control request was sent during that capture.

## Reported, not verified

- A phone on the F1 Wi-Fi reports "server can't be found" for websites.
- Internet still fails with the Mac unplugged from switch port 3.

## Hypotheses (not tested)

- **H1, ISP side**: the ISP is not giving the F1 a WAN address, for a reason outside this network. Not confirmed; the ISP has not been checked.
- **H2, ISP lease tied to a MAC**: the ISP may have bound the line to the Mac's adapter MAC, which took a lease on port 3 earlier. The F1 cannot get an address while the binding stands. Not tested.
- **H3, switch path**: the switch or its mirror setting is blocking the F1's DHCP traffic. Not tested. Port mirroring normally copies traffic without blocking it, but this unit has not been checked for that.

## Not shown

- Any WAN IP on the F1 after this point.
- Whether the F1 works with the switch removed from the path.
- Whether the ISP line is up.
- DHCP traffic on the WAN side. No capture of it has been taken.
- Whether the mirror copies F1 WAN traffic. The positive-control request has not been run successfully.

## Next test (owner action)

1. Connect the wall cable directly to the F1's WAN port, skipping the switch.
2. Power-cycle the F1 (30 seconds off).
3. Check Internet Access at `http://192.168.1.1` after about 2 minutes.

Outcome decides:
- Internet Access shows an IP: the SG108E path is the cause (H3 or the mirror setting). Next: check port 1 and 2 forwarding and whether the switch was changed by the update prompt.
- Still "DHCP Connecting": the switch is cleared. Next: check the ONT or wall connection, then the ISP lease (H2). Test H2 by plugging the F1 into a port that never had the Mac's MAC.

## Reproduction (read-only commands used)

```bash
ifconfig en10 | grep -E 'inet |status'
route -n get default | grep -E 'gateway|interface'
ping -c 2 192.168.0.1
curl -s -o /dev/null -w 'http=%{http_code}\n' -m 6 http://192.168.0.1/
arp -n 192.168.0.1
sudo tshark -i en10 -a duration:10 -q -z io,stat,0
```

## Result of the direct-connection test (owner report, 2026-10-28)

- **REPORTED:** with the wall cable plugged directly into the F1's WAN port, the internet works. The ISP and F1 are fine.
- **DERIVED:** the switch is interfering with the F1's WAN connection. H1 (ISP side) is not supported, since the ISP works without the switch. H2 is not supported either, since the failure is tied to the switch path.
- **Still open:** which switch setting causes it. The mirror config (H3) is the first suspect, and the VLAN or port settings are second.

## Next test (switch in path)

1. Set Port Mirror to **Disable**, then Apply.
2. Put the switch back in the path: wall → port 1, port 2 → F1 WAN. Port 3 unplugged.
3. Power-cycle the F1, then check Internet Access at `http://192.168.1.1`.

If internet works, the mirror config is the cause. If it doesn't, check the switch's VLAN settings next, to confirm all ports are in the default VLAN.

## Mirror-off result (owner report, 2026-10-28)

- **REPORTED:** with Port Mirror set to Disable, and the switch back in the path (wall → port 1, port 2 → F1 WAN, port 3 unplugged), the internet works.
- **DERIVED:** the mirror configuration breaks the F1's WAN connection through this switch. The VLAN/port settings are not the cause: the port page shows ports 1–3 Auto, 1000MF, flow control Off, with no link errors.
- **Not shown:** which part of the mirror config breaks it. Candidates are the Egress copy on port 1 and the mirror destination (port 3) when no device is attached to it. Port 3 was unplugged during the failing test. Only the full mirror setting was tested, not each part separately.
- **Not checked:** the switch's firmware version. A firmware bug is possible but unverified.

## Status

Internet works with the mirror off. Capture through the switch's mirror is blocked until its cause is known.

## Log export attempts (owner, 2026-10-28)

- **REPORTED:** the Export All button showed "Exporting failed; please try again."
- **REPORTED:** a console `fetch` of the same request (action=export_log with the page CSRF token) returned HTTP 403 with a 146-byte body. No log file was obtained.
- **Not tested:** whether the 403 comes from a missing referer or a per-modal token. One attempt from the logviewer page would test that, but the table copy below needs no request.

## Log viewer rows, 18:40–18:49 (owner paste, 2026-10-28)

- **VERIFIED:** nginx logged `POST without CSRF token` for `/modals/logviewer-modal.lp` at 18:48:55 from `192.168.1.150`. That's the console request. The server didn't accept the token in the form sent.
- **VERIFIED:** `192.168.1.150` is the DHCP client named `Mac` (dnsmasq DHCPACK at 18:45:07). The `GET /gateway.lp?action=scheduleReboot` requests at 18:45:08 and 18:47:42 came from the Mac's browser and were refused as unauthorized. No reboot line appears.
- **VERIFIED:** no CWMP, ACS, firmware-URL, or `.rbi` lines in these rows. The only recurring update-related entry is `obuspa_retriever.sh` run by root's crontab every minute.
- **Not shown:** the cause of the missing CSRF token. Possible reasons include a token expected in a header, or a stale token after login at 18:47:46. Not tested.
- **Limit:** the viewer shows a live window of recent rows, not the full history.

## Update: in-page export succeeded (2026-10-28, later)

The owner approved one paced export from the Mac. The POST used the page-level CSRF token and returned HTTP 200 with a 71,954-byte log. The export shows the WAN bound (`100.77.193.145` from `83.233.57.226`) with the mirror off, and contains no CWMP, ACS, or firmware-URL lines. See [f1-export-log-modal-2026-10-28.md](f1-export-log-modal-2026-10-28.md). The mirror-part isolation test is still open.
