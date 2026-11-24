"""Validated persistent Pico inactivity settings; independent of saved controls."""
from dataclasses import dataclass
import re
LEGACY_TIMEOUT_SECONDS=(30,60,90,180,*range(240,781,60))
LONG_TIMEOUT_SECONDS=(1800,2700,3600,7200,14400,21600,43200)
TIMEOUT_SECONDS=LEGACY_TIMEOUT_SECONDS+LONG_TIMEOUT_SECONDS
def timeout_label(seconds):
    if seconds>=3600 and seconds%3600==0:
        hours=seconds//3600
        return f'{hours} hour'+('s' if hours!=1 else '')
    minutes,seconds=divmod(seconds,60)
    if not minutes: return f'{seconds} seconds'
    if not seconds: return f'{minutes} minute'+('s' if minutes!=1 else '')
    return f'{minutes} min {seconds:02d} sec'
TIMEOUT_CHOICES={timeout_label(value):value for value in TIMEOUT_SECONDS}
def timeout_choices_for_version(version):
    try: modern=tuple(map(int,version.split('.')[:2]))>=(0,23)
    except (ValueError,AttributeError): modern=False
    return {timeout_label(value):value for value in (TIMEOUT_SECONDS if modern else LEGACY_TIMEOUT_SECONDS)}

@dataclass(frozen=True)
class TimeoutSetting:
    seconds:int
    source:str

def parse_timeout(line):
    match=re.search(r'\bTIMEOUT seconds=(\d+) source=(flash|default) supported=([01])\b',line)
    if not match or match[3]!='1': return None
    seconds=int(match[1])
    if seconds not in TIMEOUT_SECONDS: raise ValueError('Unsupported timeout returned by Pico')
    return TimeoutSetting(seconds,match[2])

def read_timeout(bridge):
    mark=bridge.send('power timeout')
    return parse_timeout(bridge.wait(r'\bTIMEOUT seconds=',mark,timeout=4))

def save_timeout(bridge,seconds):
    if type(seconds) is not int or seconds not in TIMEOUT_SECONDS: raise ValueError('Choose a supported inactivity timeout')
    mark=bridge.send(f'power timeout {seconds}')
    line=bridge.wait(r'\bTIMEOUT_STORE |\bTIMEOUT_REJECT ',mark,timeout=8)
    if not re.search(r'TIMEOUT_STORE rc=0 readback=1 applied=1 seconds='+str(seconds)+r'\b',line):
        raise RuntimeError('Timeout was not verified/applied: '+line)
    setting=read_timeout(bridge)
    if setting!=TimeoutSetting(seconds,'flash'): raise RuntimeError('Timeout flash readback differs from requested value')
    return setting
