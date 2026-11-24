"""One allowed local host request: enable the Pico pointer, directly or via its GUI."""
from pathlib import Path
import json
import math
import re
import time
import uuid
import serial
from manage import Bridge, choose_port

REQUEST_TTL=3.0
REQUEST_NAME=re.compile(r'^[0-9a-f]{32}\.request\.json$')


def runtime_directory(root): return Path(root)/'_runtime'/'host-actions'


def write_json(path,value):
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value),encoding='utf-8'); temp.replace(path)


def validate_request(data,serial_number,now):
    if not isinstance(data,dict) or data.get('action')!='mouse_on': raise ValueError('Unsupported host action')
    created=data.get('created')
    if isinstance(created,bool) or not isinstance(created,(int,float)) or not math.isfinite(created): raise ValueError('Invalid request time')
    if not -.25<=now-created<=REQUEST_TTL: raise ValueError('Expired host action')
    if data.get('serial')!=serial_number: raise ValueError('Request belongs to another Pico')
    return 'mouse on'


def perform_mouse_on(bridge):
    # Explicit ON, never toggle. Verify what the Pico reports after the command.
    for attempt in range(2):
        bridge.send('mouse on')
        mark=bridge.send('mouse status')
        line=bridge.wait(r'\bGYRO mode=',mark,timeout=2)
        if re.search(r'\bmode=1\b',line) and re.search(r'\bcalibrating=0\b',line): return line
        if 'calibrating=1' in line: raise RuntimeError('Calibration is active; pointer was not enabled')
    raise RuntimeError('Pico did not confirm pointer mode ON')


def request_via_companion(root,serial_number,timeout=5):
    directory=runtime_directory(root); directory.mkdir(parents=True,exist_ok=True)
    # Remove only our own protocol's abandoned temporary files after one minute.
    for old in directory.iterdir():
        if re.fullmatch(r'[0-9a-f]{32}\.(request|reply|processing)\.json(?:\.tmp)?',old.name):
            try:
                if time.time()-old.stat().st_mtime>60: old.unlink()
            except OSError: pass
    request=directory/(uuid.uuid4().hex+'.request.json')
    reply=request.with_name(request.name.replace('.request.','.reply.'))
    write_json(request,{'action':'mouse_on','serial':serial_number,'created':time.time()})
    try:
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            if reply.exists():
                result=json.loads(reply.read_text(encoding='utf-8'))
                if result.get('ok') is True: return 'companion: '+str(result.get('message','pointer ON'))
                raise RuntimeError(str(result.get('message','Companion rejected the action')))
            time.sleep(.05)
        raise RuntimeError('USB is occupied but no available companion handled the request. Close other serial tools or finish the current operation.')
    finally:
        request.unlink(missing_ok=True); reply.unlink(missing_ok=True)


def enable_pointer(root):
    root=Path(root); port=choose_port(None)
    if port.pid!=0x4005 or not port.serial_number: raise RuntimeError('A USB HID bridge with a serial identity is required')
    (root/'logs').mkdir(exist_ok=True)
    try: bridge=Bridge(port,root/'logs'/'host-actions.txt',quiet=True,log_reports=False)
    except serial.SerialException: return request_via_companion(root,port.serial_number)
    try: return 'direct: '+perform_mouse_on(bridge)
    finally: bridge.close()