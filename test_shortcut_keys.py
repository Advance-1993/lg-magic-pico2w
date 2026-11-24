"""Observe only selected Windows function-key transitions during a bounded hardware test.
Does not inject keys, bind actions, capture text, or change Windows settings.
"""
import argparse
import ctypes
import datetime as dt
from pathlib import Path
import time

parser=argparse.ArgumentParser()
parser.add_argument('--log',required=True)
parser.add_argument('--seconds',type=int,default=90)
parser.add_argument('--first',type=int,default=13)
parser.add_argument('--last',type=int,default=18)
args=parser.parse_args()
if not 1<=args.first<=args.last<=24: parser.error('Keys must be within F1..F24')
get_state=ctypes.windll.user32.GetAsyncKeyState
get_state.argtypes=[ctypes.c_int]
get_state.restype=ctypes.c_short
keys={number: False for number in range(args.first,args.last+1)}
deadline=time.monotonic()+args.seconds
with Path(args.log).open('a',encoding='utf-8',buffering=1) as log:
    def record(text):
        line=f'{dt.datetime.now(dt.timezone.utc).isoformat()} {text}'
        print(line,flush=True)
        log.write(line+'\n')
    record(f'START Windows hardware observation: only F{args.first}-F{args.last}, no input injection')
    while time.monotonic()<deadline:
        for number,previous in keys.items():
            pressed=bool(get_state(0x70+number-1)&0x8000)
            if pressed!=previous:
                record(f'F{number} {"DOWN" if pressed else "UP"}')
                keys[number]=pressed
        time.sleep(0.002)
    record('END')
