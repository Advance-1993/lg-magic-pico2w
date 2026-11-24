param([switch]$Hid, [Parameter(Mandatory=$true)][string]$ToolsRoot, [string]$HostCompiler, [string]$BuildRoot, [string]$PythonExe)
$ErrorActionPreference='Stop'
$projectRoot=$PSScriptRoot
$releaseVersion=(Get-Content (Join-Path $projectRoot 'VERSION') -Raw).Trim()
if ($releaseVersion -notmatch '^\d+\.\d+(\.\d+)?$') {throw 'Invalid VERSION'}
$toolsPath=(Resolve-Path -LiteralPath $ToolsRoot).Path
if (-not $PythonExe) {$PythonExe=Join-Path $projectRoot '.venv/Scripts/python.exe'}
if (-not (Test-Path -LiteralPath $pythonExe)) {throw 'Create .venv and install requirements-dev.txt; see docs/DEVELOPMENT.md'}
$variant=if ($Hid) {'hid'} else {'diagnostic'}
if (-not $BuildRoot) {$BuildRoot=Join-Path $projectRoot "build/$variant"}
$option=if ($Hid) {'ON'} else {'OFF'}
if (-not $HostCompiler) {$HostCompiler=(Get-Command g++.exe -ErrorAction SilentlyContinue).Source}
if (-not $HostCompiler) {throw 'Provide native host g++.exe with -HostCompiler'}
$env:PATH="$(Split-Path $pythonExe -Parent);$toolsPath/arm/bin;$(Split-Path $HostCompiler -Parent);$env:PATH"
$env:CXX=$HostCompiler
# Compile-time file/debug prefix mapping removes local usernames/tool paths.
$sourceMap=$projectRoot.Replace('\','/')
$toolMap=$toolsPath.Replace('\','/')
$maps="`"-ffile-prefix-map=$sourceMap=/src/lg-magic-pico2w`" `"-fdebug-prefix-map=$sourceMap=/src/lg-magic-pico2w`" `"-ffile-prefix-map=$toolMap=/opt/pico-tools`" `"-fdebug-prefix-map=$toolMap=/opt/pico-tools`""
& $pythonExe -m cmake -S "$projectRoot/firmware/src" -B $BuildRoot -G Ninja `
  -DPICO_BOARD=pico2_w "-DPICO_SDK_PATH=$toolsPath/pico-sdk" "-DPICO_TOOLCHAIN_PATH=$toolsPath/arm" `
  "-Dpicotool_DIR=$toolsPath/picotool/picotool" "-DPython3_EXECUTABLE=$pythonExe" `
  -DCMAKE_BUILD_TYPE=Debug "-DLG_ENABLE_HID=$option" "-DLG_BUILD_PATH_FLAGS=$maps"
if ($LASTEXITCODE) {throw 'Configure failed'}
& $pythonExe -m cmake --build $BuildRoot --parallel 8
if ($LASTEXITCODE) {throw 'Build failed'}
$name=if ($Hid) {"mr25ga-pico2w-airmouse-v$releaseVersion"} else {"lg-magic-pico2w-diagnostic-v$releaseVersion"}
New-Item -ItemType Directory -Force -Path "$projectRoot/uf2" | Out-Null
Copy-Item -LiteralPath "$BuildRoot/picow_ble_usb_hid_bridge.uf2" -Destination "$projectRoot/uf2/$name.uf2"
Get-FileHash "$projectRoot/uf2/$name.uf2"
