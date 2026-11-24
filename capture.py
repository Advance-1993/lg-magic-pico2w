"""Capture the CDC-only diagnostic. Commands are read from a local JSONL queue.
Run with local venv Python; --commands points to an append-only file containing
JSON objects with a command string. New sessions consume that file from its end.
No firmware, pairing, or other commands are sent automatically except help/status.
"""
import argparse
import datetime as dt
import json
from pathlib import Path
import time
import serial
from serial.tools import list_ports

parser = argparse.ArgumentParser()
parser.add_argument('--log', required=True)
parser.add_argument('--commands', required=True)
parser.add_argument('--seconds', type=int, default=1800)
args = parser.parse_args()
commands = Path(args.commands)
commands.touch(exist_ok=True)
position = commands.stat().st_size
deadline = time.monotonic() + args.seconds
connection = None
with Path(args.log).open('a', encoding='utf-8', buffering=1) as log:
    def record(kind, text):
        stamp = dt.datetime.now(dt.timezone.utc).isoformat()
        line = f'{stamp} {kind} {text}'
        log.write(line + '\n')
        print(line, flush=True)
    while time.monotonic() < deadline:
        if connection is None:
            ports = [p for p in list_ports.comports() if p.vid == 0xCAFE and p.pid in (0x4001, 0x4005)]
            if len(ports) != 1:
                time.sleep(0.5)
                continue
            try:
                connection = serial.Serial(ports[0].device, 115200, timeout=0.2, write_timeout=1)
                record('HOST', f'opened {ports[0].device} serial={ports[0].serial_number}')
                connection.write(b'help\nstatus\n')
            except serial.SerialException as error:
                connection = None
                record('HOST_ERROR', str(error))
                time.sleep(0.5)
                continue
        try:
            line = connection.readline()
            if line:
                record('DEVICE', line.decode('ascii', errors='replace').rstrip())
            with commands.open(encoding='utf-8') as queue:
                queue.seek(position)
                for line in queue:
                    item = json.loads(line)
                    command = item.get('command')
                    if command:
                        record('SEND', command)
                        connection.write((command + '\n').encode('ascii'))
                    if item.get('label'):
                        record('LABEL', item['label'])
                position = queue.tell()
        except (serial.SerialException, OSError) as error:
            record('HOST_ERROR', str(error))
            connection.close()
            connection = None
    if connection:
        connection.close()
    record('HOST', 'capture ended')
