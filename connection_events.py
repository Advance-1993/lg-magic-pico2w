"""Strict controller-event decoding and bounded, deduplicated connection timeline."""
from collections import OrderedDict
from dataclasses import dataclass
import re
EVENT_NAMES={
 'boot':'Pico started','usb_available':'USB host available','usb_unavailable':'USB host unavailable — pause',
 'idle_timeout':'Inactivity timeout — pause','peer_wake':'Remote wake signal','resume':'Connection resumed',
 'manual_pause':'Connections paused manually','connecting':'Connecting','connected':'Bluetooth connected',
 'secured':'Connection secured','input_ready':'HID input setup complete','first_report':'First remote report',
 'disconnected':'Bluetooth disconnected','security_retry':'Temporary security error — retry',
 'security_pause':'Security error — paused','connect_failed':'Connection failed','hid_failed':'HID setup failed',
 'timeout_saved':'Inactivity setting saved','pair_armed':'New remote pairing armed'}
REASONS={0x05:'authentication failure',0x06:'key missing',0x08:'connection timeout / signal lost',
 0x13:'remote closed connection',0x14:'remote resources exhausted',0x15:'remote powered off',
 0x16:'Pico closed connection',0x22:'link response timeout'}
@dataclass(frozen=True)
class ConnectionEvent:
    boot:str
    sequence:int
    uptime_ms:int
    event:str
    detail:int
    @property
    def label(self): return EVENT_NAMES.get(self.event,self.event)
    @property
    def description(self):
        if self.event in ('disconnected','security_retry','security_pause','connect_failed','hid_failed'):
            return f'0x{self.detail:02X}: '+REASONS.get(self.detail,'controller/status code')
        if self.event in ('idle_timeout','timeout_saved'): return f'{self.detail} seconds'
        if self.event=='connected': return f'{self.detail/1000:.3f} s since connect request'
        if self.event=='secured': return f'{self.detail/1000:.3f} s after Bluetooth connected'
        if self.event=='input_ready': return f'{self.detail/1000:.3f} s after security completed'
        if self.event=='first_report': return f'{self.detail/1000:.3f} s since connect request'
        if self.event=='manual_pause': return 'Pairing scan' if self.detail==1 else 'Disconnect command'
        return ''

def parse_event(line):
    m=re.search(r'\b(?:LINK_EVENT|HISTORY) boot=([0-9A-F]{8}) seq=(\d+) uptime_ms=(\d+) event=([a-z_]+) detail=(\d+)\s*$',line)
    if not m: return None
    seq,uptime,detail=int(m[2]),int(m[3]),int(m[5])
    if not 1<=seq<=0xFFFFFFFF or not 0<=uptime<=0xFFFFFFFF or not 0<=detail<=0xFFFFFFFF: return None
    return ConnectionEvent(m[1],seq,uptime,m[4],detail)

def uptime_label(milliseconds):
    seconds,millis=divmod(milliseconds,1000);minutes,seconds=divmod(seconds,60);hours,minutes=divmod(minutes,60)
    return f'{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}'

class ConnectionTimeline:
    def __init__(self,capacity=256):
        self.capacity=capacity;self.records=OrderedDict();self.boot_order={}
    def add(self,event):
        key=(event.boot,event.sequence)
        if key in self.records: return False
        self.boot_order.setdefault(event.boot,len(self.boot_order));self.records[key]=event
        while len(self.records)>self.capacity: self.records.popitem(last=False)
        return True
    def events(self): return sorted(self.records.values(),key=lambda e:(self.boot_order[e.boot],e.sequence))

def read_history(bridge):
    for attempt in range(2):
        mark=bridge.send('history')
        try: end=bridge.wait(r'\bHISTORY_END boot=',mark,timeout=5)
        except TimeoutError:
            if attempt: raise
            continue
        marker=re.search(r'HISTORY_END boot=([0-9A-F]{8}) count=(\d+)\b',end)
        if not marker: raise RuntimeError('Malformed history end marker')
        boot,count=marker[1],int(marker[2]);events={};began=False
        if count>32: raise RuntimeError('Unexpected Pico history size')
        with bridge.condition: lines=[line for seq,line in bridge.history if seq>mark]
        for line in lines:
            if re.search(r'\bHISTORY_BEGIN boot='+boot+r' count='+str(count)+r'\b',line):
                began=True;events={};continue
            if not began: continue
            if 'HISTORY_END boot=' in line: break
            event=parse_event(line)
            if event and event.boot==boot and re.search(r'\bHISTORY boot=',line): events[event.sequence]=event
        if began and len(events)==count: return sorted(events.values(),key=lambda e:e.sequence)
    raise RuntimeError('Incomplete Pico history snapshot; refresh again')
