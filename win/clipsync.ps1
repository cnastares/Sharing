# ClipSync
$ServerIP = "192.168.1.36"
$Port = 15200
$self = $PID
$Host.UI.RawUI.WindowTitle = "ClipSync (PID:$self)"

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

function Hash($b) { [Convert]::ToBase64String([Security.Cryptography.SHA256]::Create().ComputeHash($b)) }

$stream = $client = $null
function Connect {
    $script:client = New-Object System.Net.Sockets.TcpClient($ServerIP, $Port)
    $script:stream = $client.GetStream()
}

function Cleanup {
    try { if ($stream) { $stream.Close(); $stream.Dispose() } } catch {}
    try { if ($client) { $client.Close(); $client.Dispose() } } catch {}
    $script:stream = $script:client = $null
}

try { Connect } catch { Write-Host "No conecta: $_"; Start-Sleep -s 3; exit 1 }

$lastT = -1; $lastH = ""

$stop = $false
$handler = {
    $script:stop = $true
    Write-Host "`nDeteniendo..."
    Cleanup
    exit
}
try { Register-EngineEvent PowerShell.Exiting -Action $handler | Out-Null } catch {}

Write-Host "Conectado. Ctrl+C para salir."

while (-not $stop) {
    try {
        # 1) Si hay datos del servidor Linux
        if ($client.Available -ge 5) {
            $hdr = New-Object byte[] 5; $stream.Read($hdr,0,5) | Out-Null
            $t = $hdr[0]
            $lenBytes = [byte[]]$hdr[1..4]
            if ([BitConverter]::IsLittleEndian) { [Array]::Reverse($lenBytes) }
            $len = [BitConverter]::ToUInt32($lenBytes,0)
            Write-Host "<<< Recibido tipo=$t len=$len bytes=[$(($hdr[1..4] | ForEach-Object { '0x{0:X2}' -f $_ }) -join ',')]"
            if ($len -gt 0 -and $len -lt 100MB) {
                $buf = New-Object byte[] $len; $r = 0; while ($r -lt $len) { $r += $stream.Read($buf,$r,$len-$r) }
                $lastT = $t; $lastH = Hash $buf
                Write-Host "<<< Payload recibido: $r bytes"
                if ($t -eq 0) {
                    try {
                        $text = [Text.Encoding]::UTF8.GetString($buf)
                        [Windows.Forms.Clipboard]::SetText($text)
                    } catch { Write-Host "Error SetText: $_" }
                } elseif ($t -eq 1) {
                    try {
                        $ms = New-Object IO.MemoryStream(,$buf)
                        $img = [Drawing.Image]::FromStream($ms)
                        [Windows.Forms.Clipboard]::SetImage($img)
                        $img.Dispose(); $ms.Dispose()
                    } catch { Write-Host "Error SetImage: $_" }
                }
            }
        }

        # 2) Clipboard local
        $lt = -1; $lb = $null
        try {
            if ([Windows.Forms.Clipboard]::ContainsImage()) {
                $img = [Windows.Forms.Clipboard]::GetImage()
                if ($img) {
                    $ms = New-Object IO.MemoryStream
                    $img.Save($ms,[Drawing.Imaging.ImageFormat]::Png)
                    $lb = $ms.ToArray(); $lt = 1
                    $ms.Dispose(); $img.Dispose()
                }
            } elseif ([Windows.Forms.Clipboard]::ContainsText()) {
                $tx = [Windows.Forms.Clipboard]::GetText()
                if ($tx) { $lb = [Text.Encoding]::UTF8.GetBytes($tx); $lt = 0 }
            }
        } catch { Write-Host "Error clipboard: $_" }

        if ($lt -ne -1 -and $lb) {
            $h = Hash $lb
            if ($lt -ne $lastT -or $h -ne $lastH) {
                $lastT = $lt; $lastH = $h
                $lenB = [BitConverter]::GetBytes($lb.Length); if ([BitConverter]::IsLittleEndian) { [Array]::Reverse($lenB) }
                $stream.WriteByte($lt) | Out-Null
                $stream.Write($lenB,0,4) | Out-Null
                $stream.Write($lb,0,$lb.Length) | Out-Null
            }
        }
    } catch [Net.Sockets.SocketException] {
        Write-Host "Conexion perdida. Reconectando..."
        Cleanup; Start-Sleep -s 2; try { Connect } catch { Start-Sleep -s 2 }
    } catch {
        Write-Host "Error: $_"
        Start-Sleep -Milliseconds 500
    }
    Start-Sleep -Milliseconds 200
}

Cleanup
Write-Host "Finalizado."
Start-Sleep -Seconds 1
