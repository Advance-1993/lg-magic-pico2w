$ErrorActionPreference = 'Stop'
$pythonExe = Join-Path $PSScriptRoot '.venv/Scripts/pythonw.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) { throw 'Follow docs/SETUP.md to create .venv and install requirements.txt first.' }
Start-Process -FilePath $pythonExe -ArgumentList ('"' + (Join-Path $PSScriptRoot 'companion.py') + '"') -WorkingDirectory $PSScriptRoot
