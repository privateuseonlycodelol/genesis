# miniupnpd and cwmpd — 2026-11-06

Offline Hopper pass. No device contact. No packets sent.

## miniupnpd-igdv2

Binary `usr/sbin/miniupnpd-igdv2`, SHA-256 `5f3df37295e424a6f6c0b34da69e9475f0ddc089fb87fcf019ab9b42fcb8b5f9`, ARM ELF. Evidence `ev_cf5b22dee6cf28f25d5f5bed9ccacd0240eb4de43f4e7202a9cfa86606b6ee84`.

`ExecuteSoapAction` takes the action name between `#` and a quote, compares its length and bytes to a fixed table, and calls that row's function. An unknown name returns SOAP fault 401, "Invalid Action". The SOAP body is not passed to a shell.

The only `popen` call is `waninfoFromScript` at `0x20584` (call site `0x205d4`, evidence `ev_a8e2a823195cf5a8cb2bee375ac81606022b2b137c9d972576367a2a349c8f0e`). It runs the path it was given, reads at most 100 characters, and scans four fields. That path is the config value `upnp_wgclp_script`, shipped as `/usr/bin/upnp_wgclp`. The script reads `network.wan.ifname` from UCI and pastes it into a shell command. The UPnP request does not supply that string.

Shipped `etc/config/upnpd` has `enable_upnp` 0, `enable_natpmp` 0, and `secure_mode` 1. The `AddPortMapping` reader at `0x1b020` only calls `GetValueFromNameValueList` and has no resolved caller. The install path is `upnp_redirect` at `0x1f654`, evidence `ev_4c55a3442e8e2c5a203c39d0083ba3bdb4a0b29beeed4bd502967ac52573c0e5`. It runs `inet_aton` on the internal address and returns failure if that parse fails. It then calls `check_upnp_rule_against_permissions`. A zero result logs `redirection permission check failed` and returns `-3`. A passing result updates iptables. The shipped permission list allows external and internal ports 1024–65535 toward `0.0.0.0/0`, then denies the rest. The caller-address compare is in `sub_1b050` at `0x1b050`, evidence `ev_eefcde1b40aca773b324373ae28f1945227d070f5456494b7b134dcec661a9a7`. When `runtime_flags` bit `0x10` is set, a failed compare logs `Client %s tried to redirect port to %s`. The two code sites are `0x1b214` and `0x1bc3c`. After the log, both call `0x19084` to free the argument list and then branch to `0x1a664`. That function logs `Returning UPnPError` and sends SOAP fault 500. Neither branch reaches `upnp_redirect` at `0x1f654`. The earlier decompiler picture that showed the install call in the same block was a dropped return. No packet was sent. The daemon is off in the shipped config. `etc/config/upnpd` sets `datamodel_version` to `igdv1`, so the init script would start `miniupnpd-igdv1`, not the v2 binary, if UPnP were enabled. `miniupnpd-igdv1` SHA-256 `a9e65028f706d20bebb60879a3f743520867b97e7edf339401085fa0834bfbdc` is the binary the shipped config selects. Its mismatch sites are the same shape. Bit `0x10` gates a compare at `0x1b1e4` and `0x1bc0c`. A failed compare logs, calls `0x19084` to free the arguments, and branches to `0x1a664`, which sends SOAP fault 500. It does not continue into the install. The other two references, `0x1b3b0` and `0x1be98`, are in a pointer table. `ProcessIncomingNATPMPPacket` at `0x1c544` calls `upnp_redirect_internal`. It does not use the SOAP address compare. Before the mapping log it copies a string into a 32-byte stack buffer. The shipped config has `enable_natpmp` 0, so this handler is not started. The binary has no PCP string.

`ProcessSSDPData` at `0x16aa8` logs an M-SEARCH with a length-limited search target (`%.*s`). Its internal calls are `sockaddr_to_string` and `get_lan_for_peer`. It does not call `popen`. No packet was sent.

The web upload parser requires the CSRF token as the first form field and checks it against the session. It does not run a shell. The catch-all location already requires that session.

`pinholehelper.lua` and `redirecthelper.lua` only execute the fixed command `/etc/init.d/firewall reload`. `interceptd` is Lua and has no `os.execute`.

## cwmpd

Binary `usr/bin/cwmpd`, SHA-256 `ae1b8491efd19d5ea29de661debe2788493eb4b56653829409612223840950a2`. No procedure named `system` or `popen`. It has the download URL format `http://%s%s%s:%u/%s` and the usual TR-069 SOAP envelopes. A download still requires the ACS session. `cwmpd` on this unit is stopped.

The binary's own usage text says `-S` is "secure" mode: a client can add a mapping only to its own address. That string is evidence `ev_0857ff32b69e6e127907abf136c2454272994ccb99b3fffc0d3c5accced176ad`. **Superseded (2026-11-07):** `secure_mode` is a compiled-in entry of the config keyword table at `.rodata` `0x24464`, alongside `enable_natpmp`, `enable_upnp`, `lease_file`, and `minissdpdsocket`; the caller-address compare is the `sub_1b050` site recorded above; and the shipped config sets `secure_mode` to 1, so an enabled UPnP daemon starts with the guard on.

## wlan_mgr

Binary `bin/wlan_mgr`, SHA-256 `f2b5013149da77c0b8da28f15800c5a3b1f5a3341148996306a6b04b6d8a64fb`. No `popen`, `system`, or `execve` symbol. `/bin/sh` at `0x5b002` is referenced only from `sub_1b558`, which waits on a child and logs `wl_mgmt_system_call_timeout`. The only branch to that helper is `0x56788`, inside `sub_5675c`. No branch in the executable targets `sub_5675c`, and its address is not stored. The helper is unused.

## dnsmasq

Binary `usr/sbin/dnsmasq`, SHA-256 `6f9201deccefdb5bf6bc6743ee6c589e51dbaa8a0c3f3ce94aaab086a19157fb`. The only `popen` call is at `0x40cc`, inside the startup function that begins at `0x3c44`. It allocates a buffer, copies a pointer from its own config, appends the literal ` init`, and opens that command for reading. The init script sets that config to `/usr/lib/dnsmasq/dhcp-script.sh`. The hostname from a DHCP packet is not the command.

The init script passes `--dhcp-script=/usr/lib/dnsmasq/dhcp-script.sh`. That script stores the action, MAC, address, and hostname with `json_add_string` and runs `ubus call hotplug.dhcp call "$(json_dump)"`. The command substitution is the script's own call to `jshn`. Its output is one quoted argument. The shell does not scan that output for a further substitution.

`lib/dnsmasq/dhcp-event.sh` passes `$mac`, `$name`, `$ipaddress`, `$DNSMASQ_INTERFACE`, `$DNSMASQ_OLD_HOSTNAME`, and `$DNSMASQ_RELAY_ADDRESS` to `json_add_string` without quotes. That allows word splitting. It does not `eval` the hostname. No hotplug script under `etc/hotplug.d` evals this data.

## dropbear

Binary `usr/sbin/dropbear`, SHA-256 `7d56c96797f962b9c0ac008adfb5f128bfe9171a9d9b0759ac5f3d4860fc4a64`. The version string is `2020.81`. No `popen`, `system`, or `execve` symbol. It uses `getusershell`. The rejection string is `User '%s' has invalid shell, rejected`. A password login still has to pass that allow-list. That is the check this unit hit before `/bin/sh` was added to `/etc/shells`.

## odhcpd

Binary `usr/sbin/odhcpd`, SHA-256 `9279d68289e028d47742c9bfaedee832bf57678b0e00ad0d0137462df7b25f87`. No `popen` or `system`. `execv` is in `sub_bb40` at `0xbb40`. It writes the lease file, then `vfork` and `execv` the configured `leasetrigger` path. Shipped `etc/config/dhcp` sets that path to `/usr/sbin/odhcpd-update`, which only signals dnsmasq. The hostname is formatted into the lease file. It is not the program `execv` runs.

## nginx

Binary `usr/sbin/nginx`, SHA-256 `86104065ce8c94e44a29c20d469c7f584de25d10eea41bc02db26b7d39e1f5a6`. The only `execve` is `sub_3572c` at `0x3572c`. It executes the path stored in a structure and then exits. Hopper found no direct caller, which fits the worker-spawn helper rather than a request handler. The shipped config has no `exec` directive. Request bodies are handled by `content_by_lua`, which was read separately. Those pages do fixed actions or require a session.

## cupsd

Binary `usr/sbin/cupsd`, SHA-256 `f4a6c76a1c4459d41469dc0984c8f22cae8011f5c1b5b0b982ddaef14071039f`. No `popen`, `system`, `execve`, or `/bin/sh`. It imports `posix_spawn`. The one call is in `sub_4190c` at `0x4190c`. Earlier live IPP reads reached the daemon and did not create a queue, so this spawn was not exercised. HTTP pages on port 631 returned 403.

## airlauncher-daemon

Binary `airties-edge/usr/sbin/airlauncher-daemon`, SHA-256 `9cf6881c9b8a4e8d0b9f512cccb9586a8ebc594f8a74e8d0000d11ea8c04f47d`. No `popen` or `system`. The only `execvp` is `sub_12808`, and the log names it `launcher_exec` in `exec.c`. It forks and runs `execvp` on the argv it was given. That is a direct exec, not a shell, so metacharacters in the path are not interpreted. The argv comes from the launcher's own application list, which is the CDF file, not a packet.

## cloud-comm

Binary `airties-edge/usr/sbin/cloud-comm`, SHA-256 `22fba91f37fa1902afda30169e29357d12effb53cb06fcff3df30c07e4cda277`. No `popen`, `system`, `execve`, or `/bin/sh`. It links mosquitto and connects out to a broker. `sub_4d124` matches the topic prefix, then `sub_504d4` handles the command. That handler's direct callees are `strcmp`, `malloc`, `memcpy`, `free`, and internal functions. Return code 3 logs `command %s received on %s topic %s is not allowed`. A command that is not on the list is refused. There is no shell behind the word "executing". On this unit the daemon is disabled, and a LAN host is not the broker.

## obuspa-tch and three smaller daemons

`obuspa-tch` SHA-256 `ecb53679e8b318f14e5f652736629e0b7fc0889e6589403ea712849ac771d4c8`. `execute_script` at `0x67750` forks and `execvp`s `/bin/ash` with an argument vector. Both callers pass the fixed program `/usr/bin/switchover_usp` and the fixed mode `immediate` or `whenidle`. A USP message does not choose the program. Earlier work found the USP transports closed on the LAN.

`dnsfilterd` SHA-256 `63717d2870aa4f1d108226934a9589280d115dadaee53748fb3e4cb7a8cbf98d`, `igmpproxy` SHA-256 `7942d541e05d11033b9540add8fca35cd044a6d43ceaba726ee088612ab0d973`, and `dhcpopassthrud` SHA-256 `c306030d960bf08c5c1976e7e289e4dfa68abb3744f55cb5ca374298125a2e32` have no `popen`, `system`, `execve`, `execvp`, or `/bin/sh` string.

## mesh_broker, mcsnooper, lcmd

`mesh_broker` SHA-256 `12e6ad90a441355a3bd53f30167c61a135870942627e7600ca4923968340ecc4` imports `popen`. Both callers use fixed commands: `mb_load_network_cujo_lan_config` runs `cat /sys/class/net/br-guest/operstate` and `cat /sys/class/net/br-lan/operstate`. `mb_load_network_cujo_wan_config` runs `uci get network.wan.ifname`. No argument comes from a packet. `mcsnooper` SHA-256 `2d553ef28f967416e883f4f6a63689b9bca6636ca4857238cdaa9ab842e0956c` has no shell string. `lcmd` is Lua, SHA-256 `51809886f99efaccf776ff12f79685154f99b7d29ad1392652816c4d2d0e80a9`, and has no `os.execute` or `io.popen`.

## Remaining init helpers

`nqnd` SHA-256 `a02097e5334d288e530d2d917470ffdff389e351da7af32fb2d59c12ab4ad2fb`, `nqcs` SHA-256 `ed473e636a0ad1c51963aae908b53c1fc69a8d327880c7d9e183afd32c2976af`, `mldproxy` SHA-256 `bd9e3ffd1f25f62ffa614fdd20a2d0d76d849733dd7353e1014336035a56631d`, and `neighmd` SHA-256 `2acbb3a880c035985bc4e87afc9bff22c91546d84d0c1a1d64b6c054e55a6188` have no `popen`, `system`, `execve`, `execvp`, or `/bin/sh` string.

`gre-hotspotd.lua` SHA-256 `a58f0a84c90761c9f233bd4e9849656947f9df67aa533353169d1e178633ccef` builds `tc` and `ping` commands from an interface name, a rate, and an address, and it pastes a bridge name into `brctl showmacs`. Those values come from its own interface and neighbor tables. `hostmanager.lua` runs `nslookup` on an address it already holds for a device that did not use DHCP. Neither file takes that string from an anonymous request. `vpn.lua`, `wansensing.lua`, and `tod.lua` have no `os.execute` or `io.popen`.

## Later init programs

`apiosd`, `cgevent`, `cgrulesengd`, `dlnad`, `ethmngr`, `fseventd`, `interceptd`, strongSwan `starter` and `charon`, `datausage_notifier`, `datausaged`, `wol`, `wrtsysmgmt`, `xl2tpd`, `logd`, `rpcd`, `cwmpevents`, `transformer`, `lxc_monitor.lua`, and `ngwfdd` have no `popen`, `system`, `exec`, or `/bin/sh` string. `ocsd` has no `popen`, `system`, or `/bin/sh` string; its `execv` use is in the section below. `mdm_cache_mgr` only runs `sleep 1`. `pinholehelper.lua` and `redirecthelper.lua` run the fixed command `/etc/init.d/firewall reload`.

`mud` SHA-256 `f43fd206a6cf75623f614b9ffb5fe5175672b12a795223c75d73a07bf8ed5371` calls `system` from the USB insert, monitor, and remove paths. The commands are `/lib/functions/dlnad.sh` with `insert_partition_section`, `remove_partition_section`, or `reset_config_section`. The partition name is the last component of the local mount path. The same binary forks a configured profiler for a local file scan. Neither path takes the program name from a LAN message. `watchdog-tch` SHA-256 `64b47f5014732b7607a5d62f95113a9c49af48db0f45aab0ecb3d772b0b8e4ce` calls `popen` only while shutting down, and the program is `/usr/lib/sendmail`. `netifd` runs its configured hotplug script and protocol handlers. `xinetd` execs the server named in the config it generates; the copied tree has no `etc/config/xinetd` service list. `wldataeld` is named by the `wlan_mgr` init script and is not in the copied root.

## Airties listeners

`airnetreq` SHA-256 `de2e6e0d7742385dc0ec79ac47bc5e192197865e3ce3c7543e1fcf795e85ad7a` listens on a Unix socket, not a TCP port. `ua_sockaddr_netreq` in `libuniversal-agent.so` uses `ENV_SHARED_UNSOCK_PATH_CONTAINER/airnetreq.sock` when that directory is set. The shipped `uagent.run` exports the variable without assigning it, and `etc/edge_platform_params` does not set it, so the fallback is an abstract socket whose name is `airnetreq.sock`. Its commands run `ipset add`, `ipset del`, `ipset list -o save`, and `ipset flush`, with the set name and entry filled in from the local client. A host on the LAN cannot connect to that socket. No web handler in the copied tree connects to it.

`airconnt` and `airpcapt` use the same socket helper, with names `airconnt.sock` and `airpcapt.sock`. Each contains one `system` call, inside the shared `ua_system` wrapper. No branch in either executable targets that wrapper, and its address is not stored as a pointer. The wrapper is unused.

## Config and web scripts that build a command

`exec_config.lua` runs `/etc/init.d/<name> <action>` after a CWMP config transfer. The action must be start, stop, restart, reload, enable, or disable. The service name is the text after `/etc/init.d/` and is not limited to letters. That file is the ACS transfer handler. `ippinghelper.lua` pastes the stored IPPing host into `nslookup` when the data model is read. `VendorLog.lua` pastes a log name from the management data model into `logread`, `cat`, or `ln`. None of these is an anonymous page. `cwmpd` on this unit is stopped.

`assistance-helper.lua` is a root cron script and talks to `127.0.0.1`. `execute_command.lua` runs its own command-line argument; the ethoam init script calls it with arguments the init script assembled. `mod_syslog.lua` runs fixed `logread`. `mod_video.lua` passes an interface name from its own upstream list to `ifstatus`. `mod_conntrack.lua` reads fixed iptables and ebtables tables. `nwcommon.lua` runs fixed `ip route` commands. `banktable.lua`, `ImportConfig.lua`, and `VendorConfig.lua` only run `echo` or `sleep`. `dmz_dhcp_option124.lua` defines a command helper and does not call it; the file builds an option the router sends. `obuspa_helper.lua` writes its own crontab line. `checkOngoingServices.lua` puts numeric ports into a `conntrack` filter. `datausage_intercept.lua` reloads two fixed init scripts. `processvendorinfo.lua` reloads `cwmpd`. `multiap_controller` builds `ebtables` rules with a destination address from its own 1905 logic, and its `popen` is an interface read. `ct_top` formats `ip neigh show` for a CLI argument. `domos-qosd` calls the local netreq ipset helpers and ships one fixed `iptables -S` check. `air-cds`, `air-detector`, `air-di`, `air-journal`, `air-map-datasync`, `air-qos`, `air-steer-ng-daemon`, `aircdf-daemon`, `mosquitto`, `map-dpp-configurator`, and `edge_stub_middleware` have no shell string. `airlauncher-daemon` and `cloud-comm` were already opened.

## Web locations that skip the session check

The main server is `etc/nginx/nginx.conf`. The catch-all location runs `checkrequest` and `handleAuth` before any page. A path that is not in the web ruleset is rejected before the page runs. `handleAuth` accepts the SRP POST only on the login and password paths.

These locations do not call `handleAuth`:

- `/css/`, `/img/`, `/font/`, and `/js/` serve static files.
- `/intercept.lp` and `/no-internet-connection-intercept.lp` render those pages. The intercept page POST sets a data-usage event to one of two fixed names. The no-internet page query action `restart` is below.
- `parental-block.lp` still calls `checkrequest`, so an unauthorized request is sent to the login page.
- `127.0.0.1:55555` only. `/ra` reads its query and can enable an assistance account. `/reloadWebUsers` reloads the user table. The listen address is localhost.
- Port 8080 accepts a direct connection. A cookieless GET of `/` returned nginx 404. The redirect in that server runs only when a data-usage flag is set, a voice or IPTV mode matches, or the WAN is down.
- Port 55556 accepts a direct connection. A cookieless GET of `/` returned 302 to the UCI LAN name plus `/parental-block.lp`. The Location host was not the request Host.

`reload_assistance.lua` does not build a shell command. An unknown login name does not become a user: `changeUser` is called with no user record and the session stays at the default role. The random verifier for an unknown name comes from `/dev/urandom`.

## DHCP option 125 and the password helper

`processopt125.lua` reloads `cwmpd` with a fixed command. It will write an ACS URL from WAN DHCP option 125 only when `use_dhcp` is not `0` and the decoded URL is on `allowed_dhcp_acs_url`. The shipped `etc/config/cwmpd` has `use_dhcp` `1`, `enforce_https` `1`, and an allow-list of Telia ACS URLs. A URL that is not on that list is not written. The command string is not the URL.

`setClashPassword.lua` is called from the user and remote-access data models. It passes the user and password to `update_passw.sh`. That is the management model, not an anonymous page. `gwfd` writes its own fifo path into a helper script. `ethoam` still executes the command string from its local ubus method, and it also pastes that string into `ps`. No web caller was found.

## WAN sensing scripts

The scripts under `etc/wansensing` run fixed init commands: `network`, `dnsmasq`, `odhcpd`, `cwmpd`, `dropbear`, `nginx`, `igmpproxy`, `dhcpopassthrud`, `mmpbxd`, `mwan`, `sysntpd`, `qos`, `ethernet`, and `mesh-broker`. `L3HandleOption125Main.lua` reads option 125 from the WAN status and does not paste it into a command. `L2EntryExit.lua` reads `nvram get lan_ifnames` and writes that local value back. The value does not come from the DHCP packet.

## Extra wireless helpers

`acsd2`, `afcd`, `bsd`, `ssd`, and `dhd` listen on sockets and have no `popen`, `system`, or `/bin/sh` string. `afcd` names `127.0.0.1`. `qosmgmtd` SHA-256 `b57fd21546f0dbf87eca1d13360154ca915db73b692c36d2872ed390e4ac8c42` binds a loopback socket and reads `/tmp/qm-cmd`. Its only `popen` is the fixed command `gunzip -c /proc/config.gz | grep "CONFIG_BRIDGE_NETFILTER=" | grep -o "[m|y]"`. An unsupported command name is rejected. `pppd` has the failure string for executing `/bin/sh`; that is the local script runner, and no peer field was shown choosing the program. No packet was sent.

## Bus access for the container user

`usr/share/acl.d/ubusd_acl.json` is the only shipped ubus ACL, and its user is `lxc_telia`. That user may call `up`, `down`, `renew`, `remove`, and `set_data` on the WAN, IPTV, VoIP, and management interfaces, and it may `set` a hostmanager device. It may read wireless and system info. The list has no `ethoam` method and no shell method. `udp_echo` is a command-line UDP responder with no `popen` or `system`, and no init script starts it. No packet was sent.

## Connection request

`cwmpd` logs `Authentication disabled. Connection Request Allowed` when a flag register is zero, and then continues. The shipped `etc/config/cwmpd` sets `connectionrequest_auth` to `0` and `connectionrequest_port` to `51005`. The binary has no check of the source-address list. `lib/functions/firewall-cwmpd.sh` accepts that port from the WAN only for `connectionrequest_allowedips`, drops other WAN sources, and rejects the LAN zone. An allowed request starts a session toward the configured ACS. It does not run a shell. The shipped `acs_url` is empty. On this unit the daemon is stopped. No packet was sent.

## XMPP connection request

`cwmpd` contains an XMPP connection-request path. It logs `ConnectionRequest JabberID NOT allowed` and `credentials do not match`. Argument 0 makes the reply `service-unavailable` with code `503`. Argument 1 makes the reply `not-authorized`. The Jabber-ID failure path passes 0. The credential-mismatch path passes 1. Both are error replies. The shipped `etc/config/cwmpd` has no XMPP server, user, or enable flag. On this unit the daemon is stopped. No packet was sent. The path does not run a shell.

## Guest web role

`etc/config/web` defines a `guest` user with role `guest`. Every content rule lists `admin`, `telia`, or `superuser`. None lists `guest`. `SessionMgr:authorizeRequest` allows the login path, then requires the session role to be present on that rule. A guest session fails that check and is sent to the login page. It does not reach a page that runs a command. No packet was sent.

## ubus socket

`sbin/ubusd` SHA-256 `238a97031904d9a7d00c68211f7e43adf8182ed0e140a2f988fa7610f7b163ab` calls `umask(0111)` and listens on `/var/run/ubus.sock`. A new client is accepted only when both the user and the group exist in the password database. The policy pointer is stored on the client at offset `0x58` and is set only when a loaded ACL matches that user. The check at `0x45d0` allows the call when that pointer is null or the uid is 0. The only ACL file is `lxc_telia`, so every other named local user is not limited by it. nginx runs as `nobody`. The live socket is mode 666, owner root. `nobody` is a local user and is not covered by `lxc_telia`, so the null-policy check allows that user's calls. The socket is not a LAN port. No call was made.

## Telnet and the Wi-Fi socket helper

`utelnetd` SHA-256 `d7a3153d18dd8cbf4389c033419cf1d9595f2bd444bda8871eb80a71064c5e60` is started only from `bcm-wlan-drivers.sh` when `WLAN_BTEST` is `y`. The script sets that variable to empty. The default program string is `/bin/login`. `wl_server_socket` contains `popen` and `/bin/sh`, and its usage text describes a shell command over a socket transport. No init script or config file references it. No packet was sent.

## Boot diagnostics

`wanconf` SHA-256 `8cfa30f209135f26727b20ef6a807e7dd4bb08797fff6195720528d50bf2cd6f` is started with no arguments. Its `popen` formats `cat /proc/modules | grep "^%s"` with the fixed names `bcm_pondrv`, `smtc`, and `pmd`. Another function runs `ps | grep r[g]s_logger`, then `kill -9` of that numeric pid, then the fixed command `bs /d/o testlogger`. None of those strings comes from a packet.

The transformer init starts the socat debug relay only when `trace_requests` is 1. That option is not in the shipped config. `/usr/bin/tr143` builds a diagnostic command from the diagnostics config, including the interface name, and is the management-triggered launcher. No packet was sent.

## wlssk

`bin/wlssk` SHA-256 `d7877f386e8fbdb2dfbe34b01d9580e40201bf17a5737c4ff8007ee314d48a99` calls `system` from many sites and `popen` from four. One `popen` runs the fixed command `/etc/init.d/wifi.sh dpdmode | cut -d '|' -f1`. The `ifconfig` helper builds the interface name as `wlN` or `wlN.M` and reads the MAC from nvram key `<ifname>_hwaddr`. `sub_17480` runs `mkdir -p` and `hnddm.sh` with values from `nvram_unf_get`. `wlevent_handler` is `sub_16408`. From `0x16408` through `0x16c80` there is no direct call to `system` or to those helpers.

`sub_185c4` runs `sh /etc/init.d/wifi.sh edpdbind wlN`. The script path is that literal, and `N` is the radio index in the loop. `sub_18b7c` runs `sh /etc/init.d/wifi.sh edpdunbind wlN`, with the interface name formatted from the same index. `sub_17288` builds `wlN` or `wlN.M` the same way and runs `wl -i <ifname> bss down` followed by `bss up` only when nvram `<ifname>_mode` exists and is not `ap`. `sub_140fc` builds the same interface name and sets its MAC from nvram `<ifname>_hwaddr`. None of these reads a field from a received frame. The `system` import has 49 call sites. **Full sweep (2026-11-07):** pairing all 53 `system`/`popen` sites with their formats found thirty distinct forms, every one of them a fixed script path, a `killall` target, an nvram-derived value, or an interface name built from numeric indices — with the one exception of the already-recorded message-bus path, whose words are prefix-checked and length-capped. No packet field reaches any site. `sub_15d28` is the startup path. It runs fixed program names when an nvram flag matches: `ceventd`, `acsd2`, `appeventd`, `wps_pbcd`, `wbd_master`, `wbd_slave`, `afcd`, `qosmgmtd`, `hspotap`, and `airiq_app -i wlN`. It also runs fixed `killall` commands for `bsd` and `ssd`. `sub_154a0` reads nvram `toad_ifnames`, splits it on spaces, copies at most 15 bytes of each token, and runs `toad -i` with that token.

`sub_145b4` builds `ifconfig <name> up`, `ifconfig <name> down`, `brctl addif <bridge> <name>`, and `brctl delif <bridge> <name>`, then passes each line to `system`. Its only caller is `sub_19404`. That function reads Broadcom CMS messages. When the message text contains `Hotplug`, it scans two words of at most 31 characters and passes them to `sub_145b4`. This function does not open a TCP port.

The program that formats `Hotplug %s %s` is `bin/hotplug`, the same file as `sbin/hotplug`, SHA-256 `f59282d2f5b9cb9390b29be9a1bd2859df4ebd08ace393515900d079aa409301`. `sub_10b44` reads `INTERFACE` and `ACTION` from the environment. It continues only when the interface name starts with `wl`, `radiotap`, `wds`, or `eth`, and only when the action is `add`, `register`, or `remove`. The bridge name in the command is the literal `br0`. `sub_10d00` forks and runs `/bin/sh` with `-c` and that command line. The same environment values are sent on `/tmp/wifi_msg_bus` toward the process named `wlssk`. This program does not listen. The environment is the one the kernel supplies when it runs a hotplug helper. `oalMsg_initUnixDomainServerSocket` in `libcms_msg.so` unlinks the path, binds an `AF_UNIX` stream socket, and listens. That function does not call `chmod` or `umask`, and neither `wlssk` nor the message library contains those strings. The live socket is mode 755, owner root, so any local user can connect. It is a Unix socket. `sub_145b4` places the first word in `ifconfig` and `brctl` lines and passes those lines to `system` when the action is `add` or `remove` and the word starts with `wds`, or when the proxy-STA check is set. The scan format copies at most 31 characters and stops at whitespace. This function does not check the other characters in the word. No message was sent. The path is named only by `hotplug`, `wlssk`, `wifi_md`, `libcms_msg.so`, `libnvram.so`, and `libbcm_comp_md.so`. No page or script names it. `sub_13668` runs `wl -i wlN reboot` and `ifconfig wlN down` or `ifconfig wlN.M down`. `N` and `M` are the radio and virtual-interface indexes. `sub_14a50` is the init path. Its `system` call is one fixed `ubus call` announcing that init is done, and it loads `*.so` files from `/usr/lib/wlssk-plugins/` when an nvram flag is set. `sub_159ec` runs the fixed command `wps_monitor&` only when an nvram value matches. `sub_18714` inserts its interface argument into `acs_cli2`, `wlconf`, and `ifconfig`. It does that only for the actions `pwrup` and `pwrdn`, and only after `sscanf` reads a `wl` index that is in range. The power-down caller builds that name as `wlN`. The bridge helper calls it with the interface word from the CMS message when that name is not a proxy-STA or radiotap-style name. `sub_13470` calls `devCtl_boardIoctl` with request `0xc0184201` and argument `6`, filling a 1024-byte buffer. It then `stat`s that buffer. Only when the path exists does it pass the same buffer to `system`. The text is the board driver's reply, not a field from a received frame. The event handler still has no direct `system` call. No packet was sent.

## DHCP SIP server hook

`etc/udhcpc.user` calls `/usr/bin/processsipservers` with the DHCP `sipsrv` value when that variable is set. The script writes it as the SIP proxy and registrar only when `mmpbxrvsipnet.sip_net.interface` equals the DHCP interface, then restarts `mmpbxd` if it is already running. The value is passed and stored in quotes. The shipped `etc/config` tree has no `mmpbxrvsipnet` file, so that comparison does not match.

The other hooks that exist are `parseopt125`, `parsevendorinfo`, `processlease`, `processpassthrough`, and `processserverid`. Option 125 and option 43 both call the ACS-URL writer that only accepts the shipped allow-list, then reload `cwmpd` with a fixed command. `processpassthrough` puts the option blob in a JSON string. `processlease` stores the lease time. `processserverid` is empty. `processerror`, `processip6rd`, `parsenovendorinfo`, `processopt230`, `parseopt60`, and `processrouter` are named by the hook and are not in the image.

`etc/odhcp6c.user` calls `parsev6vendorinfo` for DHCPv6 option 17. That script decodes the option and looks for `/usr/lib/lua/processv6vendorinfo.lua`, which is not in the image, so it logs and stops. `parsev6addresses` and `processv6opt230` are named and are not in the image. No packet was sent.

The live WAN client is `odhcpc` on `eth4` with `/lib/netifd/dhcp.script`, and its UDP port 68 socket is bound to every address. That script runs `eval` on the output of `ipcalc.sh`. `ipcalc.sh` prints only the addresses it computed with integer conversion. The script then sources `/etc/udhcpc.user`, which is the hook already reviewed. `odhcp6c` on `eth4` uses `/lib/netifd/dhcpv6.script`. That script compares the router-advertisement numbers before it writes them to sysctl, and it sources `/etc/odhcp6c.user`. A second `odhcpc` runs in a container on `eth0` with `/usr/lib/dhcp.sh`. That file is not in the host root. It passes the address and the router to `ifconfig` and `route` as arguments and writes nameserver lines. It does not `eval`. No packet was sent.

## L2TP

`etc/rc.d/S60xl2tpd` starts `xl2tpd`. `etc/xl2tpd/xl2tpd.conf` sets UDP port 1701 and `access control = no`. The `[lns]` and `[lac]` sections are commented out, so no tunnel is defined. `options.xl2tpd` contains `noauth` and `require-mschap-v2`, and it is only named from those commented sections. `ip-up` has no `ip-up.local`. No packet was sent.

## websockd, socat, and the L2TP server switch

`bin/websockd` SHA-256 `c0c4d42e93ffa48cc35d62ee64a54304f00e6b11bc3e96b64bbbb8d59e56c9c2` is started by `S98websockd`. It imports `system` once. That call passes a stack buffer. The only command-like string in the binary is `mpstat -P ALL 1 1 > /var/cpuinfo 2> /dev/null`. The decompiler crashed on that function, so the copy into the buffer was not shown instruction by instruction. No `popen` or `/bin/sh` string.

`etc/config/socat` has `enable` 0. `etc/config/vpn` has `l2tpipsecserver` `enable` 0, and `l2tp-ipsec-server` returns immediately in that case. No packet was sent.

## dosprotect and trafficmon

`dosprotect` appends the UCI `extra` string into an iptables command. That string is local config, not a packet. `trafficmon-ubus` creates a user of the same name with uid 0, gid 0, and shell `/bin/ash` if the user is missing. `user_add` writes the shadow password field as `x`, not an empty password. The cron line runs as that user. No packet was sent.

## mountd

`sbin/mountd` SHA-256 `7e182b4a4b471c17bbc9356ffa6782accba07c8a7f757e7448d67c710361303d` is started by `S99mountd`. When the kernel asks it to mount a device, it builds `mount -t <type> -o <options> /dev/<name> <path>`. The type and options come from a fixed table (`ext2`, `ext3`, `ext4`, `vfat`, `ntfs-3g`, `hfsplus`, `exfat`, and fixed option strings) unless a `mountd` UCI value overrides them. The device name is the kernel block name. An invalid path is rejected before that command. This is not a LAN listener. No packet was sent.

## Samba

`etc/config/samba` sets `enabled` and `filesharing` to 0, and `wan_access` to 0. `nqe` returns before adding shares when samba is disabled. `nqnd` and `nqcs` were already found to have no shell string. The `authentication` option is 0, and the `nqe` init script does not read that option. No packet was sent.

## hostapd control socket

`usr/sbin/hostapd` is on the image. The shipped `etc` tree has no `init.d/hostapd` and no `ctrl_interface` setting. The live processes are started with generated configs that set `ctrl_interface` to `/var/run/hostapd` and `wps_state` to 2. That directory is mode 750 and the sockets `wl0`, `wl0.1`, and `wl1` are mode 770, all owned by root. A process that is not root cannot connect. No packet was sent.

## ipset-dns

`usr/sbin/ipset-dns` SHA-256 `49f336de7db3698f697f3231a322315851389b4a14db042ccb56a702d317bbb8` is started by `S61ipset-dns` when a WAN nameserver is already known. The shipped config names the sets `domain-filter-ipv4` and `domain-filter-ipv6` and does not set a port, so the init script uses `53001`. It does not set an upstream server. No other shipped file names those sets.

The listener socket is UDP, family IPv4. After the address structure is cleared, the program stores family 2, the byte-swapped port from its third argument, and the address `127.0.0.1`, then calls `bind`. A query shorter than a DNS header is discarded. A full query is forwarded to the upstream server, and an answer whose id does not match is discarded. Address records in a matching answer are added to the named sets through netlink. There is no `popen`, `system`, or `/bin/sh` string. No packet was sent.

## DLNA

`etc/config/dlnad` sets `enabled` to 0. `S98dlnad` returns before starting `/usr/bin/dlnad` in that case. `sharing` and `share_all_folder` are 1 and are not read while the service is disabled. The binary was already found to have no shell string. No packet was sent.

## IGMP proxy

`etc/config/igmpproxy` sets the global `state` to 1, the LAN interface to `downstream`, and the WAN interface to `inactive`. `S70igmpproxy` starts `/usr/sbin/igmpproxy` SHA-256 `7942d541e05d11033b9540add8fca35cd044a6d43ceaba726ee088612ab0d973`. The multicast forward rule is added only for an interface whose state is `upstream`, and this config has none. The binary has no `popen`, `system`, `execve`, or `/bin/sh` string. No packet was sent.

## NTP

`usr/sbin/ntpd` is a symlink to `bin/busybox` SHA-256 `67d898cd07c588e1f78dd1bd03e906705a5a044c39dc5574684b08228f15c77f`. `etc/config/system` sets `enable_server` to 1 and does not set an interface. `S98sysntpd` therefore starts it with `-l` and does not pass `-I`. The LAN firewall zone input is `ACCEPT`. The guest and WAN zone inputs are `DROP`, and the guest allow rules do not name port 123. The live socket table shows `ntpd` on IPv6 port 123 only.

The script launcher is `sub_21ff0`. It runs the configured script and sets `stratum`, `freq_drift_ppm`, `poll_interval`, and `offset` with numeric formats. The calls pass the fixed words `step`, `stratum`, `unsync`, and `periodic`. `usr/sbin/ntpd-hotplug` sends those values to ubus. A peer name is used in a log line and is not the script argument. No packet was sent.

## DNS filter

`etc/config/parental` sets `mode` to `dns` and `enable` to 0. `S80dnsfilter` installs the port-53 NFQUEUE rule only when both are true, so that rule is not installed. It still starts `/usr/sbin/dnsfilterd`. That binary was already found to have no shell string. No packet was sent.

## Protocol helpers

`S95bcm_alg` loads the FTP, SIP, RTSP, TFTP, and H.323 connection-tracking modules when they are present, and it appends `net.netfilter.nf_conntrack_helper = 1`. The LAN zone also lists the helpers `ftp`, `tftp`, `snmp`, `pptp`, `sip`, `rtsp`, `irc`, and `amanda`. Those are kernel parsers for forwarded traffic. No shell script references `nf_conntrack_ftp`. The module is `lib/modules/4.19.235/kernel/net/netfilter/nf_conntrack_ftp.ko`, SHA-256 `3df3028e90f3998b5cc1f098aec794bbe884fc0d8c8862e1bd7518e3f2411a2b`. `nf_conntrack_sip.ko` SHA-256 `884a62a40797812f1a322ac08e1e98d6591ca60507f65877dcfc29c7ff079d7b` and `bcmkernel` `nf_conntrack_rtsp.ko` SHA-256 `c64a69894d6586d571c4c655cd61e4f931732af0b4dc03202d8f3dab02602a90` have no shell string. No packet was sent.

**Superseded for the RTSP parser (2026-11-07):** the `bcmkernel` module is aarch64 and keeps its symbol table. Its one packet parser is `help` (4172 bytes); the others are `get_cseq`, `memmem`, and `expect_rtsp_channel`. Relocation tables show the parser's only data-receiving primitive is one `skb_copy_bits` call, with the copy length taken from a stack slot that earlier instructions clamp with compare-and-branch arithmetic. Numbers are parsed with `simple_strtoul`, and the address text with `in4_pton`. `strcpy`, `strncpy`, and `sprintf` appear as imports, but the only relocation for any of them is one `sprintf` in the init code, which runs at load with the local module parameters. No unbounded copy of packet text is present. The module was not fully decoded, so a logic error is not excluded, but the easy memory-corruption class is ruled out.

**Mainline helper sweep (2026-11-07, REPORTED from the CVE records):** the kernel is 4.19.235. Two public fixes sit inside the version gap and both modules are shipped and loaded with the helper flag set. CVE-2024-26851 (`nf_conntrack_h323` ASN.1 bitmap length out of range, fixed in 4.19.310) parses attacker bytes in tracked RAS messages, and CVE-2026-23457 (`nf_conntrack_sip` Content-Length truncation on 64-bit systems, fixed only in 6.1.167 and later, so no 4.19 backport exists) mis-sizes the message boundary. A LAN client can send H.323 or SIP traffic through the router, so both parsers are packet-reachable; the impact class of both is parser confusion or denial of service, not a demonstrated memory write. CVE-2023-53619 triggers only when conntrack initialization fails, and CVE-2026-53349 requires module-unload rights; neither is network-reachable. No packet was sent.

**Engagement verified (2026-11-07, later pass — supersedes "No packet was sent"):** controlled probes from 192.168.1.150 through NAT confirmed the ALG chain is live. One UDP SIP INVITE with SDP (`m=audio 16384`) to a TEST-NET address on port 5060 produced **two `sip/audio` conntrack expectations** in `/proc/net/nf_conntrack_expect` (ports 16384/16385 toward the WAN address) — the `nf_conntrack_sip` parser processed attacker-supplied SDP bytes in kernel context and the NAT rewrite of the SDP address worked. A TCP SYN to port 1720 created an h323-range tracked flow the same way. The vendor's `/etc/init.d/bcm_alg` deliberately loads the h323/sip/ftp/tftp/rtsp helper modules and appends `net.netfilter.nf_conntrack_helper = 1` to `/etc/sysctl.conf` (live value 1; `sysctl.d/40-tch-default.conf` alone would set 0). Caveat: this BCM build does not print `helper=` in `/proc/net/nf_conntrack` (0 entries show it), so absence there is not evidence of non-engagement — expectations are the reliable signal. Both CVE trigger paths are therefore **VERIFIED packet-reachable from a LAN client**; no crash or parser-confusion PoC was attempted this pass (impact class per public records remains DoS/parser-confusion, not a demonstrated write). Two probes sent: one benign SIP OPTIONS, one SIP INVITE with SDP, one TCP SYN to 192.0.2.1.

## DHCP option passthrough

`usr/bin/dhcpopassthrud` SHA-256 `c306030d960bf08c5c1976e7e289e4dfa68abb3744f55cb5ca374298125a2e32` is started by `S18dhcpopassthrud`. The shipped `etc/config/dhcp` has no passthrough section. `etc/uci-defaults/tch_0050-dhcpopassthrud` adds one on first boot: the script is `/lib/dhcpopassthrud/dnsmasq.sh`, `options_needed` is 0, and WAN options 42 and 43 are copied into the LAN pool.

`sub_11828` forks and calls `execv` on that script. For an update it formats each option as `OPT_%d=` and writes the bytes as colon-separated hex from the alphabet `0123456789abcdef`, then puts that string in the environment. The option id on the script command line is printed with `%d`. The script reads the value back with `eval`. Because the value is hex, the raw option bytes are not the text the shell evaluates. No packet was sent.

## Soft switch

`S21softswitch` calls `/etc/init.d/ethernet softswitch`. That function reads the local `softswitch` flag for each non-WAN `eth` and `moca` interface and writes it to sysfs. It does not listen. No packet was sent.

## Field diagnostics

`etc/config/ngwfdd` sets `enable` to 0. `S99ngwfdd` returns before writing the outbound URL or starting collectors. The binary was already found to have no shell string. No packet was sent.

## WAN check

`usr/bin/wancheck` SHA-256 `658b8fb862c7a1aa028deb574eccc203666410f40c6c9f691d768bcaffe4de34` is a shell loop started by `S99wancheck`. It reads `ifstatus wan`, takes the `l3_device` name from that local status, and passes it to `ifconfig` in quotes. If the interface exists and has no address, it runs `ifup wan` or `/etc/init.d/network reload`. If the WAN stays down for an hour, it runs `reboot`. It does not listen, and it does not `eval` the status text. `network_logger.sh` is named and is not in the image. No packet was sent.

## Port manager

`S15portsmngr` reads the local `ports` config and writes speed, duplex, and pause for each `ethport` through `/lib/network/port.sh`. It does not listen. No packet was sent.

## Syslog

`etc/config/system` sets `log_port` to 514 and does not set `log_ip`. `S12log` returns before starting a remote forward when that address is empty. `/sbin/logd` still starts. It was already found to have no shell string. No packet was sent.

## Bulk data

`etc/config/bulkdata` sets the global `enabled` flag to 1, so `S20bulkdata` does not exit. The only profile, `profile_1`, has `enabled` 0. `usr/bin/bulkdata` SHA-256 `3b0add37aa4a9643cc57b0cef5368ed3468c56e0d7f8a244073a76f89a2321c8` skips a profile that is not enabled, so this config does not post and does not write a crontab line. The script's `os.execute` calls are `sleep` and a crontab update built from the local profile name and a numeric time. It does not listen. No packet was sent.

## MVFS and the alternate root

`S96mvfs` starts only when DLNA is enabled. `etc/config/dlnad` has `enabled` 0, so it returns first. `S99native_ee` runs boot scripts only for an `lcmd` root that is not `/`. The shipped roots are `/` and `/opt/`. The image has no `/opt/etc/rc.d` scripts. No packet was sent.

## Filesystem events

`usr/bin/fseventd` SHA-256 `d3055289c820c8616a4158ae1a4a6857406dc547b7fb8efb475969ed85b8d332` is started by `S95fseventd`. It uses the local sockets `/tmp/evd_listener_sock` and `/tmp/evd_producer_sock`. The binary contains no `chmod`, `umask`, `system`, `popen`, or `exec` string. It forwards mount-point events. It does not open a TCP port. Neither socket path exists on the running device. No packet was sent.

## Assistance trigger, certificates, and boot flags

`S85ra` runs `wget` against `http://127.0.0.1:55555/ra` when the WAN interface changes. The URL has no query. `S79sscert` generates the nginx certificate when the year is 2016 or later and the existing file is not mode `0400`. `S99zprozone` writes `0` to the boot-fail, boot-counter, and boot-bank files under `/proc/prozone`. None of these listens. No packet was sent.

## Button and Wi-Fi queue hotplug

`etc/hotplug.d/button/00-button` runs `eval` on the handler stored for the matching button. The event supplies the button name and the action, which select the row. The shipped `etc/config/button` handlers are `rtfd` with an optional local flag, `wps_button_pressed.sh`, `wifionoff.sh`, and a fixed logger plus `ubus send`. The script comment says stripping metacharacters from the handler was considered and was not done. The handler text is local config.

`etc/hotplug.d/net/10-broadcom-qos` calls `/usr/sbin/wifi_qos` SHA-256 `a21118776892d0dadf2cd2d1fa758f2b20f584337bf3e59186222cbd2a3b319c` with `addq` or `delq` and the kernel interface name. The script writes that name into the local `qos` config. It does not `eval` it. Neither script listens. No packet was sent.

## USB mount share name

`sbin/mountd` runs `/sbin/hotplug-call mount` with `ACTION=add` or `ACTION=remove`. `etc/hotplug.d/mount/00-samba` then calls `cs_get_device_info`. That function reads the disk vendor and model from sysfs, deletes the characters `` ( ) ` $ * . ; space / \ | ``, and passes the remainder to `eval`. Ampersand is not in that set, so it is still a separator when `eval` parses the result. The hash appended to the share name is four hex characters from `sha256sum`. The disk letter and partition number that other helpers pass to `eval` are reduced to letters or digits first. `mountd` stores the disk section name as twelve hex characters from `%08X%02X%02X`, or `000000000000` when it finds no serial. The later unquoted `eval` of that section name therefore receives hex. The vendor and model path above is the one that still reaches `eval` after the shorter filter. `mountd` also copies the raw vendor and model into its state config. `contentsharing.sh` does not read those config values. It reads the sysfs files again and applies the filter before `eval`. Samba file sharing is disabled, and this hotplug script still runs. This input is a USB disk identity, not a LAN packet. No packet was sent.

## websockd port

`S98websockd` starts `/bin/websockd -v 0`. `sub_12634` clears a libwebsockets context info and writes 7681 at byte offset `0x30`. The first field, the primary port, stays 0. In `lws_create_vhost`, a zero primary port makes the library read offset `0x30` and keep its low 16 bits. That value is 7681. The interface pointer stays null. A TCP connection from 192.168.1.150 to port 7681 succeeded. Ports 443, 51005, and 55555 refused the connection. No application data was sent.

`sub_1202c` is the websocket callback. Reason `0` only logs the new connection. Reason `0xb` copies the literal `mpstat -P ALL 1 1 > /var/cpuinfo 2> /dev/null` and passes that buffer to `system` only when the connection's stored word is not zero. The instruction that loads the literal is at `0x12144`, and `system` is the next call at `0x12174`. Reason `0x6` is the receive path. When that word is zero it reads an integer session key and calls `hsl_checkSessionKey`. That function rejects 0. Any other value is compared with the key stored by `hsl_setSessionKey`. **Superseded (2026-11-07):** `hsl_setSessionKey` and `hsl_checkSessionKey` are both exported by `libhttpdshared.so`; `websockd` is the only file in the image that links or even names that library, and it calls only the checker, so the `mpstat` path is dead code in the shipped image and no other component can reach the setter. A failed check clears the word and does not schedule the writable callback. The binary names a second protocol, `flowstats`. Its callback `sub_12d08` reads connections through `dpictl_get_connections` and does not call `system`. The only `system` call in the binary is the one above. A TCP connection to port 7681 was accepted and then closed with no application data.

## ocsd exec

`bin/ocsd` SHA-256 `59be25d62549f9a31246080ddcce6eea0c9412494198c2e151b58d577dfc20c3` is started by `S21ocsd`. It has two `execv` calls. `sub_16200` is the ubus method `ocs_bbf_saveConfig`. It forks and executes the fixed path `/sbin/reload_config`. `sub_125d0` forks and executes its fourth argument. No direct caller of `sub_125d0` was found. The TR-069 download fault strings, including the unsupported-protocol text, have no code reference. `sub_17068`, `ocs_bbf_xbcm_set_value`, formats the supplied path and value as one `uci` assignment and calls `uci_set`. It does not execute that value. The object is `neutron.ocsd.bbf` on the local ubus socket. `ocsd` does not open a TCP port. No packet was sent.

## Time-of-day host rules

`usr/lib/lua/todfw/todaction.lua` builds iptables and `conntrack` commands with `os.execute`. For a host rule it uses the UCI `id` string as the MAC and does not check that the string is a MAC. It then asks `hostmanager.device` for that MAC and appends each returned address to `conntrack -D -s`. `etc/config/tod` enables the global timer and has no host rule, so this path is not armed. The `id` comes from that config, not from a packet. No packet was sent.

## Host manager lookup

`usr/bin/hostmanager.lua` runs `nslookup` concatenated with an address. Before that, the message is kept only when the MAC matches six hex octets and the address matches dotted decimal or hex-and-colon. The lookup uses the address after that check. Characters outside those patterns are not stored.

The bridge table is read as 16-byte records and the MAC is formatted with `%02x`. `hostmanager.device set` stores `user-friendly-name` in UCI and does not pass it to a command. A hostname from a device message is stored without a character filter. `www/docroot/modals/wireless-client-modal.lp` puts that name into `ui_helper.createLabel`. `string.format` escapes a tainted argument before inserting it, and `ngx.print` escapes tainted output again. No packet was sent.

## DHCP lease name and the ping helper

`transformer/shared/dhcp.lua` reads a hostname from a lease line and returns it. No other file in the tree calls `getDhcpInfo`.

`ippinghelper.lua` reads the UCI `ipping` host when the IPv4 diagnostic value is read. If that string does not match a loose dotted pattern, it is concatenated into `nslookup`. The string is the stored diagnostic target, not the DHCP client name. On this unit `cwmpd` is stopped and the shipped ACS URL is empty. The web page that can set the target requires a session. No packet was sent.

## Traceroute helper

`usr/bin/igd_traceroute` reads the host from the `traceroute` UCI section and places it as one entry in an argument list passed to `process.popen`. The numeric options are converted with `tonumber` first. `usr/bin/igd_traceroute_helper` starts that program with `start-stop-daemon` and appends the section name, not the host. The `tch.process` module that implements `popen` is not in the copied tree, so this pass did not see whether that list is executed directly. The web page that sets the host requires a session. No packet was sent.

## DHCP client hostname event

Shipped `etc/config/dhcp` sets `dhcpscript` to `/lib/dnsmasq/dhcp-event.sh`. On add, update, and delete, that script puts the client hostname into a `network.neigh` ubus event. The hostname is expanded inside the script and is not passed to `eval`.

`hostmanager.lua` listens and stores the name. `ledframework/ubus.lua` reacts only when the interface is `br-wan` and the action is add, then calls a fixed name. `wansensingfw/wasasync.lua` builds an event name from the interface, the action, and the address, and does not include the hostname. `gre-hotspotd.lua` uses the neighbor MAC and address to pick a bridge port. `hotplug.dhcp` appears in the dnsmasq ACL and has no subscriber in the tree. No packet was sent.

## Unauthenticated WAN restart page

`etc/nginx/nginx.conf` listens on 80 and 443. The firewall rule `block_https_443_lan` rejects port 443 from the LAN zone. Port 80 is not in that rule. `location ^~ /no-internet-connection-intercept.lp` is a longer prefix than the catch-all, and that block does not call `checkrequest` or `handleAuth`. The page handles a query action named `restart` before it renders HTML. That action sets `rpc.network.wan_up` to `1` and calls `proxy.apply()`.

`usr/share/transformer/mappings/rpc/network.map` queues the token `rpc.network.wan_up` when the value is `1`. `usr/share/transformer/commitapply/rpc_network.ca` matches that token and its action text is `ifup wan`. Commit-apply loads each `.ca` line as a pattern plus an action and passes the action to `lasync.execute`. `lasync.so` contains `/bin/sh` and `execl`. The same directory's other actions are shell syntax. The action here is the fixed command, not text from the request.

The data-model client id is a random value created when `datamodel.lua` loads. It is not the web session. The session check that every other page uses is the one this location skips.

The same page's `wanIpStatus` query prints whether the WAN is up. `/intercept.lp` also skips `handleAuth`. Its POST sets `rpc.datausage_notifier.event` to `ignore_limit` or `ignore_threshold`, and that setter sends a ubus event `datausage.` plus that fixed name. A live GET of that path from 192.168.1.150, with no cookie and no query, returned HTTP 200 and the reconnect page. It was not the login form. The restart action was not sent, so the live `ifup` was not observed. **DERIVED:** the restart action is a GET with no session and no token, so a request fired by any web page visited by a LAN client would also reach it, limited only by the browser's public-to-private request rules. That cross-site path was not tested.

**VERIFIED live (2026-11-07, later pass):** two paced GETs from 192.168.1.150 with no cookies: `?action=wanIpStatus` → HTTP 200 `success` (unauthenticated WAN-status oracle), `?action=restart` → HTTP 200 `true`, and the WAN interface restarted — `network.interface.wan` uptime fell from 18,756 s to 10 s, with `mwan`/`firewall`/`hotplug` logging `ifup` for `wan`/`wan6` at 02:55:50, the same IPv4 re-acquired on DHCP, and LAN SSH unaffected. The unauthenticated chain is confirmed end-to-end; impact remains the fixed `ifup wan` command (reconnect control / DoS-class), with no injection into the command.

The same page copies the `url` query into a script string with `ngx.print`. The page loads `web.content_helper`, which loads `web.web`. That module taints query values and escapes `<`, `>`, `&`, `"`, `'`, and `/` before printing a tainted string. A later GET with a plain `url` value returned that value unchanged in the script string. No other character was sent. The escape function's comment says it covers an HTML context.

## Login and password pages

`/login.lp` and `/password` are allowed before a role check. `handleAuth` accepts only POST. On `/password` every POST ends inside `handleAuth`: the SRP exchange, a password change after that exchange has set `changeAllowed`, or a 400. The page's own `PasswordChanged` and `resetLegacySalt` writes are not reached.

On `/login.lp` the last-access branch writes `/etc/lastaccess` and can return a LAN address. That branch is inside the `lastAccess` variant, and `www/lua/variant_helper.lua` sets that variant to false. The page also copies each user name and legacy salt into a script string when that salt is not empty. A live GET with no cookie returned HTTP 200. Those two strings were empty, and the variant value in the page was false. The session-status query returns the session role. A new session role is an empty string.

`server_parental.conf` listens with `tproxy` on 55556 and redirects to the hostname and domain from UCI, then `/parental-block.lp`. The request path is not part of that URL. The copied tree has no `ui_server.conf`. A later direct GET confirmed the 302 and that the Location host comes from UCI.

## Disabled listeners and the throughput test

`etc/config/xinetd` has its only service commented out. `socat` `http` is enable 0. The WAN wake proxy is enable 0. Both UDP echo sections are Enable 0 and UDPPort 0. `intercept` is enabled 0. Both DDNS services are enabled 0. The IPsec L2TP remote is enabled 0. `obuspa` daemon enable is 0. `printersharing` is enabled 1, which is what starts `cupsd`. `tr143` diagnostics are State Idle and DiagnosticsState None.

`usr/bin/tr143` builds the diagnostic command from those UCI values and runs `$prog $opt` with the option string unquoted. The download URL is one of those values. Nothing under `www` sets it. The commit-apply rule that starts a test is the management model. `cwmpd` is stopped and `obuspa` is disabled. No test was started.

## Neighbour monitor

`etc/init.d/neighm` starts `/usr/bin/neighmd` with no enable flag. SHA-256 `2acbb3a880c035985bc4e87afc9bff22c91546d84d0c1a1d64b6c054e55a6188`. The LAN section turns on SLAAC discovery and duplicate-address snooping. The binary has no `system`, `popen`, `execve`, or `/bin/sh` string. It publishes `network.neigh` and `network.link`.

WAN sensing turns a neighbor event into the name `network_neigh_`, the interface, the action, and the address. The state machine looks that name up in the current state's event table. A missing name stays in the same state. No script under `etc/wansensing` contains `network_neigh_`. The L2TP/IPsec server in `etc/config/vpn` is enable 0. No packet was sent.

## Multicast snooper and the traffic cron

`etc/init.d/mcsnooper` starts `/usr/bin/mcsnooper` with no enable flag. SHA-256 `2d553ef28f967416e883f4f6a63689b9bca6636ca4857238cdaa9ab842e0956c`. The LAN section has IGMP snooping on. The binary has no `system`, `popen`, `execve`, or `/bin/sh` string. It connects to ubus and subscribes to `ubus.object.add`. This pass did not decompile the multicast parser.

`etc/init.d/trafficmon-ubus` adds a user named `trafficmon-ubus` with uid 0, shell `/bin/ash`, and a shadow password field of `x`. That field is not a password hash. The crontab entries run `/usr/bin/trafficmon-ubus` with the interface names `wan`, `mgmt`, `voip`, and `iptv` from `etc/config/system`. The program has no shell string. No packet was sent.

## Multicast snooper, traffic monitor, and the hotspot daemon

`etc/init.d/mcsnooper` starts `/usr/bin/mcsnooper` with no enable flag. SHA-256 `2d553ef28f967416e883f4f6a63689b9bca6636ca4857238cdaa9ab842e0956c`. It has no `system`, `popen`, `execve`, or `/bin/sh` string. The LAN bridge has IGMP snooping on. The binary was not decompiled.

`etc/init.d/trafficmon-ubus` adds a user named `trafficmon-ubus` with uid 0, gid 0, and shell `/bin/ash`. The shadow password field it writes is the single character `x`. The crontab runs `/usr/bin/trafficmon-ubus` with the interface names `wan`, `mgmt`, `voip`, and `iptv`. That script reads the interface's `ifname` from UCI and places it in one `ubus call`. It does not listen. SHA-256 `713db56d2b8877dd9a0fd36bc3e0c38e9756ce6fe0aa695e93affe10924ab3ed`.

`gre-hotspotd` global enable is 1, so `/usr/bin/gre-hotspotd.lua` starts. The hotspot section enable is 0. The process registers ubus listeners for `wireless.ssid` and `network.interface`. Its `ping` command uses an address returned for a configured tunnel peer. No TCP or UDP listen showed up in that file. No packet was sent.

## Firewall exceptions

The LAN zone input policy is ACCEPT. The guest zone input policy is DROP. Guest exceptions that accept traffic to the router are ICMP, DHCP port 67, and DNS port 53, plus the IPv6 ICMP rule. `block_https_443_lan` rejects port 443 from the LAN.

SIP port 5060 and CWMP port 51005 are accepted only from `194.255.167.128/25` on the WAN and VoIP zones. The tree has no `mmpbx` init script and no `mmpbx` binary under `usr/bin`. The firewall include names `/lib/functions/firewall-mmpbx.sh`, and that file is not in the tree. Two LAN rules mark forwarded TCP ports 5055 and 8060 for the RTSP helper. They are not local listeners.

`mud` starts only when `/var/run/mvfs.pid` exists. `mvfs` starts only when DLNA is enabled. Shipped `etc/config/dlnad` has enabled 0, so neither starts. The high-rule group is enabled 0. The default LAN-to-WAN rule is ACCEPT. No packet was sent.

## Ethernet manager and the rate limiter

`etc/init.d/ethmngr` starts `/usr/sbin/ethmngr` with no enable flag. SHA-256 `7fd41c3ffaa71715ccbdc34cfd1584d953c79b689907385f2c6eb87465072e21`. It has no `system`, `popen`, `execve`, or `/bin/sh` string. It adds a local ubus object named `ethernet` and reads interface counters through `libethernet.so`. The directories `www/docroot/js`, `css`, `img`, and `font` contain no `.lp`, `.lua`, or `.sh` file, so the unauthenticated static locations have nothing to execute.

`dosprotect` globals enabled is 1 and rpfilter is 0, so the reverse-path chain is not installed. Each rate-limit section appends its `extra` text to an iptables command. Those texts are local config. The shipped SYN and FIN extras match flags on interfaces other than `br-lan`. No packet was sent.

## Lua commands built from a value

A search of `usr` and `www` for `os.execute` and `io.popen` in Lua found the call sites below that were not already tied to a fixed command.

`usr/lib/cwmpd/transfers/checkOngoingServices.lua` builds a `conntrack` filter from firewall destination ports with a numeric format, then reads the result. That file is the CWMP transfer check. `cwmpd` is stopped.

`restrict_internet.lua` would delete conntrack rows for addresses stored by hostmanager. The only commit-apply rule that names it is the token `guiaccessonly` in `uci_firewall.ca`. No mapping sets that token.

`transformer/shared/common/network.lua` defines `executeCommand` and nothing in the tree calls it. `www` has no `os.execute` or `io.popen`. No packet was sent.

## Hotplug scripts

`etc/hotplug.d/dhcp`, `neigh`, and `tftp` are empty. `net/10_ethoam` calls `ifadd_event` with the kernel device name. That function stores the name and never reads it. The ubus command it sends is `/bin/tmsctl` with an empty argument. The tree has no `etc/config/ethoam`. `net/00-sysctl` uses the device name only as a match against local sysctl files, then pipes the matches to `sysctl`. `ieee80211/10-wifi-detect` runs `/sbin/wifi config`. The DSL script starts or stops a fixed helper. Button and USB mount scripts were already covered. No packet was sent.

## MLD proxy

`etc/init.d/mldproxy` starts `/usr/sbin/mldproxy` on every boot. SHA-256 `bd9e3ffd1f25f62ffa614fdd20a2d0d76d849733dd7353e1014336035a56631d`. Globals state is 1. The LAN interface is downstream. `wan6` is inactive, so there is no upstream to forward to. The dynamic symbol table does not import `system`, `popen`, or `execve`. The word `system` in the file is the program's own `system_set_src_filter` and `system_vif_add` names. The binary was not decompiled. No packet was sent.

## QoS management daemon

`usr/sbin/qosmgmtd` SHA-256 `b57fd21546f0dbf87eca1d13360154ca915db73b692c36d2872ed390e4ac8c42` imports `system`. `sub_1e074` calls `ether_etoa` on its station argument, then `snprintf`, then `system` on that buffer. One format is `fc flush --mac %s &> /dev/null` with the converted address. The next format is an iptables rule whose `--mac-source` is the same text and whose bitmap and limit are the bytes at station offsets `0x18` and `0x19`, printed as numbers. `usr/lib/libshared.so` contains `%02x:%02x:%02x:%02x:%02x:%02x`. `ether_etoa` itself was not decompiled. No file in the tree writes `/tmp/qm-cmd`. No init script names `qosmgmtd`; `wlssk` can start it from nvram, and that key is not in the shipped `etc` tree. No packet was sent.

`mcpd`, `wifi_md`, `ssd`, `debug_monitor`, `wbd_slave`, `bsd`, `wbd_master`, and `aspmd` are below.

## Wi-Fi message daemon and mcpd

`bin/wifi_md` SHA-256 `4838d6a46c6998b412032920d349f40706385306337ef70cbc9c37387dfeb402` is started by `etc/init.d/wifi_md.sh` when `/proc/net/dev` has a `wl` interface. `sub_11c38` calls `system` only when the message word equals `0x1000080d`. The argument is the fixed string `killall wlssk`. The stop action of that init script sends the same word with `send_cms_msg`. No LAN socket was found in this function.

`bin/mcpd` SHA-256 `a4ec09324042d2f5b3cdcc7ee38d0f28603888771bdbb4941160548f19a200de` imports `system` and contains iptables commands whose interface field is a `%s`. The only mention in the init tree is a comment in `startup_ctl.sh`. No script starts it. No packet was sent.

## Softblock daemon

`usr/sbin/ssd` SHA-256 `457f8345db41d79d915324636fcdd95fdf7d49aef86a8f6b2431cad2d62423ab` imports `system`. `sub_12a14` reads an interface name from nvram, copies at most 15 bytes, and on a matching mode value formats `wl -i %s mac none` and passes that buffer to `system`. The daemon's log calls its socket a loopback socket. No init script under `etc` starts `ssd`. No packet was sent.

## Crash monitor

`etc/init.d/bcm-wlan-drivers.sh` starts `/usr/sbin/debug_monitor` with the UCI kernel-crash path. SHA-256 `109af0e9e75940cfdf71652d466d7d146cc7279279058ff2265247036579348d`. `sub_130e4` calls `system` with literal command addresses: the `bcm-wlan-drivers.sh` stop and start lines, `nvram restart`, and `echo 1 > /proc/prozone/reboot`. The same function formats `wlconf wl%d` with its second argument and passes that buffer to `sub_11b18`, which also calls `system`. **Superseded (2026-11-07):** the `cp %s%s %s%s` and `rm -f %s` formats take the kernel-crash and backup directory paths from the same local UCI configuration; every one of the binary's ten `system` sites uses those config paths, fixed literals, or numeric arguments. No `listen` or `socket` string was found. No packet was sent.

## Mesh slave

`usr/sbin/wbd_slave` SHA-256 `fc5170e9d2abea6bd85321d6e0f11be35c68ab638d03eb4e4a55183aa35ea86e`. In `sub_20f5c` the roam and CSA changes go through `blanket_set_roam_off` and `blanket_set_client_csa`. `system` runs only when a flag bit is set, and the buffer is `wpa_cli -p /var/run/<field>_wpa_supplicant -i <interface> ap_scan 0`. The interface is the string at offset `0xf` of the same record. The middle field is the string at offset `0xb8`. **Superseded (2026-11-07):** three scan passes (direct stores to `+0xb8`, base-add-then-store in `wbd_slave`, and direct stores in `libshared.so`) found no writer for that field, so it travels inside a block-copied record from the daemon's local message sources rather than from any direct write. The daemon is loopback-only, so the line's exposure stays local. No init script under `etc` names `wbd_slave`. No packet was sent.

## Band steering daemon

`usr/sbin/bsd` SHA-256 `f9086b606d8531f66f1ddd6b3092822b594da46753ba4e07c8a0a95856120940`. Its log calls the socket a loopback socket, and the binary contains `127.0.0.1`. The only call to `system` is in `sub_135b8`. It formats `cat %s` with the literal path `/tmp/bsd.log` after that file exists. No init script under `etc` names `bsd`. No packet was sent.

## Mesh master and ASPM

`usr/sbin/wbd_master` SHA-256 `95fdb5468413ccb58c7500b5fabf874673e2de63c7e802b933d5732e123e348c`. `sub_16220` calls `system` with either `hostapd -B /tmp/map_ctrl_hapd.conf &` or `hostapd -dddtK /tmp/map_ctrl_hapd.conf &`, chosen by the nvram value `map_ctrl_hapd_dbg`. `sub_4beec` calls `system` with `hostapd_cli` against `/var/run`. One form reloads. Three forms set `dpp_connector`, `dpp_csign`, or `dpp_netaccesskey` from the matching nvram value when that value is shorter than 1537 bytes. No init script under `etc` names `wbd_master`.

`usr/sbin/aspmd` SHA-256 `83920b6fec1ab0046983b7eed03efcbeea6a54cb1e6401ed3bb94a8319365da0`. Its usage text is a command line with flags. Three sites format `echo %s > /sys/module/pcie_aspm/parameters/policy` immediately before `system`. The file also contains `default`, `performance`, and `powersave`. **Superseded (2026-11-07):** its complete format inventory is the policy echo, `wl -i %s aspm 0x%x` with a numeric policy, and its usage text; the interface name comes from its command-line prefix. All six `system`/`popen` sites are covered by those bounded formats. No init script under `etc` names `aspmd`. No packet was sent.

## Live overlay page

The running nginx config matches the firmware locations and adds `/genesis/`, `/genesis`, `/genesis/api`, and `/genesis/api/`. Each one calls `checkrequest` and `handleAuth` before `/genesis/ui.lua`. The web rules for those paths list `admin`, `telia`, and `superuser`. A GET with no cookie returned the login page. The page's POST commands are fixed names: toggle, cache, an address that matches a dotted form, fallback, Tailscale start or stop, route acceptance, telemetry block or allow, and two diagnostic reads. No command from that page was sent.

## Live listeners

A read of the running socket table shows nginx on 80 and 443, CUPS on 631, websockd on 7681, dnsmasq on 53 and 67, dropbear on 22, ntpd on IPv6 123, and two `hostapd` processes on 49152 and UDP 1900. `charon` is bound to UDP 500 and 4500 on every IPv4 and IPv6 address. The mesh, QoS, and event sockets that were checked earlier are on 127.0.0.1.

Listener binary versions: the live `dnsmasq --version` prints 2.85 with DNSSEC off and the UBus and dns-filter options on. The dropbear banner on port 22 is `SSH-2.0-dropbear` with no version; the ROM binary carries the constant 2020.81. `cupsd` identifies itself as 2.2.10 and `busybox` as 1.34.1. The public-issue applicability for dnsmasq is worked out in its own section below. For busybox 1.34.1: the ntpd amplification fix predates it (CVE-2016-6301 was fixed in 1.25.1), so the one busybox listener on port 123 is not affected; the netstat and nslookup escape-sequence issue CVE-2022-28391 is in range but needs a human reading the output on a VT-compatible terminal, which the router does not have; the awk use-after-free family is a shell applet reached here only with WAN-DHCP-derived values. For hostapd 2.10: the RADIUS advisories 2024-1 and 2026-5 do not apply because no RADIUS server is configured; the SAE downgrade advisory 2024-2 needs SAE hash-to-element, and the live config runs SAE with hunting-and-pecking, so it does not apply; the multi-link parsing advisory 2026-1 concerns MLO support that hostapd 2.10 does not contain. These statements are REPORTED from the advisory records; the live configs were read only. For the others, whether a public issue applies to these builds was not tested; that statement would be REPORTED, not verified.

`dnsproxy` listens on 127.0.0.1 port 5053. The live dnsmasq config forwards to that address. The proxy config names listen addresses, bootstrap, upstream, fallback, cache, and DNSSEC. It has no command key. It is not a LAN port.

The processes that are not root are `logd`, `dnsmasq`, the nginx worker (`nobody`), and one `socat` running as `lxc_telia`. That `socat` listens on `/var/run/lcm_ipc_lxc_ee/ubus.sock`, which is mode 755, and switches to `lxc_telia`. That user is the one the ACL covers. The socket is not a LAN port.

Every process uses the host network namespace. A listener in another namespace is not present.

`eapd` listens on 127.0.0.1 only. SHA-256 `190f2ebd7d8f98cce53e7846b8d990883f47285c63c825f6a00113113f999a9a`. Its dynamic symbols do not include `system`, `popen`, or an `exec` function. No packet was sent.

No shadow password is empty. The uid 0 accounts with a shell are `root`, `tchroot`, and `trafficmon-ubus`. The `tchroot` field starts with `!`. The `trafficmon-ubus` field is `x`. `mosquitto` is running and its only listener is `/run/airties-edge/mosquitto.sock`, mode 770, owner root. The config allows anonymous clients on that socket. It is not a TCP port, and a process that is not root cannot connect. No connection was made.

`xinetd` is listening on IPv6 TCP 60443. `/etc/xinetd.d/remote` is enabled, runs as root, and redirects that port to `::1` port 443. Nginx treats port 443 as the assistance session. No firewall rule names 60443. The LAN zone input policy is ACCEPT. No connection to 60443 was opened.

The live assistance record is active, the user is `assist`, and the role is `telia`. The salt and verifier are empty. The session code uses that record because the user exists, so it does not substitute the random verifier it uses for an unknown name. The user has no source-address allow-list, and that check allows the request when the list is absent. `xinetd` presents the connection to nginx as localhost. `srp.Verifier` passes the salt, the verifier, and the client value to `BN_hex2bn`. A zero return makes the constructor return nil, and the login handler then stops. An empty string is not a hex number, so that call returns zero. No login was sent.

`ipsec status` reported no security associations. The live `/etc/ipsec.conf` and `/var/ipsec/ipsec.conf` contain no connection. `/var/run/charon.ctl` is mode 770, owner root, and the vici socket is absent. No IKE packet was sent. `tailscaled` (the project's own overlay install, version 1.104.5, userspace-networking mode) binds TCP 0.0.0.0:49037, but its accept path refuses connections not addressed to loopback or the tailnet: a connect to 127.0.0.1:49037 succeeds on the box, and the same connect to 192.168.1.1:49037 is refused both from the box and from the LAN, so the port is not LAN-exposed despite the bind. No firewall rule names 49037; the refusal comes from the daemon.

There is no RA guard on the LAN bridge: the ebtables filter tables are empty and the ip6tables ICMPv6 rules are the standard zone allow-lists, so a main-LAN client can emit router advertisements that other main-LAN clients will process. The router itself ignores RAs (`accept_ra` is 0). Guest clients are blocked from the LAN bridge. This is a client-to-client trust issue inside the LAN, inherent to the shipped bridging design.

Two live `hostapd` processes are `/usr/sbin/hostapd`, started with `/tmp/wl0_hapd.conf` and `/tmp/wl1_hapd.conf`. Those configs set `bridge` to `br-lan` and the interfaces to `wl0`, `wl0.1`, and `wl1`. `sub_ab578` runs `execlp("ovs-vsctl", "ovs-vsctl", "add-port", <name>, <name>)`. The names are separate arguments. One caller passes the bridge and interface arguments of the nl80211 bridge helper. The WDS caller formats the port name from the interface name, the text `.sta`, and an integer, and limits that name to 16 characters. No packet was sent to 49152.

## dnsmasq version and public issues

The live `dnsmasq --version` prints 2.85. The compile options are IPv6, UBus, DHCP, TFTP, conntrack, and dns-filter, with **DNSSEC and DHCPv6 off**. The live config forwards every query to the local `dnsproxy` on `127.0.0.1:5053`, sets `script-arp`, and adds `/tmp/dnsmasq.d`, which holds only the `dhcpopassthrud` fragment. There is no `address=` line, no lease-change script, and no `add-subnet`. The daemon runs as the non-root user `dnsmasq`.

Against the public fix record (REPORTED from the upstream changelog and the May 2026 writeups coordinated as VU#471747; not reproduced here):

- **CVE-2026-2291** is a heap overflow in the DNS cache: escaped label text can exceed the fixed cache slot. The affected range is every release from 2.73 to before 2.92rel2, so this 2.85 build is in range. The trigger is a crafted upstream response with a name about four times the RFC 1035 255-octet limit. On this unit that response cannot reach the cache: `dnsmasq` forwards to the live-overlay `dnsproxy` (AdGuard, not present in the ROM copy), which parses every upstream response with `github.com/miekg/dns` compiled at version **v1.1.72**. In that version `UnpackDomainName` counts each label against a 255-wire-octet budget and returns `ErrLongDomain` for any name past it, so the crafted response fails parsing inside the proxy and is dropped before `dnsmasq` sees it. The upstreams are DoH endpoints, which reject the oversized name first. The trigger needs the crafted bytes to arrive as an upstream response, and `dnsmasq` accepts responses only from its configured forwarder on loopback. VERIFIED: the build is in the affected range. DERIVED: the network path to the bug is closed by the proxy's parser at this firmware. No query and no response was sent.
- **CVE-2026-4890** and **CVE-2026-4891** are DNSSEC parsing bugs. This build has no DNSSEC, so they do not apply.
- **CVE-2026-4892** is a DHCPv6 helper overflow that needs DHCPv6 support and a lease script. This build has no DHCPv6 and no lease script, so it does not apply.
- **CVE-2026-4893** is an EDNS Client Subnet check bypass that needs `add-subnet`. It is not configured, so it does not apply.

## cupsd configuration and public issues

The live `/etc/cups/cupsd.conf` was obtained read-only. It is 34 lines: `Port 631`, `Browsing On`, no `<Policy>` section, `<Location />` allowing `127.0.0.1` and `192.168.1.0/24`, and `<Location /admin>` with `AuthType None` and `Allow From All`. This resolves the effective-config unknown in the earlier CUPS matrix.

**DERIVED from upstream `conf.c`:** with no Policy section, cupsd auto-creates a `default` policy in which read and print operations are anonymous, job-owning operations require `@OWNER` or `@SYSTEM`, and the state-changing printer and class operations require `@SYSTEM` with the location's default authentication. That matches the earlier live matrix: unauthenticated reads succeeded, `CUPS-Get-Devices` executed (it falls in the permissive all-operations tail of the auto-created policy), and `CUPS-Create-Local-Printer` was forbidden. The permissive `<Location /admin>` does **not** make IPP administration anonymous: IPP requests are dispatched against the request resource and the auto-created policy, not the web-admin location, and the browser interface returns 403 for every page path, re-verified from inside the allowed LAN subnet.

Public fixes after 2.2.10 (REPORTED from the upstream release notes and patch; not reproduced here):

- **CVE-2019-8675 and CVE-2019-8696**, SNMP ASN.1 overruns in `snmp.c`: not reachable in this configuration. There is no SNMP discovery directive, no configured printer, no UDP 631 listener, and `cups-deviced` errored internally in the earlier matrix.
- The 2.2.12 "IPP buffer overflow" is a `httpPrintf` 16-kilobyte stack buffer with no length check on its formatted output. **VERIFIED in the shipped build (2026-11-07):** `cupsd` needs `libcups.so.2`, and the shipped `usr/lib/libcups.so` `httpPrintf` reserves exactly `0x4000` bytes of stack and has neither change of the upstream fix — the vulnerable form is present. **Traced to the call sites (2026-11-07, pinned v2.2.10 source):** cupsd itself contains no `httpPrintf` call. The server-side formats live in libcups's response writer: the status line, one `"%s: %s"` per response header field, and the cookie line. Every response field cupsd sets is fixed text, configuration-derived, or a bounded local copy — the error-page message goes to the body writer, and the only path that copies network input into response fields is the CGI script-header loop, which requires the web interface that returns 403 on this device. The overflow therefore needs a formatted string past 16 KB, and no network-reachable caller can produce one in this configuration. The trigger would re-open if the web interface or a CGI path is enabled. No probe was sent.
- The 2.2.12 scheduler fixes move the client-disconnect EOF check and clear the cookie on error responses. The disconnect is trivially reachable from the network and the impact class is a daemon crash; it was not tested.

The dropbear ROM constant is 2020.81. The upstream changelog after that release lists security fixes for X11 forwarding, `authorized_keys` parsing, forced commands, unix stream forwarding, and the scp client — all post-authentication or client-side; no pre-auth server fix was found there. REPORTED.

## wps_pbcd shell commands

`usr/sbin/wps_pbcd` SHA-256 `05f8dba76b84a55d0847d5bf6b3c6ce5afd5278dd65efcb41b7580aca37d80da` runs as root, listens on UDP 127.0.0.1:58032, and imports `system`. Its 24 `system` call sites are all inside one function. Each site clears a 1024-byte stack buffer, fills it with `snprintf`, and passes it to `system`. Every format is a `hostapd_cli -i %s` command: `set dpp_connector %s`, `set dpp_csign %s`, `set dpp_netaccesskey %s`, `reload`, `set ssid %s`, `set wpa_passphrase %s`, and fixed-text `wpa`, `wpa_key_mgmt`, and `ieee80211w` variants. The interface name is a buffer inside the daemon's context structure; the credential strings are stack buffers the function fills first from files and `nvram_get`. The function also calls the MAP helpers `wl_wlif_is_map_onboarding`, `wpa_supp_map_apply_creds_to_supp`, and `wl_wlif_apply_dpp_creds`.

The init code stores this function as a callback inside the context structure, and a dispatcher loads that slot and calls the callback indirectly. The dispatcher and the callback are reached from the `wl_wlif` MAP code in `libshared.so`, not from a LAN socket.

**Loopback 58032 protocol addendum (2026-11-07, VERIFIED — closes the socket's own shell reachability).** The UDP socket in the init path is confirmed in disassembly: `socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)` with `SO_REUSEADDR`, bound to `127.0.0.1:58032` (sockaddr built from the constants `0x0100007F` and `htons(0xE2B0)`), inside the Broadcom `bcm_usched` event loop. The datagram parser: a 16-byte interface name at offset 0, a **big-endian u32 message type at offset `+0x2c`**, accepted range **7–26**, dispatched by jump table; everything else is dropped. The interface name is looked up against the per-interface config records (`strncmp`, 4 records) for the type-26 path. The non-trivial cases call the WDS handler and UI updaters (`wl_wlif_update_wps_ui`, `wl_wlif_update_dpp_ui`, `hapd_wpasupp_wds_hndlr`); none reaches the `system()` applier. The WDS handler (`hapd_wpasupp_wds_hndlr` at `0x135a0` in `libnv2hapdcfg.so`, ROM md5 `73697caa5d94a1111a3df530d7387b19`, same as live) re-checks the `"wds"` name prefix and a message-type value of 1, then builds an nvram key `%s_hwaddr` from the (computed) WDS interface name, requires the peer MAC in nvram to sort below the local MAC, requires `wpasupp_dbg` to be exactly `"1"`, and only then runs its one `system()` — a **completely fixed command**: `wpa_supplicant -Dnl80211 -B -ddK -b br0 -g /var/run/wpa_supplicant-global` (format `wpa_supplicant -Dnl80211 %s -b br0 -g %s` with constant arguments `-B -ddK` and `/var/run/wpa_supplicant-global`). No datagram byte reaches that command line, and its type-1 requirement cannot even pass the 7–26 dispatch gate, so via this socket the command is dead code. The applier's DPP sub-block is additionally gated in wps_pbcd itself: a present-credential check, then `wl_wlif_is_map_onboarding()`, then a backhaul-type check (three gates at `0x19b64`–`0x19b84`) before `wl_wlif_map_dpp_configure_backhaul_sta_interface`. The applier callbacks are installed into the context by the registration functions at `0x17248`/`0x17a8c` and are invoked from `libshared.so` MAP code, not from the datagram path. **Conclusion: the 58032 socket is a state/UI notification bus, not a command channel; no shell-injection path exists from it.**

**Per-site format resolution — pre-onboarding paths closed (2026-11-07, VERIFIED, corrects the format inventory above).** Resolving the format literal at every one of the 24 in-function `system()` sites (plus the one `system()`-tail helper at `0x15818`, which is the fixed command `nvram commit restart`): the sites run, in order of the function, `hostapd_cli -i %s set dpp_connector %s` (`0x19720`), `set dpp_netaccesskey %s` (`0x19b1c`), `reload`, `set wpa 2`, `set wpa_pairwise CCMP`, `set rsn_pairwise CCMP`, nine `set wpa_key_mgmt <fixed-set>` variants (`DPP`, `SAE`, `"DPP WPA-PSK-SHA256 SAE"`, `"SAE DPP"`, `"DPP WPA-PSK WPA-PSK WPA-PSK-SHA256 SAE"`, `"WPA-PSK-SHA256 SAE"`, `"WPA-PSK WPA-PSK-SHA256 SAE"`, `"WPA-PSK-SHA256"`, `"WPA-PSK WPA-PSK-SHA256"`), and the paired `set ieee80211w 1|2` sites. **Only `dpp_connector` and `dpp_netaccesskey` take a data argument**; the values are parsed from `wpa_ctrl` event strings (`DPP-CONNECTOR `, `DPP-NET-ACCESS-KEY ` prefixes) that hostapd emits from a completed DPP exchange, and that sub-block is behind the credential/onboarding/backhaul gates recorded above. The string inventory quoted above — `set dpp_csign %s`, `set ssid %s`, `set wpa_passphrase %s`, and the `Info: PBCD %s ssid %s psk %s ...` log — is present in `.rodata` but **referenced by no instruction, no pointer table, and no relocation** (full ldr/add-pair scan, raw pointer-value search, reloc scan, movw scan): these are **dead strings, not live call sites** (the pass text above attributed them to the 24 sites; they are not among them). The `csign` artifact is instead written by `libnv2hapdcfg.so`'s live `wpa_cli ... dpp_csign` line recorded further below, which requires the same onboarding-gated apply path. **Therefore no pre-onboarding shell-injection path exists in `wps_pbcd` at all: the non-DPP WPS credential path is dead code, and the only attacker-influenced shell lines remain the two DPP sites inside the onboarding-gated flow.** Live `/sbin/wps_pbcd` md5 matches the ROM copy (`5b251be35632527cc6c2ec7b9510fa31`).

Live nvram has `map_onboarded` set, `map_agent_configured` unset, the active backhaul type `unknown`, `wps_mode` enabled, and the open-backhaul flag unset. The origin of the credential strings was traced one step further: `libnv2hapdcfg.so` SHA-256 `f4b15d1c1bc938349c8c0a26f0373daf82b0e094cd4aa901c68cf7e63208bafa` imports `system` and `popen`, formats `wpa_cli -i %s -p %s set_network %lu dpp_connector '"%s"'` and the csign and netaccesskey variants, and stores the artifacts under nvram key patterns `%s_dpp_connector` and `%s_dpp_csign` plus `map_dpp_priv_key`. No live nvram key matching those patterns exists on this unit. The quoting in those formats is quotes only. The MAP state machine itself is in `libshared.so`, which also imports `system`, `execvp`, and `fork`. **Credential-provenance trace (2026-11-07):** the `%s_dpp_connector` and `%s_dpp_csign` nvram keys are written by `wpa_supp_map_apply_creds_to_supp` in `libnv2hapdcfg.so`, whose credential values arrive as function arguments from the apply path, with no character filtering between the DPP exchange and the shell lines — only the length caps already recorded. The shipped `wpa_supplicant` contains the full DPP agent-side path (`dpp_connector`, `dpp_netaccesskey`, the DPP event set), so the values can originate from a completed DPP exchange. **DERIVED:** if the unit is put into onboarding and completes DPP with a malicious configurator, configurator-supplied credential fields can reach the `system()` lines with quotes-only protection; upstream `wpa_supplicant` does not shell-filter protocol values because it never needed to. The exposure is gated entirely by the user-initiated onboarding window. What was not shown is that an unauthenticated peer controls any of these strings outside that window, and no session was started. No packet was sent.

## Airties container tier

The `lxc_ee` container (`lxc-start -n lxc_ee`) runs its own rootfs inside the host network namespace. The correct detector is a mount-namespace comparison; `readlink /proc/PID/root` returns `/` because of pivot_root, and a network-namespace check alone is not sufficient. Running inside it now: its init, `core-watchdog`, `core-lcm`, `systeminfo`, `odhcpc` on `eth0`, `mosquitto`, and `aircdf-daemon`. The container's init.d names `nginx` and `zend`, but no container listener appeared in the complete socket table, so the web tier is not up.

The ROM copy carries the whole `airties-edge` tree, and a dynsym sweep of all its binaries found shell imports in listeners that the earlier Airties pass did not cover: `air-domosd` (`system`, `fork`, `execlp`, plus `accept`/`bind`/`listen`), `domos-qosd` (`fork`, `execvp`, `system`, `popen`, plus the full net set, with both `0.0.0.0` and `127.0.0.1` bind strings), `multiap_controller` (`popen`, `system`, plus `accept`/`bind`/`listen`), and `airconnt` and `airpcapt` (`system`; netlink consumers). `air-dpi` imports `execlp`, `fork`, and `system` and starts DPI modules by name via `dpi-cli set -m %s -l %s`. `cloud-comm` has the full net set and no shell import.

None of these daemons is running now, so none listens; the live socket table remains authoritative. When the smart-wifi features start them they come up in the shared host namespace, directly on the LAN. Their bind addresses, ports, and `system` call sites were not traced. The one root SSH key in `dropbear` and `root` authorized_keys matches the project's own `f1-root-ed25519` pair, so there is no vendor key. No packet was sent.

**Call-site and listener trace (2026-11-07, VERIFIED — completes the untraced-daemon item).** Disassembly of the three named daemons from the ROM tree (live `domos-qosd` was already shown byte-identical except a build timestamp above; the others are the same ROM/LCM copies unless Telia ships new versions):

- **`air-domosd`**: both `socket()` calls are `socket(AF_UNIX, SOCK_STREAM, 0)` — the `cli_init` debug CLI ("[cli] accepting cli session") is a **unix-domain socket**, not a network listener. Its `system()` sites build `mkdir -p %s; mkdir -p %s; mkdir -p %s` chains from its own config paths (`g_domos_tmp_path`/`g_domos_dl_path`, set by `cfg_init`) and an indexed command table; `execlp` launches `domos-iotclient` after an `executable_in_path` check. No packet field reaches any command line; the only LAN exposure if it ever runs would be through the mqtt/cloud path it shares with `domos-qosd`.
- **`multiap_controller`**: the main CLI listener is AF_UNIX (`map_cli`), and there is one **`PF_PACKET` bind** (20-byte `sockaddr_ll`, `sll_family=AF_PACKET`, `sll_hatype=ARPHRD_ETHER`, `sll_protocol=htons(<config ethertype>)`) — the **IEEE 1905.1 raw-ethertype listener** on the LAN bridge; that raw 1905.1 frame parser, not a TCP/UDP port, is its real LAN surface when running. Its shell sites are the fixed `map_cli --command sendChScanReportPolicyConf --payload '{"args":"help"}'` string and `iw dev %s station get <mac> | grep %s`, with the interface and MAC taken from its own 1905 tables — LAN-attacker-influenced **only if** the daemon runs and the 1905 parser accepts the attacker's frames; the ebtables usage recorded in the `domos-qosd` trace above belongs to the same MAP code. A third small bind is a 12-byte AF_UNIX sockaddr (local only).
- **`air-dpi`**: no socket imports at all; its `execlp/fork/system` serve `dpi-cli set -m %s -l %s` with the module name and level from its own config (unchanged from the pass summary). Netlink consumers `airconnt`/`airpcapt` were already classified; nothing new reaches them.

Net result: of the whole untraced tier, **only `multiap_controller`'s PF_PACKET 1905.1 parser would be a LAN-facing pre-auth surface**, and only if Telia's `core-lcm` push re-enables the smart-wifi suite on this unit (the backend demonstrably pushes `airties_EWA1331` — see the [LCM deep audit](f1-lcm-package-channel-deep-audit-2026-11-07.md)); everything else is unix-socket or config-driven. No daemon was started for this trace. No packet was sent.

**domos-qosd call-site trace (2026-11-07):** its 19 `system` and 8 `popen` sites build `ipset add/list/flush` lines with set names, fixed `ip route show default ... | awk` and `iptables -S -t mangle | grep` pipelines, `tc` filter formats with hex arguments, a fixed `killall`, and one unquoted `echo %s | openssl enc -base64 -d | hexdump ... | awk ...` pipeline whose `%s` is a CUJO record field named in the adjacent log as `sakey`. The `mtr` and `fpingdq` diagnostics run with targets from the daemon's own config. The inputs to every traced site are the UCI config, the mqtt bus, ubus, and cloud records — none is a LAN packet field. The code contains an `AF_INET` socket setup that resolves `0.0.0.0`, but its port and role were not resolved and the daemon is not running. The shipped `domosqos` config carries an `rpcjson_url http://192.168.1.1/ubus` block with root credentials, but `/ubus` returns 404 on the host, so it is an inert reference default. The `domosqed` config embeds cloud SAS tokens; their values are not reproduced here. Which service the container's `core-lcm` lifecycle manager may enable remotely, and what verification the `cloud-comm` channel uses, remain the open leads in this tier.

**Container package channel (2026-11-07):** the container's `core-lcm` lifecycle manager (3.8 MB) installs, upgrades, and uninstalls packages from a remote backend. Its strings show token-authenticated downloads, a backend certificate file `tc_lcm_backend.crt`, a package-signature public key `tc_public.pem`, and a "Failed to verify package" failure path, so package verification is present. The channel is outbound; a LAN attacker's angle would be resolver poisoning, which the backend certificate file defeats unless the pin is bypassed. The URL and token are not in `/etc` and were not traced. Whether the TLS layer permits a downgrade, and whether the signature check can be bypassed, would need a deep review of the 3.8 MB binary and were not done. The `/genesis` overlay and its supervisor are this project's own prior-session tooling, not vendor software, so they are outside this inventory.

**Superseded 2026-11-07 (same day, later pass):** every open question in this paragraph was resolved by disassembly, live memory reads, and fetching real backend content. There is **no token** (the "token" string was nlohmann-json internals; the backend serves apps list and packages to an unauthenticated third-party curl), the channel is **plain `http://`** so the backend certificate is not used at all, and the URL **is** in `/etc/telia_app_config/tc_lcm` (overlay-provisioned `http://lcm.teliasmartrgw.com/`, `enabled '1'`). Signature coverage and fail-closed behavior are confirmed; residual exposure is an unsigned-apps-list downgrade vector. See [f1-lcm-package-channel-deep-audit-2026-11-07.md](f1-lcm-package-channel-deep-audit-2026-11-07.md).

**core-lcm crypto audit (2026-11-07, VERIFIED at string/cert level):** the binary links libcurl with OpenSSL. The backend certificate file is **Amazon Root CA 1** — a public trust anchor, not a vendor-specific pin — so the effective TLS policy is "any certificate chaining to Amazon's public root", which any AWS customer can obtain for domains they control. A man-in-the-middle therefore needs DNS-level control of the backend hostname first; on this unit the resolver path runs through the local dnsproxy's DoH hop, which raises that bar. The package check verifies against `tc_public.pem` with an explicit failure path; forging a package would need the vendor's private key, and whether any code path continues past a verification failure was not instruction-traced. No connection was made and no package was fetched.

**Superseded 2026-11-07 (same day, later pass):** the "links libcurl with OpenSSL" is true only as *static* linkage (subprojects/curl-8.0.1 + openssl-3.0.7 compiled in; dynamic deps are libuci/libstdc++/libpthread/libc only). The Amazon-root analysis is moot for the live channel: the configured `backend_url` is `http://`, so no TLS and no certificate are involved; interception needs only network position or DNS, and the only integrity control is the per-member RSA-2048 signature — which was now verified end-to-end against `tc_public.pem` and is fail-closed with no skip path. See [f1-lcm-package-channel-deep-audit-2026-11-07.md](f1-lcm-package-channel-deep-audit-2026-11-07.md).

## What was not shown

A memory-corruption bug, a SOAP field that reaches a shell, a live UPnP request, a DHCP hostname that is evaluated as shell code, a dropbear login that skips the shell allow-list, or an nginx request that chooses the `execve` path. hostapd was closed in an earlier pass. That an unauthenticated peer controls the MAP/DPP credential strings that the `wps_pbcd` and `libnv2hapdcfg` command lines use. No packet was sent.
