# Build and test

Tested toolchain: Pico SDK2.2.0 at a1438dff1d38bd9c65dbd693f0e5db4b9ae91779;
BTstack501e6d2b86e6c92bfb9c390bcf55709938e25ac1; Arm GNU14.2.Rel1;
Python3.13; CMake4.4.4; Ninja1.13.2; pyserial3.5. Native GCC/G++ needed for tests
and SDK host pioasm. Obtain toolchains from official upstreams, not this repository.

## Windows

Create a tools directory containing `pico-sdk/`, `arm/bin/arm-none-eabi-gcc.exe`
and `picotool/picotool/picotool.exe`. The official picotool archive has an inner
picotool directory. Install a native GCC/G++ (e.g. MSYS2 MinGW-w64) and add its bin
to PATH. In the repository:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
git clone --branch 2.2.0 --depth 1 https://github.com/raspberrypi/pico-sdk.git C:/PicoTools/pico-sdk
git -C C:/PicoTools/pico-sdk submodule update --init --depth 1 lib/btstack lib/cyw43-driver lib/lwip lib/mbedtls lib/tinyusb
.\build.ps1 -Hid -ToolsRoot C:/PicoTools -HostCompiler C:/msys64/mingw64/bin/g++.exe
.\build.ps1 -ToolsRoot C:/PicoTools -HostCompiler C:/msys64/mingw64/bin/g++.exe
```

The wrapper uses project `.venv`, separate `build/hid` / `build/diagnostic` caches,
and maps source/tool paths in compiled strings. Do not publish ELF files or caches.
Rebuild the manifest after either build: `.venv/Scripts/python.exe tools/release_manifest.py`.

## CMake directly / other hosts

Install Arm GCC, CMake, Ninja, Python and the pinned SDK/submodules. Set PICO_SDK_PATH.
Use separate directories and explicitly select the variant:

```sh
cmake -S firmware/src -B build/hid -G Ninja -DPICO_BOARD=pico2_w -DPICO_SDK_PATH="$PICO_SDK_PATH" -DLG_ENABLE_HID=ON
cmake --build build/hid --parallel
```

OFF produces CDC-only diagnostic. Before distributing such a build, supply your
own `-ffile-prefix-map` flags for source and SDK/tool paths to avoid leaking them.
Copy each resulting UF2 under the versioned name expected by `VERSION`, then
run `python tools/release_manifest.py`. Installer checks manifest SHA256, UF2 family,
and USB variant. Do not disable the pinned BTstack SHA256 check to update SDK.

## Tests (no connected hardware required)

```powershell
$env:PICO_SDK_PATH='C:/PicoTools/pico-sdk'
$env:CC='C:/msys64/mingw64/bin/gcc.exe'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe tools/run_native_tests.py
.\.venv\Scripts\python.exe tools/verify_artifacts.py
.\.venv\Scripts\python.exe tools/check_public.py
```

Linux: use `CC=gcc`, a Python/Tk installation and the same Python commands.
Firmware rebuilds need the Arm toolchain; native tests do not.
The workflow runs these checks on GitHub without flashing hardware. It does not
prove hardware compatibility. For releases also test the changed behavior on a
real board with a verified private backup. Never commit those backups/logs.

Official sources: https://github.com/raspberrypi/pico-sdk/tree/2.2.0,
https://github.com/raspberrypi/pico-sdk-tools/releases/tag/v2.2.0-2,
https://github.com/raspberrypi/picotool,
https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads.
