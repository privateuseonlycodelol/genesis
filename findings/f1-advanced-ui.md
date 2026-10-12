# F1 Advanced UI

**When:** 2026-10-11 ~21:20 (UTC+2)  
**Gateway:** `http://192.168.2.1`  
**This Mac:** Wi-Fi `en0` on `192.168.2.0/24` (host address redacted in public notes)  
**Config changed:** none  
**Requests:** 5 (login page, two SRP posts, two page GETs). No HTTP 503.

An earlier try from `172.20.10.2/28` never reached the gateway. This pass did.

## Login

`GET /login.lp` → **200**, login form.  
SRP identify and proof → **200**. Login **succeeded**.

## `/gateway.lp`

**HTTP 200**, 17267 bytes. Title **Telia F1**. Not the login screen.

This is the Advanced **dashboard**. The header is the signed-in user menu (Change my password, Sign out). The body is status cards, each opening a modal. It is a menu of settings, not a command shell.

Cards and what they show:

| Card | On the page |
|------|-------------|
| System Info | Version **23.1.b** |
| Broadband | Ethernet connected |
| Internet Access | DHCP on, a WAN address, IPv6 connected |
| Wireless | A 2.4 GHz name and a 5 GHz name |
| Local Network | DHCP enabled, gateway `192.168.2.1`, netmask `255.255.255.0`, IPv6 assigned |
| Devices | 1 Ethernet device, 2 Wi-Fi devices |
| WAN Services | DynDNS off, 0 port-forward rules, 0 UPnP rules |
| Firewall | A level, 1 IPv4 rule, 1 IPv6 rule |
| Diagnostics | Card only |
| Sharing | Samba off, DLNA off |
| Parental Controls | Site blocking off, access control on, 0 time-of-day rules |
| VPN Server | Off, 0 clients |
| Bridge ETH port 4 | Off |

Footer: © Vantiva 2026.

The cards link to other modals (`system-info`, `broadband`, `internet`, `ethernet`, `device`, `firewall`, `parental`, `tod`, `l2tp-ipsec`, `dmz`). Those were not opened. Logviewer was not requested. Diagnostics, WAN Services, and Sharing were opened in a later login, below.

Saved: `artifacts/ui/gateway.lp.authenticated.html`.

## `/modals/wireless-ap-modal-newEM.lp`

**HTTP 200**, 13602 bytes. Not the login screen. No page title; it is a modal fragment.

This is the **Wireless access-point form**. Tabs: Wireless, Radio, AP, WPS. Network choice: Home and Guest. For 2.4 GHz and 5 GHz it has AP state, SSID, broadcast, security (WPA2 PSK, or WPA2 PSK with WPA3 SAE), a password field, access-control list (off / blacklist / whitelist), and a QR-code button. Buttons: hide advanced, show advanced, Close, Cancel, Save.

It is a settings form, not a command shell.

Saved: `artifacts/ui/wireless-ap-modal-newEM.lp.html` (password field values removed).

## Diagnostics, WAN Services, Sharing

A second login (login page plus two SRP posts, all **200**) then three GETs, 2 seconds apart. No HTTP 503. Nothing else was requested. These are settings and status forms, not a command shell.

### `/modals/diagnostics-connection-modal.lp`

**HTTP 200**, 4210 bytes. Not the login screen.

**Diagnostics connection check.** Tabs along the top: Connection, Ping & Traceroute, Network, Igmpproxy. The Connection tab shows WAN operational state **Up**, WAN config available, an IPv4 address, an IPv6 address, and ping lines for the next hop and two DNS servers (some still running or unanswered). Buttons: Restart all tests, Close, Cancel, Save.

Saved: `artifacts/ui/diagnostics-connection-modal.lp.html`.

### `/modals/wanservices-modal.lp`

**HTTP 200**, 13146 bytes. Not the login screen.

**WAN services / port mapping form.** Tabs: Port Mapping (open) and DNS & DynDNS (opened later, below). The open tab is an IPv4 port-forwarding table (name, protocol, WAN port, LAN port, source, destination) with a preset list (FTP, HTTP, SSH, and similar), an IPv6 forwarding table, and UPnP / NAT-PMP / secure-mode switches. Buttons: refresh, hide advanced, show advanced, Close, Cancel, Save.

Saved: `artifacts/ui/wanservices-modal.lp.html`.

### `/modals/contentsharing-modal.lp`

**HTTP 200**, 8873 bytes. Not the login screen.

**Content sharing form** for Samba and DLNA. Samba name is Vantiva. Storage interface choices are LAN or LAN/WAN. Disk protection has an ID and a password field (the value was removed from the saved copy). DLNA name is Telia F1, profiler idle. USB 3.1 is a toggle, with a note that turning it on reboots the gateway. Hard-disk section says no devices are connected. The page also shows the notice “Changes saved successfully”; this pass only fetched the page and did not press Save.

Saved: `artifacts/ui/contentsharing-modal.lp.html`.

## DNS & DynDNS

The session cookie was gone, so this was a new login (login page and two SRP posts, all **200**) and then one GET. No HTTP 503. Nothing else was requested.

### `/modals/dyndns-wanservices-modal.lp`

**HTTP 200**, 10711 bytes. Not the login screen.

**DynDNS settings form.** Status is disabled. Fields are service name (a long provider list, including dyndns.org and no-ip.com), an HTTPS option, domain, user name, and password. Password values were removed from the saved copy. There is also a DynDNS IPv6 control. Buttons: Close, Cancel, Save. It is a settings form, not a command shell.

Saved: `artifacts/ui/dyndns-wanservices-modal.lp.html`.
