$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$args = @(
  '--clean',
  '--noconfirm',
  '--onefile',
  '--console',
  '--name', 'gaming-audit',
  '--paths', 'src',
  'packaging/windows_entry.py'
)

python -m PyInstaller @args
