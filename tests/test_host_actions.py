"""F22 transport checks: explicit ON, no arbitrary commands or stale replays."""
import json
from pathlib import Path
import sys,tempfile,time,unittest
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import host_actions as h
from companion import Companion

class FakeBridge:
    error=None
    port=SimpleNamespace(serial_number='PICO123',pid=0x4005)
    def __init__(self,line='GYRO mode=1 gain=12.500 calibrating=0'):
        self.line=line;self.commands=[];self.closed=False
    def send(self,command): self.commands.append(command);return len(self.commands)
    def wait(self,*args,**kwargs): return self.line
    def close(self): self.closed=True

class Actions(unittest.TestCase):
    def test_explicit_on_does_not_toggle_or_touch_other_settings(self):
        bridge=FakeBridge();self.assertIn('mode=1',h.perform_mouse_on(bridge))
        self.assertEqual(bridge.commands,['mouse on','mouse status'])

    def test_calibration_blocks_success(self):
        with self.assertRaises(RuntimeError): h.perform_mouse_on(FakeBridge('GYRO mode=0 calibrating=1'))

    def test_requests_reject_other_actions_peers_and_expired_times(self):
        good={'action':'mouse_on','serial':'PICO123','created':100.0}
        self.assertEqual(h.validate_request(good,'PICO123',101),'mouse on')
        for change in ({'action':'bootsel'},{'serial':'OTHER'},{'created':90},{'created':110},{'created':float('nan')},{'created':True}):
            with self.assertRaises(ValueError): h.validate_request(good|change,'PICO123',101)

    def test_busy_serial_uses_companion_transport(self):
        with tempfile.TemporaryDirectory() as directory, patch('host_actions.choose_port',return_value=FakeBridge.port),patch('host_actions.Bridge',side_effect=h.serial.SerialException('occupied')),patch('host_actions.request_via_companion',return_value='companion: OK') as ipc:
            self.assertEqual(h.enable_pointer(directory),'companion: OK')
            ipc.assert_called_once_with(Path(directory),'PICO123')

    def test_free_serial_closes_its_connection(self):
        bridge=FakeBridge()
        with tempfile.TemporaryDirectory() as directory,patch('host_actions.choose_port',return_value=bridge.port),patch('host_actions.Bridge',return_value=bridge):
            self.assertTrue(h.enable_pointer(directory).startswith('direct:'))
            self.assertTrue(bridge.closed)

    def test_companion_handles_only_the_allowed_request(self):
        for action,expected in [('mouse_on',True),('bootsel',False)]:
            with self.subTest(action=action),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);runtime=h.runtime_directory(root);runtime.mkdir(parents=True)
                path=runtime/('a'*32+'.request.json')
                h.write_json(path,{'action':action,'serial':'PICO123','created':time.time()})
                bridge=FakeBridge()
                app=SimpleNamespace(busy=False,bridge=bridge,work=lambda fn,done:done(fn()),note=lambda text:None)
                with patch('companion.ROOT',root): Companion.poll_host_actions(app)
                reply=json.loads((runtime/('a'*32+'.reply.json')).read_text())
                self.assertEqual(reply['ok'],expected)
                self.assertEqual(bridge.commands,['mouse on','mouse status'] if expected else [])
                self.assertFalse(path.exists())

if __name__=='__main__':unittest.main()