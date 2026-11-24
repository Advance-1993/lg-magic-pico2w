"""AHK entry point: enable air mouse. Returns a useful exit code; no console/UI."""
from pathlib import Path
import datetime as dt
from host_actions import enable_pointer

ROOT=Path(__file__).resolve().parent

def main():
    try:
        message=enable_pointer(ROOT); code=0
    except Exception as error:
        message='ERROR: '+str(error); code=1
    (ROOT/'logs').mkdir(exist_ok=True)
    with (ROOT/'logs'/'host-actions.txt').open('a',encoding='utf-8') as log:
        log.write(f'{dt.datetime.now(dt.timezone.utc).isoformat()} F22 {message}\n')
    return code

if __name__=='__main__': raise SystemExit(main())