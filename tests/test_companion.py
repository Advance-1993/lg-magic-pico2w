"""Guard live display against interpreting unknown layouts as real buttons."""
import sys
from pathlib import Path
import unittest
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from companion import input_report,windows_action,load_labels,BUTTONS,Companion

class Reports(unittest.TestCase):
    def test_captured_layout_and_signed_wheel(self):
        data=bytearray(20); data[0]=0xFD; data[17:19]=bytes.fromhex('807C'); data[19]=255
        self.assertEqual(input_report('REPORT svc=0 id=FD len=20 offset=0 data='+data.hex().upper()),(0x807C,-1))

    def test_other_layouts_and_incomplete_data_are_not_live_keys(self):
        for line in ('REPORT svc=0 id=FD len=20 offset=0 data=FD',
                     'REPORT svc=0 id=F9 len=20 offset=0 data='+'00'*20,
                     'REPORT svc=0 id=FD len=20 offset=0 data='+'00'*20):
            self.assertIsNone(input_report(line))

    def test_ok_mapping_changes_with_pointer_mode(self):
        self.assertEqual(windows_action(0x8044,False),'Enter')
        self.assertEqual(windows_action(0x8044,True),'Left mouse button (click; hold to drag)')
        self.assertEqual(windows_action(0x807C),'Windows / Start (Left GUI)')
        self.assertIn('no Windows key',windows_action(0xFFFF))

    def test_drag_label_follows_firmware_support(self):
        app=SimpleNamespace(drag_supported=False)
        self.assertEqual(Companion.effective_action(app,0x8044,True),'Left mouse click')
        app.drag_supported=True
        self.assertEqual(Companion.effective_action(app,0x8044,True),'Left mouse button (click; hold to drag)')

    def test_user_identified_extra_controls(self):
        for code,key in ((0x8029,'F19'),(0x80A1,'F20'),(0x80AB,'F21'),(0x8045,'F22'),(0x8043,'F12')):
            self.assertEqual(windows_action(code),key)
            self.assertTrue(BUTTONS[code])

    def test_saved_play_pause_is_displayed_instead_of_factory_f12(self):
        app=SimpleNamespace(device_mappings={0x8043:('consumer',0xCD)},
                            mapping_required=False,legacy_defaults=False)
        self.assertEqual(Companion.effective_action(app,0x8043),'Media Play / Pause')
        self.assertEqual(BUTTONS[0x8043],'Select / Settings')
        app.device_mappings={0x8043:('key',0x45)}
        self.assertEqual(Companion.effective_action(app,0x8043),'Keyboard F12')

    def test_f18_host_action_annotation_follows_actual_output(self):
        app=SimpleNamespace(device_mappings={0x800C:('key',0x6D)},
                            mapping_required=False,legacy_defaults=False)
        self.assertEqual(Companion.effective_action(app,0x800C),
                         'Keyboard F18 — AHK: double tap → TV off + PC shutdown')
        app.device_mappings[0x800C]=('key',0x68)
        self.assertEqual(Companion.effective_action(app,0x800C),'Keyboard F13')

    def test_local_labels_cannot_inject_unknown_codes_or_controls(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'labels.json'
            path.write_text('{"8056":"Netflix", "FFFF":"Fake", "8040":"bad\\nlabel", "8041":3}')
            self.assertEqual(load_labels(path),{0x8056:'Netflix'})
            path.write_text('[]'); self.assertEqual(load_labels(path),{})

    def test_cancel_model_check_does_not_scan_or_warn_about_unknown_model(self):
        app=SimpleNamespace(bridge=SimpleNamespace(port=SimpleNamespace(pid=0x4005)),
                            busy=False,pair_window=None,root=None)
        with patch('companion.simpledialog.askstring',return_value=None), patch('companion.messagebox.showinfo') as info:
            Companion.pair_dialog(app)
            info.assert_not_called()

if __name__=='__main__': unittest.main()
