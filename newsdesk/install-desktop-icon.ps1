# Run once: right-click > Run with PowerShell
$bat = Join-Path $PSScriptRoot "start.bat"
$desktop = [Environment]::GetFolderPath("Desktop")
$lnk = Join-Path $desktop "Somnia Forest NewsDesk.lnk"
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut($lnk)
$s.TargetPath = $bat
$s.WorkingDirectory = $PSScriptRoot
$s.IconLocation = "$env:SystemRoot\System32\shell32.dll,220"
$s.Description = "Somnia Forest NewsDesk"
$s.Save()
Write-Host "Desktop icon created: $lnk"
