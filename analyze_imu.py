"""Analyze timestamp-bounded raw sensor samples; no remote commands are sent."""
import argparse
import datetime as dt
import json
from pathlib import Path
import re
import statistics
import struct

parser=argparse.ArgumentParser()
parser.add_argument('capture')
parser.add_argument('--after', required=True)
parser.add_argument('--before')
parser.add_argument('--output', required=True)
args=parser.parse_args()
after=dt.datetime.fromisoformat(args.after)
before=dt.datetime.fromisoformat(args.before) if args.before else dt.datetime.max.replace(tzinfo=dt.timezone.utc)
samples=[]
pattern=re.compile(r'REPORT svc=0 id=FD len=20 offset=0 data=([0-9A-F]{40})')
for line in Path(args.capture).read_text(encoding='utf-8').splitlines():
    match=pattern.search(line)
    if not match: continue
    stamp=dt.datetime.fromisoformat(line.split()[0])
    if after <= stamp <= before:
        raw=bytes.fromhex(match.group(1))
        samples.append((stamp, struct.unpack('>hhh', raw[5:11]), struct.unpack('>hhh', raw[11:17])))
if not samples: raise SystemExit('No matching samples')
result={'samples':len(samples),'first':samples[0][0].isoformat(),'last':samples[-1][0].isoformat()}
for name,index in [('gyro',1),('accel',2)]:
    result[name]=[]
    for axis in range(3):
        values=[row[index][axis] for row in samples]
        result[name].append({'mean':statistics.mean(values),'stddev':statistics.pstdev(values),'min':min(values),'max':max(values),'sum':sum(values)})
Path(args.output).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,indent=2))
