# Serve ONE small, deliberately non-firmware file over TFTP, once, then exit.
# Companion to f1-bootp-reply.ps1 -- run this in a SECOND elevated PowerShell
# window, alongside (not instead of) that script, both started before the
# router is rebooted into BOOT-P mode.
#
# Purpose: observe how the GCNT-X loader reacts to a file that actually
# EXISTS at the requested TFTP path but is not valid firmware -- the first
# step that touches any parsing/validation code, without ever risking a
# real or plausible image. See "Next" in findings/f1-bootp-lan-2026-10-13.md.
#
# DO NOT point this at a real firmware image. Keep -FileContent small,
# obviously inert text. This script only implements a single-DATA-block
# transfer (payload must fit in 512 bytes) -- deliberately minimal, not a
# general TFTP server.
#
# 2026-10-27 revision: replies from the SAME port (69) the RRQ arrived on,
# instead of RFC 1350's usual "reply from a new ephemeral port" (TID)
# convention. A live test on 2026-10-27 showed the RRQ reaching this
# listener correctly (11x, same source port), a block-1 DATA reply sent
# correctly each time (verified payload length), and zero ACKs ever
# received back -- consistent with either the router's bootloader not
# implementing TID tracking (expects replies from port 69), or Windows
# Firewall silently dropping inbound traffic to the new ephemeral port.
# Replying from port 69 sidesteps both possible causes at once. This
# revision has NOT yet been tested against the real device.

param(
    [string]$FileContent = "NOT-FIRMWARE-TEST`n",
    [int]$TimeoutSec = 90,
    [int]$ListenPort = 69
)

$ErrorActionPreference = "Stop"
$payload = [System.Text.Encoding]::ASCII.GetBytes($FileContent)
if ($payload.Length -gt 512) { throw "keep -FileContent <= 512 bytes; this server only sends one DATA block" }

Write-Output "serving $($payload.Length)-byte payload on first RRQ, udp/$ListenPort, timeout ${TimeoutSec}s"
Write-Output "payload: $FileContent"
Write-Output "replying from the SAME port ($ListenPort) the RRQ arrived on (non-RFC-1350 TID, see header comment)"

$listener = New-Object System.Net.Sockets.UdpClient($ListenPort)
$listener.Client.ReceiveTimeout = 1000
$deadline = (Get-Date).AddSeconds($TimeoutSec)
$served = $false

while ((Get-Date) -lt $deadline -and -not $served) {
    try {
        $remote = New-Object System.Net.IPEndPoint ([Net.IPAddress]::Any, 0)
        $buf = $listener.Receive([ref]$remote)
    } catch [System.Net.Sockets.SocketException] {
        continue
    }

    if ($buf.Length -lt 4 -or $buf[0] -ne 0 -or $buf[1] -ne 1) { continue }
    $nul1 = [Array]::IndexOf($buf, [byte]0, 2)
    $filename = if ($nul1 -gt 2) { [System.Text.Encoding]::ASCII.GetString($buf, 2, $nul1 - 2) } else { "<unparsed>" }
    Write-Output ("RRQ from {0}: file='{1}'" -f $remote, $filename)

    $data = New-Object byte[] (4 + $payload.Length)
    $data[0] = 0; $data[1] = 3
    $data[2] = 0; $data[3] = 1
    [Array]::Copy($payload, 0, $data, 4, $payload.Length)
    [void]$listener.Send($data, $data.Length, $remote)
    Write-Output "sent DATA block=1 bytes=$($payload.Length) from port $ListenPort"

    $listener.Client.ReceiveTimeout = 2000
    try {
        $ackRemote = New-Object System.Net.IPEndPoint ([Net.IPAddress]::Any, 0)
        $ack = $listener.Receive([ref]$ackRemote)
        if ($ack.Length -ge 4 -and $ack[0] -eq 0 -and $ack[1] -eq 4 -and $ack[2] -eq 0 -and $ack[3] -eq 1) {
            Write-Output "received ACK block=1 from $ackRemote -- transfer complete"
            $served = $true
        } else {
            $hex = ($ack | ForEach-Object { $_.ToString("x2") }) -join " "
            Write-Output "unexpected reply (not ACK block1): $hex"
        }
    } catch [System.Net.Sockets.SocketException] {
        Write-Output "no ACK received within timeout -- will retry on next RRQ if router sends one"
    }
    $listener.Client.ReceiveTimeout = 1000
}

$listener.Close()
if (-not $served) {
    Write-Output "no ACK ever received within ${TimeoutSec}s"
    exit 2
}
Write-Output "done"
