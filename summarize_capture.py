"""Summarize raw capture without assuming an LG byte layout."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re

parser = argparse.ArgumentParser()
parser.add_argument('capture')
parser.add_argument('--output', required=True)
args = parser.parse_args()
pattern = re.compile(r'REPORT svc=(\d+) id=([0-9A-F]+) len=(\d+) offset=(\d+) data=([0-9A-F]+)')
groups = {}
for line in Path(args.capture).read_text(encoding='utf-8').splitlines():
    match = pattern.search(line)
    if not match:
        continue
    service, report_id, length, offset, hex_data = match.groups()
    data = bytes.fromhex(hex_data)
    if int(offset) != 0 or len(data) != int(length):
        continue  # This summary covers complete single-chunk reports only.
    key = (int(service), report_id, int(length))
    group = groups.setdefault(key, {'count': 0, 'bytes': [Counter() for _ in data], 'first': line, 'last': line})
    group['count'] += 1
    group['last'] = line
    for histogram, value in zip(group['bytes'], data):
        histogram[value] += 1
result = []
for (service, report_id, length), group in sorted(groups.items()):
    result.append({
        'service': service, 'report_id_hex': report_id, 'length': length,
        'count': group['count'], 'first': group['first'], 'last': group['last'],
        'byte_histograms': [{f'{value:02X}': count for value, count in sorted(histogram.items())} for histogram in group['bytes']],
        'note': 'Byte positions are observed data, not confirmed protocol fields or button mappings.'
    })
Path(args.output).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
for group in result:
    print(f"service={group['service']} id={group['report_id_hex']} length={group['length']} count={group['count']}")
