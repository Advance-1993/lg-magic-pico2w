"""Named USB outputs and the validated firmware mapping serial protocol."""
import re

OUTPUTS={'Disabled':('none',0),'Toggle air mouse':('pointer',0)}
for i,letter in enumerate('ABCDEFGHIJKLMNOPQRSTUVWXYZ',4): OUTPUTS[f'Keyboard {letter}']=('key',i)
for i,digit in enumerate('1234567890',0x1E): OUTPUTS[f'Keyboard {digit}']=('key',i)
for i in range(1,25): OUTPUTS[f'Keyboard F{i}']=('key',0x39+i if i<=12 else 0x68+i-13)
for name,value in {'Enter':0x28,'Escape':0x29,'Backspace':0x2A,'Tab':0x2B,'Space':0x2C,
 'Minus':0x2D,'Equals':0x2E,'Left bracket':0x2F,'Right bracket':0x30,'Backslash':0x31,
 'Semicolon':0x33,'Apostrophe':0x34,'Grave':0x35,'Comma':0x36,'Period':0x37,'Slash':0x38,
 'Caps Lock':0x39,'Print Screen':0x46,'Scroll Lock':0x47,'Pause':0x48,'Insert':0x49,
 'Home':0x4A,'Page Up':0x4B,'Delete':0x4C,'End':0x4D,'Page Down':0x4E,
 'Right arrow':0x4F,'Left arrow':0x50,'Down arrow':0x51,'Up arrow':0x52,
 'Application menu':0x65,'Left Ctrl':0xE0,'Left Shift':0xE1,'Left Alt':0xE2,
 'Windows / Start':0xE3,'Right Ctrl':0xE4,'Right Shift':0xE5,'Right Alt':0xE6,'Right Windows':0xE7}.items(): OUTPUTS['Keyboard '+name]=('key',value)
for name,value in {'Volume Up':0xE9,'Volume Down':0xEA,'Mute':0xE2,'Play / Pause':0xCD,
                   'Next track':0xB5,'Previous track':0xB6,'Stop':0xB7}.items(): OUTPUTS['Media '+name]=('consumer',value)


def describe(action):
    for name,value in OUTPUTS.items():
        if value==action: return name
    return f'{action[0]} HID 0x{action[1]:04X}'


def read_mappings(bridge,expected_codes):
    for attempt in range(2):
        mark=bridge.send('help')
        try:
            help_line=bridge.wait(r'LG BRIDGE .*HID=',mark,timeout=4); break
        except TimeoutError:
            if attempt: raise
    version=re.search(r'version=(\d+)\.(\d+)',help_line)
    if not version or tuple(map(int,version.groups()))<(0,12) or 'HID=1' not in help_line:
        return None
    for attempt in range(2):
        mark=bridge.send('map list')
        try: bridge.wait(r'MAP_END count=23\b',mark,timeout=6)
        except TimeoutError:
            if attempt: raise
            continue
        with bridge.condition: lines=[line for sequence,line in bridge.history if sequence>mark]
        result={}
        for line in lines:
            match=re.search(r'\bMAP code=([0-9A-F]{4}) kind=(key|consumer|pointer|none) value=([0-9A-F]{4})\b',line)
            if match:
                code=int(match[1],16)
                if code in expected_codes: result[code]=(match[2],int(match[3],16))
        if set(result)==set(expected_codes): return result
    raise RuntimeError('Incomplete mapping readback. Please Read from Pico again; no mapping was changed.')


def save_mapping(bridge,code,action,expected_codes):
    if code not in expected_codes or action not in OUTPUTS.values(): raise ValueError('Unsupported button/output')
    if code==0x8044 and action[0]=='pointer': raise ValueError('Wheel/OK remains a click in pointer mode; choose a navigation key instead.')
    mark=bridge.send(f'map set {code:04X} {action[0]} {action[1]:04X}')
    result=bridge.wait(r'MAP_STORE |MAP_REJECT ',mark,timeout=8)
    if 'applied=1' not in result: raise RuntimeError('Mapping was not saved/applied: '+result)
    mappings=read_mappings(bridge,expected_codes)
    if not mappings or mappings[code]!=action: raise RuntimeError('Mapping readback differs from the requested output.')
    return mappings


def restore_mappings(bridge,expected_codes):
    mark=bridge.send('map reset')
    result=bridge.wait(r'MAP_STORE ',mark,timeout=8)
    if 'applied=1' not in result: raise RuntimeError('Defaults were not applied: '+result)
    return read_mappings(bridge,expected_codes)