param([string]$Compiler='C:/msys64/mingw64/bin/gcc.exe')
$ErrorActionPreference='Stop'
$env:PATH="$(Split-Path $Compiler -Parent);$env:PATH"
$project=Split-Path $PSScriptRoot -Parent
$dest=Join-Path $env:TEMP 'lg-magic-power-policy-tests'
New-Item -ItemType Directory -Force -Path $dest | Out-Null
& $Compiler -std=c11 -Wall -Wextra -Werror "-I$project/firmware/src" "$PSScriptRoot/power_policy_test.c" -o "$dest/policy.exe"
if ($LASTEXITCODE) { throw 'Policy compile failed' }
& "$dest/policy.exe"
if ($LASTEXITCODE) { throw 'Policy tests failed' }
& $Compiler -std=c11 -Wall -Wextra -Werror -Wno-sign-compare -DLG_ENABLE_HID=1 "-I$PSScriptRoot/power_stubs" "-I$project/firmware/src" "$PSScriptRoot/power_activity_test.c" -lm -o "$dest/activity.exe"
if ($LASTEXITCODE) { throw 'Activity compile failed' }
& "$dest/activity.exe"
if ($LASTEXITCODE) { throw 'Activity tests failed' }
& $Compiler -std=c11 -Wall -Wextra -Werror "-I$PSScriptRoot/power_stubs" "-I$project/firmware/src" "$PSScriptRoot/host_usb_test.c" -o "$dest/usb.exe"
if ($LASTEXITCODE) { throw 'USB compile failed' }
& "$dest/usb.exe"
if ($LASTEXITCODE) { throw 'USB tests failed' }

& $Compiler -std=c11 -Wall -Wextra -Werror "-I$project/firmware/src" "$PSScriptRoot/power_settings_history_test.c" -o "$dest/settings-history.exe"
if ($LASTEXITCODE) { throw 'Settings/history compile failed' }
& "$dest/settings-history.exe"
if ($LASTEXITCODE) { throw 'Settings/history tests failed' }

& $Compiler -std=c11 -Wall -Wextra -Werror -Wno-sign-compare -DLG_ENABLE_HID=1 "-I$PSScriptRoot/reconnect_stubs" "-I$project/firmware/src" "$PSScriptRoot/hid_reconnect_test.c" -o "$dest/reconnect.exe"
if ($LASTEXITCODE) { throw 'Reconnect compile failed' }
& "$dest/reconnect.exe"
if ($LASTEXITCODE) { throw 'Reconnect tests failed' }

$python=Join-Path $project '../../work/tools/venv/Scripts/python.exe'
if (-not (Test-Path $python)) { $python='python' }
& $python "$PSScriptRoot/run_hid_snapshot_test.py"
if ($LASTEXITCODE) { throw 'HID snapshot tests failed' }

& $Compiler -std=c11 -Wall -Wextra -Werror -Wno-sign-compare -DLG_ENABLE_HID=1 "-I$PSScriptRoot/power_stubs" "-I$project/firmware/src" "$PSScriptRoot/mouse_drag_test.c" -lm -o "$dest/mouse-drag.exe"
if ($LASTEXITCODE) { throw 'Mouse drag compile failed' }
& "$dest/mouse-drag.exe"
if ($LASTEXITCODE) { throw 'Mouse drag tests failed' }
