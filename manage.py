"""Interactive local setup/pairing for the Pico bridge; no vendor commands.
Requires pyserial 3.5. Run --help. Normal remote use does not need this program.
"""
import argparse
from collections import deque
import datetime as dt
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
import threading
import time

import serial
from serial.tools import list_ports

ADDRESS = re.compile(r'^[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}$')


def decode_advertisement(hex_data):
    """Bounds-checked BLE AD fields. Does not treat a name as model proof."""
    data = bytes.fromhex(hex_data)
    result = {}
    offset = 0
    while offset < len(data):
        size = data[offset]
        if not size or offset + 1 + size > len(data):
            break
        kind = data[offset + 1]
        value = data[offset + 2:offset + 1 + size]
        if kind in (8, 9):
            name = value.decode('utf-8', errors='replace')
            result['name'] = ''.join(c if 32 <= ord(c) < 127 else '?' for c in name)
        if kind == 255 and len(value) >= 2:
            result['manufacturer'] = int.from_bytes(value[:2], 'little')
        offset += size + 1
    return result


class Bridge:
    def __init__(self, port, log, raw=False, quiet=False, log_reports=True):
        self.port = port
        self.raw = raw
        self.quiet = quiet
        self.log_reports = log_reports
        self.log = Path(log).open('a', encoding='utf-8', buffering=1)
        try:
            self.serial = serial.Serial(port.device, 115200, timeout=0.15, write_timeout=2)
        except Exception:
            self.log.close(); raise
        self.condition = threading.Condition()
        self.history = deque(maxlen=6000)
        self.sequence = 0
        self.devices = {}
        self.last_advertisement = None
        self.error = None
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._read, daemon=True)
        self.thread.start()
        self.record('HOST', f'opened {port.device} serial={port.serial_number}')

    def record(self, kind, text):
        stamp = dt.datetime.now(dt.timezone.utc).isoformat()
        with self.condition:
            self.log.write(f'{stamp} {kind} {text}\n')

    def _read(self):
        pending = b''
        while not self.stop.is_set():
            try:
                pending += self.serial.read(max(1, self.serial.in_waiting))
                while b'\n' in pending:
                    raw, pending = pending.split(b'\n', 1)
                    line = raw.decode('ascii', errors='replace').rstrip('\r')
                    with self.condition:
                        self.sequence += 1
                        self.history.append((self.sequence, line))
                        match = re.search(r'ADV addr=([0-9A-F:]{17}) type=([01]) rssi=(-?\d+)', line)
                        if match:
                            key = (match[1], int(match[2]))
                            self.last_advertisement = key
                            self.devices.setdefault(key, {}).update(rssi=int(match[3]), seen=time.monotonic())
                        match = re.search(r'\bAD .*data=([0-9A-F]+)', line)
                        if match and self.last_advertisement:
                            self.devices[self.last_advertisement].update(decode_advertisement(match[1]))
                        self.condition.notify_all()
                    if self.log_reports or not re.search(r'\b(REPORT|ADV|AD) ', line):
                        self.record('DEVICE', line)
                    chatty = re.search(r'\b(REPORT|AD|ADV)\b|HEARTBEAT|Scan timeout|Scanning for', line)
                    if not self.quiet and (self.raw or not chatty):
                        print(line, flush=True)
                if len(pending) > 8192:
                    pending = b''
                    self.record('HOST', 'discarded overlong unterminated serial line')
            except (serial.SerialException, OSError, ValueError) as error:
                if not self.stop.is_set():
                    with self.condition:
                        self.error = str(error)
                        self.condition.notify_all()
                return

    def send(self, command):
        if '\n' in command or '\r' in command or len(command.encode('ascii')) > 95:
            raise ValueError('Send one ASCII command of at most 95 bytes')
        with self.condition:
            mark = self.sequence
        self.record('SEND', command)
        self.serial.write((command + '\n').encode('ascii'))
        return mark

    def wait(self, pattern, after, timeout=8):
        deadline = time.monotonic() + timeout
        regex = re.compile(pattern)
        with self.condition:
            while True:
                for sequence, line in self.history:
                    if sequence > after and regex.search(line):
                        return line
                if self.error:
                    raise RuntimeError(f'USB serial disconnected: {self.error}')
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(f'No response matching {pattern!r}; see log')
                self.condition.wait(min(remaining, 0.3))

    def scan_ready(self):
        self.send('scan')
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            mark = self.send('status')
            line = self.wait(r'\bSTATUS state=', mark, timeout=3)
            if 'state=1 ' in line:
                return
            time.sleep(0.3)
        raise TimeoutError('Bluetooth did not reach scan state')

    def show_devices(self):
        with self.condition:
            devices = [(key, dict(value)) for key, value in self.devices.items()]
        devices.sort(key=lambda item: (not (item[1].get('manufacturer') == 0xC4 or 'LGE MR' in item[1].get('name', '')), -item[1]['seen']))
        print('\nObserved addresses (names are hints; verify the physical model):')
        for number, ((address, kind), info) in enumerate(devices, 1):
            age = time.monotonic() - info['seen']
            manufacturer = info.get('manufacturer')
            label = 'LG manufacturer' if manufacturer == 0xC4 else ''
            print(f"{number:2}: {address} type={kind} RSSI={info['rssi']} age={age:.1f}s {info.get('name', '')} {label}")
        return devices

    def close(self):
        self.stop.set()
        self.thread.join(timeout=2)
        self.serial.close()
        self.record('HOST', 'closed; serial port released')
        self.log.close()


def choose_port(requested):
    deadline = time.monotonic() + 8
    while True:
        ports = [p for p in list_ports.comports() if p.vid == 0xCAFE and p.pid in (0x4001, 0x4005)]
        if requested:
            ports = [p for p in ports if p.device.lower() == requested.lower()]
        if ports or time.monotonic() >= deadline:
            break
        time.sleep(0.25)  # USB may still be enumerating after a firmware reboot.
    if len(ports) != 1:
        raise RuntimeError('Expected exactly one matching Pico bridge. Use ports, then --port COMx. Close other serial loggers.')
    return ports[0]


def pairing_result(bridge, mark, subscribe_timeout=90, report_timeout=20):
    bridge.wait('HID_SUBSCRIBED', mark, timeout=subscribe_timeout)
    line = bridge.wait(r'\bREPORT ', mark, timeout=report_timeout)
    print('\nHID subscription AND an input report observed. Save this log.')
    if not re.search(r'id=FD len=20\b', line):
        print('Report layout differs from the tested FD/20-byte layout. Do not assume the translator is compatible.')
    print('Now test individual buttons/releases, then calibrate while still. See docs/SETUP.md.')
    return line


def pair(bridge):
    if bridge.port.pid == 0x4005:
        print('This HID image translates the tested MR25GA protocol only.')
        if input('Check the physical label. Type MR25GA, or anything else to stop: ').strip().upper() != 'MR25GA':
            print('For a different/unknown model, flash the CDC-only diagnostic first. Pairing is not decoder compatibility.')
            return
    print('Keep the TV fully unplugged. Confirm access to the original TV and its recovery procedure.')
    print('For our tested LG remote: Back+Home for five seconds unregisters; powered-on original TV + pointed Wheel/OK restores it.')
    if input('Type READY when recovery is understood and the TV is unplugged: ').strip().upper() != 'READY':
        return
    bridge.scan_ready()  # retains old keys until the explicit replacement step below.
    print('Unregister the remote ONCE as its manual requires; for this MR25GA hold Back+Home five seconds.')
    print('Press Wheel/OK near the Pico. Advertisements are being logged in the background.')
    input('Press Enter after those physical actions: ')
    time.sleep(1)
    while True:
        devices = bridge.show_devices()
        choice = input('Choose a number, MAC and type (AA:BB:CC:DD:EE:FF 0), or R to refresh: ').strip()
        if choice.upper() != 'R':
            break
        input('Press only Wheel/OK again near the Pico, then Enter to refresh: ')
        time.sleep(1)
    if choice.isdecimal() and 1 <= int(choice) <= len(devices):
        (address, kind), _ = devices[int(choice) - 1]
    else:
        parts = choice.split()
        if len(parts) != 2 or not ADDRESS.fullmatch(parts[0]) or parts[1] not in ('0', '1'):
            raise ValueError('Invalid address/type; nothing selected')
        address, kind = parts[0].upper(), int(parts[1])
    print(f'Selected {address}, type {kind}. This replaces the Pico\'s single saved peer, not the remote firmware.')
    if input('Type PAIR to replace the Pico peer and continue: ').strip().upper() != 'PAIR':
        print('Cancelled. Use resume to restore automatic reconnection to the old saved peer.')
        return
    mark = bridge.send('forget')
    bridge.wait('FORGOT local bond', mark)
    mark = bridge.send(f'forget {address} {kind}')
    bridge.wait('FORGOT explicit local address', mark)
    for attempt in range(1, 4):
        bridge.scan_ready()
        mark = bridge.send(f'pair {address} {kind}')
        bridge.wait('PAIR armed', mark)
        print(f'Attempt {attempt}: press ONLY Wheel/OK once near the Pico. Do not repeat Back+Home.')
        try:
            pairing_result(bridge, mark)
            return
        except TimeoutError as error:
            print(error)
            # The user may press OK just as the deadline expires. Check again
            # before prompting and after their answer, without restarting a good link.
            try:
                pairing_result(bridge, mark, subscribe_timeout=2, report_timeout=2)
                return
            except TimeoutError:
                pass
            retry = attempt < 3 and input('Retry with an ordinary Wheel/OK wake-up? Type YES: ').strip().upper() == 'YES'
            try:
                pairing_result(bridge, mark, subscribe_timeout=0.05, report_timeout=0.05)
                return
            except TimeoutError:
                pass
            if not retry:
                print('Stopped without proof of usable input. See the raw log and troubleshooting guide.')
                return


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', help='Explicit matching bridge COM port if more than one is present')
    parser.add_argument('--log', type=Path)
    parser.add_argument('--raw', action='store_true', help='Print every raw report as well as logging it')
    sub = parser.add_subparsers(dest='action', required=True)
    for action in ('ports', 'status', 'pair', 'console', 'calibrate'):
        sub.add_parser(action)
    gain = sub.add_parser('gain'); gain.add_argument('value')
    send = sub.add_parser('send'); send.add_argument('command')
    args = parser.parse_args()
    if args.action == 'ports':
        for p in list_ports.comports():
            if p.vid == 0xCAFE and p.pid in (0x4001, 0x4005):
                print(f'{p.device} PID={p.pid:04X} serial={p.serial_number} {p.description}')
        return
    log = args.log or Path(__file__).parent/'logs'/f'manage-{dt.datetime.now(dt.timezone.utc):%Y%m%d-%H%M%S}.txt'
    log.parent.mkdir(parents=True, exist_ok=True)
    print(f'Raw log: {log}')
    bridge = Bridge(choose_port(args.port), log, args.raw)
    try:
        mark = bridge.send('help')
        help_line = bridge.wait(r'LG BRIDGE .*HID=', mark)
        mark = bridge.send('status'); bridge.wait('STATUS state=', mark)
        if args.action == 'pair':
            pair(bridge)
        elif args.action == 'status':
            if 'HID=1' in help_line:
                mark = bridge.send('mouse status'); bridge.wait('GYRO mode=', mark)
        elif args.action == 'gain':
            try:
                value = Decimal(args.value)
                if not value.is_finite() or not 1 <= value <= 100 or value != value.quantize(Decimal('0.001')):
                    raise ValueError('Gain must be 1..100, with at most three decimal places')
            except InvalidOperation as error:
                raise ValueError('Invalid decimal gain') from error
            mark = bridge.send(f'mouse gain {value:.3f}')
            line = bridge.wait('GYRO config store|COMMAND rejected|gain rejected', mark)
            if 'rc=0 readback=1' not in line:
                raise RuntimeError('Gain store was not verified')
            mark = bridge.send('mouse status'); bridge.wait('GYRO mode=', mark)
        elif args.action == 'calibrate':
            if 'HID=1' not in help_line:
                raise ValueError('Calibration needs the HID/air-mouse firmware, not the CDC-only image')
            print('Place the remote flat and leave it untouched until PASS/REJECTED, about five seconds.')
            if input('Type READY when it is still: ').strip().upper() == 'READY':
                mark = bridge.send('calibrate')
                bridge.wait('GYRO calibration PASS|GYRO calibration REJECTED', mark, timeout=15)
        elif args.action == 'send':
            bridge.send(args.command); time.sleep(1)
        elif args.action == 'console':
            print('Commands go to the Pico. Local commands: devices, quit. Send help for firmware commands; see docs/CONTROLS.md.')
            while True:
                command = input('pico> ').strip()
                if command in ('quit', 'exit'): break
                if command == 'devices': bridge.show_devices()
                elif command: bridge.send(command)
    finally:
        bridge.close()


if __name__ == '__main__':
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print('\nClosed.')
    except (ValueError, RuntimeError, TimeoutError, serial.SerialException) as error:
        raise SystemExit(f'Error: {error}')
