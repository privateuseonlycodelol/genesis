# Combined BOOTP-reply + minimal single-block TFTP server, in one script,
# for running from a single Parsec/no-mouse-friendly PowerShell window.
# The port-69-reply revision (run 2026-10-27 ~01:46, transcript archived in
# artifacts/bootp/2026-10-27/) is the logic below minus the pktmon capture and
# Tailscale send in the start/finally blocks, which were added 2026-10-27
# after that run and have NOT been run yet. If this file and what actually ran
# on the Windows PC ever diverge, the Windows copy is ground truth for what was
# tested; update this file to match it, don't assume this file was what ran.
#
# Writes C:\bootp_tftp_result.log (transcript), C:\bootp_tftp_capture.etl and
# C:\bootp_tftp_capture.pcapng (packet capture of BOOTP/TFTP + the router IP),
# then sends the log and pcapng to the Mac over Tailscale (Taildrop).
#
# Companion/superset of scripts/f1-bootp-reply.ps1 (BOOTP only) and
# scripts/f1-tftp-serve-test.ps1 (TFTP only, same port-69 logic). Prefer
# running this single combined script when working one-handed via remote
# desktop; the two separate scripts exist for review/reuse.
#
# DO NOT point -FileContent at a real firmware image. See
# findings/f1-bootp-lan-2026-10-13.md "Next" / addenda for the gate on
# ever serving a real/signed RBI.

param(
    [string]$InterfaceAlias = "Ethernet",
    [string]$ClientMac = "00-1E-E3-76-83-61",
    [string]$ServerIp = "192.168.1.1",
    [string]$OfferIp = "192.168.1.2",
    [string]$BootFile = "GCNT-X",
    [string]$FileContent = "NOT-FIRMWARE-TEST`n",
    [int]$TimeoutSec = 180
)
$logFile = "C:\bootp_tftp_result.log"
$etlFile = "C:\bootp_tftp_capture.etl"
$pcapFile = "C:\bootp_tftp_capture.pcapng"
$tailscaleExe = "C:\Program Files\Tailscale\tailscale.exe"
$tailnetTarget = "macbook-pro-som-tillhr-nils:"
$capStarted = $false
Start-Transcript -Path $logFile -Append
Write-Host "=== STARTING COMBINED BOOTP+TFTP TEST (port-69-reply fix + pktmon capture) ===" -ForegroundColor Cyan
Write-Host "Adapter: $InterfaceAlias / Target MAC: $ClientMac / Timeout: $TimeoutSec s"
try {
    pktmon filter remove | Out-Null
    pktmon filter add -p 67 | Out-Null
    pktmon filter add -p 69 | Out-Null
    pktmon filter add -i $OfferIp | Out-Null
    pktmon start --capture --pkt-size 0 -f $etlFile | Out-Null
    if ($LASTEXITCODE -eq 0) { $capStarted = $true; Write-Host "pktmon capture started: $etlFile" -ForegroundColor Cyan }
    else { Write-Host "pktmon start failed (exit $LASTEXITCODE): no packet capture this run" -ForegroundColor Yellow }

    Write-Host "Switching $InterfaceAlias to static IP $ServerIp (Parsec will disconnect now)..." -ForegroundColor Yellow
    Remove-NetIPAddress -InterfaceAlias $InterfaceAlias -Confirm:$false -ErrorAction SilentlyContinue
    New-NetIPAddress -InterfaceAlias $InterfaceAlias -IPAddress $ServerIp -PrefixLength 24 -ErrorAction Stop

    $mac = ([byte[]]($ClientMac -split '[:-]' | ForEach-Object { [Convert]::ToByte($_, 16) }))
    function IpBytes([string]$ip) { return ([byte[]]($ip.Split('.') | ForEach-Object { [byte]$_ })) }
    $server = IpBytes $ServerIp
    $offer = IpBytes $OfferIp
    $fileBytes = [System.Text.Encoding]::ASCII.GetBytes($BootFile)
    $payload = [System.Text.Encoding]::ASCII.GetBytes($FileContent)
    if ($payload.Length -gt 512) { throw "FileContent too long for one TFTP block" }

    $bootpSock = New-Object System.Net.Sockets.UdpClient
    $bootpSock.Client.SetSocketOption([Net.Sockets.SocketOptionLevel]::Socket, [Net.Sockets.SocketOptionName]::ReuseAddress, $true)
    $bootpSock.Client.Bind((New-Object System.Net.IPEndPoint ([Net.IPAddress]::Any, 67)))
    $bootpSock.EnableBroadcast = $true
    $bootpSock.Client.ReceiveTimeout = 200

    $tftpSock = New-Object System.Net.Sockets.UdpClient(69)
    $tftpSock.Client.ReceiveTimeout = 200

    Write-Host "Listening BOOTP/udp67 and TFTP/udp69 for $TimeoutSec s (TFTP replies FROM port 69 this time)..." -ForegroundColor Green
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    $replied = 0
    $served = $false

    while ((Get-Date) -lt $deadline) {
        try {
            $remote = New-Object System.Net.IPEndPoint ([Net.IPAddress]::Any, 0)
            $buf = $bootpSock.Receive([ref]$remote)
            if ($buf.Length -ge 44 -and $buf[0] -eq 1 -and $buf[1] -eq 1 -and $buf[2] -eq 6) {
                $got = $buf[28..33]
                $same = $true
                for ($i = 0; $i -lt 6; $i++) { if ($got[$i] -ne $mac[$i]) { $same = $false } }
                if ($same) {
                    $reply = New-Object byte[] 300
                    $reply[0] = 2; $reply[1] = 1; $reply[2] = 6
                    [Array]::Copy($buf, 4, $reply, 4, 4)
                    $reply[10] = 0x80
                    [Array]::Copy($offer, 0, $reply, 16, 4)
                    [Array]::Copy($server, 0, $reply, 20, 4)
                    [Array]::Copy($mac, 0, $reply, 28, 6)
                    [Array]::Copy($fileBytes, 0, $reply, 108, $fileBytes.Length)
                    $dest = New-Object System.Net.IPEndPoint ([Net.IPAddress]::Broadcast, 68)
                    [void]$bootpSock.Send($reply, $reply.Length, $dest)
                    $replied++
                    $xid = ($buf[4..7] | ForEach-Object { $_.ToString("x2") }) -join ""
                    Write-Host "REPLIED to BOOTP! xid=$xid count=$replied" -ForegroundColor Green
                }
            }
        } catch [System.Net.Sockets.SocketException] { }

        try {
            $tremote = New-Object System.Net.IPEndPoint ([Net.IPAddress]::Any, 0)
            $tbuf = $tftpSock.Receive([ref]$tremote)
            if ($tbuf.Length -ge 4 -and $tbuf[0] -eq 0) {
                if ($tbuf[1] -eq 1) {
                    $nul1 = [Array]::IndexOf($tbuf, [byte]0, 2)
                    $filename = if ($nul1 -gt 2) { [System.Text.Encoding]::ASCII.GetString($tbuf, 2, $nul1 - 2) } else { "<unparsed>" }
                    Write-Host "RRQ from $tremote : file='$filename'" -ForegroundColor Cyan
                    $data = New-Object byte[] (4 + $payload.Length)
                    $data[0]=0; $data[1]=3; $data[2]=0; $data[3]=1
                    [Array]::Copy($payload, 0, $data, 4, $payload.Length)
                    [void]$tftpSock.Send($data, $data.Length, $tremote)
                    Write-Host "sent DATA block=1 bytes=$($payload.Length) FROM port 69" -ForegroundColor Green
                } elseif ($tbuf[1] -eq 4 -and $tbuf[2] -eq 0 -and $tbuf[3] -eq 1) {
                    Write-Host "received ACK block=1 from $tremote -- TRANSFER COMPLETE" -ForegroundColor Green
                    $served = $true
                } else {
                    $hex = ($tbuf | ForEach-Object { $_.ToString("x2") }) -join " "
                    Write-Host "unexpected TFTP packet from $tremote : $hex" -ForegroundColor Yellow
                }
            }
        } catch [System.Net.Sockets.SocketException] { }
    }

    $bootpSock.Close()
    $tftpSock.Close()
    Write-Host "DONE. BOOTP replies sent: $replied / TFTP ACK received: $served" -ForegroundColor Cyan
}
catch {
    Write-Host "ERROR: $_" -ForegroundColor Red
}
finally {
    if ($capStarted) {
        pktmon stop | Out-Null
        pktmon etl2pcap $etlFile --out $pcapFile | Out-Null
        Write-Host "packet capture saved: $pcapFile" -ForegroundColor Cyan
    }
    Write-Host "Restoring DHCP on $InterfaceAlias..." -ForegroundColor Yellow
    Remove-NetIPAddress -InterfaceAlias $InterfaceAlias -Confirm:$false -ErrorAction SilentlyContinue
    Remove-NetIPAddress -InterfaceAlias $InterfaceAlias -IPAddress $ServerIp -PolicyStore PersistentStore -Confirm:$false -ErrorAction SilentlyContinue
    Set-NetIPInterface -InterfaceAlias $InterfaceAlias -Dhcp Enabled -ErrorAction SilentlyContinue
    ipconfig /release $InterfaceAlias | Out-Null
    ipconfig /renew $InterfaceAlias | Out-Null
    $dhcpOk = $false
    for ($w = 0; $w -lt 30 -and -not $dhcpOk; $w++) {
        Start-Sleep -Seconds 1
        $dhcpOk = [bool](Get-NetIPAddress -InterfaceAlias $InterfaceAlias -AddressFamily IPv4 -PrefixOrigin Dhcp -ErrorAction SilentlyContinue)
    }
    $addrs = (Get-NetIPAddress -InterfaceAlias $InterfaceAlias -AddressFamily IPv4 -ErrorAction SilentlyContinue).IPAddress -join ", "
    $staticLeft = $addrs -split ", " -contains $ServerIp
    if ($dhcpOk -and -not $staticLeft) {
        Write-Host "DHCP lease restored on ${InterfaceAlias}: $addrs" -ForegroundColor Green
    } else {
        Write-Host "WARNING: no DHCP lease after 30 s. IPv4 now: '$addrs' (static $ServerIp still present: $staticLeft). Reboot or run ipconfig /renew by hand." -ForegroundColor Red
    }
    Stop-Transcript
    $send = @($logFile, $pcapFile) | Where-Object { Test-Path $_ }
    $ts = if (Test-Path $tailscaleExe) { $tailscaleExe } else { "tailscale" }
    Write-Host "Sending $($send.Count) file(s) to $tailnetTarget over Tailscale..." -ForegroundColor Cyan
    & $ts file cp @send $tailnetTarget
}
