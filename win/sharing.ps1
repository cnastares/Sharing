# Configuration
$Port = 15200
$DiscoveryPort = 15201
$MagicPing = "SHARING_PING:"

# Load assemblies for Clipboard and Image handling
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$self = $PID
$Host.UI.RawUI.WindowTitle = "Sharing Client (PID:$self)"

Write-Host "Starting Sharing Client... Listening for UDP discovery pings on port $DiscoveryPort..."

$udpListener = New-Object System.Net.Sockets.UdpClient($DiscoveryPort)
$udpListener.Client.ReceiveTimeout = 2000

$stream = $client = $null
$serverIP = ""
$serverName = ""

function Find-Server {
    while ($script:serverIP -eq "") {
        try {
            $remoteEP = New-Object System.Net.IPEndPoint([System.Net.IPAddress]::Any, 0)
            $data = $udpListener.Receive([ref]$remoteEP)
            $msg = [System.Text.Encoding]::UTF8.GetString($data)
            if ($msg.StartsWith($MagicPing)) {
                $script:serverName = $msg.Substring($MagicPing.Length)
                $script:serverIP = $remoteEP.Address.ToString()
                Write-Host "Found peer: $serverName at $serverIP"
            }
        } catch {
            # timeout or network error, retry
        }
    }
}

function Connect-Server {
    Write-Host "Connecting to $serverName ($serverIP:$Port)..."
    $script:client = New-Object System.Net.Sockets.TcpClient($serverIP, $Port)
    $script:stream = $client.GetStream()
    Write-Host "Connected successfully! Monitoring clipboard & file transfers..."
}

function Cleanup {
    try { if ($stream) { $stream.Close(); $stream.Dispose() } } catch {}
    try { if ($client) { $client.Close(); $client.Dispose() } } catch {}
    $script:stream = $script:client = $null
    $script:serverIP = ""
}

# Find and connect
Find-Server
try { Connect-Server } catch { Write-Host "Connection failed: $_"; Cleanup; Exit }

# Helper to compute SHA256 hash of byte array
function Hash($b) { [Convert]::ToBase64String([Security.Cryptography.SHA256]::Create().ComputeHash($b)) }

$lastT = -1
$lastH = ""

# Setup exit handler
$stop = $false
$handler = {
    $script:stop = $true
    Write-Host "`nStopping..."
    Cleanup
    $udpListener.Close()
    exit
}
try { Register-EngineEvent PowerShell.Exiting -Action $handler | Out-Null } catch {}

# Monitor loops
while (-not $stop) {
    try {
        # 1. Read incoming TCP packets from Linux
        if ($client.Available -ge 5) {
            $hdr = New-Object byte[] 5
            $stream.Read($hdr, 0, 5) | Out-Null
            $t = $hdr[0]
            
            # Read 4-byte length
            $lenBytes = [byte[]]$hdr[1..4]
            if ([BitConverter]::IsLittleEndian) { [Array]::Reverse($lenBytes) }
            $len = [BitConverter]::ToUInt32($lenBytes, 0)
            
            if ($len -gt 0 -and $len -lt 100MB) {
                $buf = New-Object byte[] $len
                $r = 0
                while ($r -lt $len) {
                    $r += $stream.Read($buf, $r, $len - $r)
                }
                
                $lastT = $t
                $lastH = Hash $buf
                
                if ($t -eq 0) { # Text
                    try {
                        $text = [System.Text.Encoding]::UTF8.GetString($buf)
                        Write-Host "<<< Received Text: ($($buf.Length) bytes)"
                        [System.Windows.Forms.Clipboard]::SetText($text)
                    } catch { Write-Host "Error SetText: $_" }
                }
                elseif ($t -eq 1) { # Image
                    try {
                        Write-Host "<<< Received Image: ($($buf.Length) bytes)"
                        $ms = New-Object System.IO.MemoryStream(,$buf)
                        $img = [System.Drawing.Image]::FromStream($ms)
                        [System.Windows.Forms.Clipboard]::SetImage($img)
                        $img.Dispose()
                        $ms.Dispose()
                    } catch { Write-Host "Error SetImage: $_" }
                }
                elseif ($t -eq 2) { # File
                    try {
                        # Format: [name_len (2 bytes)][name][file_data]
                        $nameLenBytes = [byte[]]$buf[0..1]
                        if ([BitConverter]::IsLittleEndian) { [Array]::Reverse($nameLenBytes) }
                        $nameLen = [BitConverter]::ToUInt16($nameLenBytes, 0)
                        
                        $nameBytes = [byte[]]$buf[2..(2+$nameLen-1)]
                        $filename = [System.Text.Encoding]::UTF8.GetString($nameBytes)
                        
                        $fileBytes = [byte[]]$buf[(2+$nameLen)..($buf.Length-1)]
                        
                        $desktopPath = [System.Environment]::GetFolderPath("Desktop")
                        $filePath = Join-Path $desktopPath $filename
                        
                        [System.IO.File]::WriteAllBytes($filePath, $fileBytes)
                        Write-Host "<<< Received File: $filename saved to Desktop!"
                        
                        # Show balloon notification using Windows Forms
                        $balloon = New-Object System.Windows.Forms.NotifyIcon
                        $balloon.Icon = [System.Drawing.SystemIcons]::Information
                        $balloon.Visible = $true
                        $balloon.ShowBalloonTip(5000, "Sharing - Recibido", "Se ha recibido el archivo: $filename en tu Escritorio.", [System.Windows.Forms.ToolTipIcon]::Info)
                    } catch { Write-Host "Error saving file: $_" }
                }
            }
        }
        
        # 2. Check local Windows clipboard changes
        $lt = -1
        $lb = $null
        try {
            if ([System.Windows.Forms.Clipboard]::ContainsImage()) {
                $img = [System.Windows.Forms.Clipboard]::GetImage()
                if ($img -ne $null) {
                    $ms = New-Object System.IO.MemoryStream
                    $img.Save($ms, [System.Drawing.Imaging.ImageFormat]::Png)
                    $lb = $ms.ToArray()
                    $lt = 1
                    $ms.Dispose()
                    $img.Dispose()
                }
            }
            elseif ([System.Windows.Forms.Clipboard]::ContainsText()) {
                $tx = [System.Windows.Forms.Clipboard]::GetText()
                if ($tx -ne $null -and $tx -ne "") {
                    $lb = [System.Text.Encoding]::UTF8.GetBytes($tx)
                    $lt = 0
                }
            }
        } catch {
            # Ignore transient clipboard errors
        }
        
        if ($lt -ne -1 -and $lb -ne $null) {
            $h = Hash $lb
            if ($lt -ne $lastT -or $h -ne $lastH) {
                $lastT = $lt
                $lastH = $h
                
                $label = if ($lt -eq 1) { "image" } else { "text" }
                Write-Host ">>> Sending local $label ($($lb.Length) bytes)..."
                
                $lenB = [BitConverter]::GetBytes($lb.Length)
                if ([BitConverter]::IsLittleEndian) { [Array]::Reverse($lenB) }
                
                $stream.WriteByte($lt) | Out-Null
                $stream.Write($lenB, 0, 4) | Out-Null
                $stream.Write($lb, 0, $lb.Length) | Out-Null
            }
        }
        
    } catch [System.IO.IOException], [System.Net.Sockets.SocketException] {
        Write-Host "Connection lost. Reconnecting..."
        Cleanup
        Find-Server
        try { Connect-Server } catch { Start-Sleep -Seconds 2 }
    } catch {
        Write-Host "Error: $_"
        Start-Sleep -Milliseconds 500
    }
    
    Start-Sleep -Milliseconds 200
}

Cleanup
$udpListener.Close()
Write-Host "Finished."
Start-Sleep -Seconds 1
