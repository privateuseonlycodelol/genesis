# Answer one Technicolor BOOT-P request. Does not serve a file.
# Run from an elevated PowerShell on the PC cabled to a router LAN port.
# Requires this adapter already set to 192.168.1.1/24.
# UART should change from "BOOTP Reply timeout" to a TFTP error. Stop there.

param(
    [Parameter(Mandatory = $true)]
    [string]$ClientMac,
    [string]$ServerIp = "192.168.1.1",
    [string]$OfferIp = "192.168.1.2",
    [string]$BootFile = "GCNT-X",
    [int]$TimeoutSec = 90
)

$ErrorActionPreference = "Stop"
$mac = ([byte[]]($ClientMac -split '[:-]' | ForEach-Object { [Convert]::ToByte($_, 16) }))
if ($mac.Length -ne 6) { throw "ClientMac must be 6 bytes" }

function IpBytes([string]$ip) {
    return ([byte[]]($ip.Split('.') | ForEach-Object { [byte]$_ }))
}

$server = IpBytes $ServerIp
$offer = IpBytes $OfferIp
$fileBytes = [System.Text.Encoding]::ASCII.GetBytes($BootFile)
if ($fileBytes.Length -gt 127) { throw "BootFile name too long" }

$udp = New-Object System.Net.Sockets.UdpClient
$udp.Client.SetSocketOption([Net.Sockets.SocketOptionLevel]::Socket, [Net.Sockets.SocketOptionName]::ReuseAddress, $true)
$udp.Client.Bind((New-Object System.Net.IPEndPoint ([Net.IPAddress]::Any, 67)))
$udp.EnableBroadcast = $true
$udp.Client.ReceiveTimeout = 1000
Write-Output "listening udp/67 for $TimeoutSec s; reply file name is $BootFile; no TFTP server"
$deadline = (Get-Date).AddSeconds($TimeoutSec)
$replied = 0

while ((Get-Date) -lt $deadline) {
    try {
        $remote = New-Object System.Net.IPEndPoint ([Net.IPAddress]::Any, 0)
        $buf = $udp.Receive([ref]$remote)
    } catch [System.Net.Sockets.SocketException] {
        continue
    }
    if ($buf.Length -lt 44 -or $buf[0] -ne 1 -or $buf[1] -ne 1 -or $buf[2] -ne 6) { continue }
    $got = $buf[28..33]
    $same = $true
    for ($i = 0; $i -lt 6; $i++) { if ($got[$i] -ne $mac[$i]) { $same = $false } }
    if (-not $same) { continue }

    $reply = New-Object byte[] 300
    $reply[0] = 2
    $reply[1] = 1
    $reply[2] = 6
    [Array]::Copy($buf, 4, $reply, 4, 4)
    $reply[10] = 0x80
    [Array]::Copy($offer, 0, $reply, 16, 4)
    [Array]::Copy($server, 0, $reply, 20, 4)
    [Array]::Copy($mac, 0, $reply, 28, 6)
    [Array]::Copy($fileBytes, 0, $reply, 108, $fileBytes.Length)
    $dest = New-Object System.Net.IPEndPoint ([Net.IPAddress]::Broadcast, 68)
    [void]$udp.Send($reply, $reply.Length, $dest)
    $replied++
    $xid = ($buf[4..7] | ForEach-Object { $_.ToString("x2") }) -join ""
    Write-Output ("replied xid={0} count={1}" -f $xid, $replied)
}

$udp.Close()
Write-Output "done replies=$replied"
if ($replied -eq 0) { exit 2 }
