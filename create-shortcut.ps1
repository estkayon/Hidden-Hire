# Creates a "Hidden Hire" shortcut on the desktop that starts the app with its own icon.
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$desktop = [Environment]::GetFolderPath('Desktop')
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut((Join-Path $desktop 'Hidden Hire.lnk'))
$shortcut.TargetPath = Join-Path $root 'start.bat'
$shortcut.WorkingDirectory = $root
$shortcut.IconLocation = (Join-Path $root 'assets\hidden-hire.ico') + ',0'
$shortcut.WindowStyle = 7
$shortcut.Description = 'Start Hidden Hire'
$shortcut.Save()
Write-Host "Shortcut created on the desktop."