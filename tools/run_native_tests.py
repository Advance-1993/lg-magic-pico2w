"""Run seven native production-code suites; no device access or flashing."""
from pathlib import Path
import os,shutil,subprocess,sys,tempfile
root=Path(__file__).resolve().parents[1]
cc=os.environ.get('CC') or shutil.which('gcc')
if not cc:raise SystemExit('Set CC to a native GCC and PICO_SDK_PATH to SDK2.2.0')
env=os.environ.copy();env['CC']=cc
env['PATH']=str(Path(cc).parent)+os.pathsep+env['PATH']
suites=[('power_policy_test.c',None,[]),
 ('power_activity_test.c','power_stubs',['-Wno-sign-compare','-DLG_ENABLE_HID=1']),
 ('host_usb_test.c','power_stubs',[]),('power_settings_history_test.c','power_stubs',[]),
 ('hid_reconnect_test.c','reconnect_stubs',['-Wno-sign-compare','-DLG_ENABLE_HID=1']),
 ('mouse_drag_test.c','power_stubs',['-Wno-sign-compare','-DLG_ENABLE_HID=1'])]
with tempfile.TemporaryDirectory(prefix='pico-native-') as temp:
 for name,stub,extra in suites:
  exe=Path(temp)/(name+'.exe')
  args=[cc,'-std=c11','-Wall','-Wextra','-Werror',*extra,'-I'+str(root/'firmware/src')]
  if stub:args+=['-I'+str(root/'tests'/stub)]
  subprocess.run([*args,str(root/'tests'/name),'-lm','-o',str(exe)],check=True,env=env)
  subprocess.run([str(exe)],check=True,env=env)
subprocess.run([sys.executable,str(root/'tests/run_hid_snapshot_test.py')],check=True,env=env)
