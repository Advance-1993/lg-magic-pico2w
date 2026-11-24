"""Check current prebuilt UF2 family/USB variant identities without flashing."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct


def inspect(path, hid):
    raw = path.read_bytes()
    if len(raw) % 512:
        raise ValueError(f'{path.name}: incomplete UF2 block')
    flash = bytearray(b'\xff') * (4 * 1024 * 1024)
    families = Counter()
    for offset in range(0, len(raw), 512):
        block = raw[offset:offset+512]
        first, second, flags, address, size, number, total, family = struct.unpack('<8I', block[:32])
        if (first, second) != (0x0A324655, 0x9E5D5157) or struct.unpack('<I', block[-4:])[0] != 0x0AB16F30:
            raise ValueError(f'{path.name}: invalid UF2 magic')
        if size > 476 or not flags & 0x2000:
            raise ValueError(f'{path.name}: unexpected UF2 payload/family header')
        families[family] += 1
        if 0x10000000 <= address and address + size <= 0x10400000:
            flash[address-0x10000000:address-0x10000000+size] = block[32:32+size]
    # picotool adds an RP2350 absolute metadata block (family ...57) outside the
    # 4 MB application region. The actual ARM Secure program family is ...59.
    if 0xE48BFF59 not in families:
        raise ValueError(f'{path.name}: not an RP2350 ARM Secure program')
    pid = 0x4005 if hid else 0x4001
    device = bytes.fromhex('12010002EF020140FECA') + struct.pack('<H', pid) + bytes.fromhex('000101020301')
    configuration = bytes.fromhex('09026400030100807D' if hid else '09024B00020100807D')
    if device not in flash or configuration not in flash:
        raise ValueError(f'{path.name}: expected USB device/configuration descriptor not found')
    other = bytes.fromhex('12010002EF020140FECA') + struct.pack('<H', 0x4001 if hid else 0x4005) + bytes.fromhex('000101020301')
    if other in flash:
        raise ValueError(f'{path.name}: opposite variant descriptor is present')
    return {'file': path.name, 'sha256': hashlib.sha256(raw).hexdigest(),
            'pid': f'CAFE:{pid:04X}', 'interfaces': 3 if hid else 2,
            'uf2_families': {f'{key:08X}': count for key, count in families.items()}}


def main():
    root = Path(__file__).resolve().parents[1]
    version = (root/'VERSION').read_text().strip()
    result = [inspect(root/'uf2'/f'mr25ga-pico2w-airmouse-v{version}.uf2', True),
              inspect(root/'uf2'/f'lg-magic-pico2w-diagnostic-v{version}.uf2', False)]
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
