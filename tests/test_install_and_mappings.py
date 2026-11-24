"""Installer invariants: wrong devices, missing backups and changed images stop before writes."""
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from installer import Installer,board_identity
from output_mappings import read_mappings,save_mapping,OUTPUTS
from companion import BUTTONS

IDENTITY='''Device Information
 type: RP2350
 chipid: 0x0123456789abcdef
 secure boot: 0
 flash size: 4096K
'''

class InstallChecks(unittest.TestCase):
    def setUp(self):
        self.tool_patch=patch("installer.shutil.which",return_value=__file__)
        self.tool_patch.start()
        self.addCleanup(self.tool_patch.stop)

    def test_only_one_supported_device_is_accepted(self):
        self.assertEqual(board_identity(IDENTITY),'0123456789ABCDEF')
        for text in (IDENTITY*2,IDENTITY.replace('RP2350','RP2040'),IDENTITY.replace('4096K','2048K'),IDENTITY.replace('secure boot: 0','secure boot: 1'),'No devices'):
            with self.assertRaises(RuntimeError): board_identity(text)

    def scenario(self,directory,change_identity=False):
        root=Path(__file__).resolve().parents[1]
        calls=[]
        def runner(command,**kwargs):
            args=command[1:]; calls.append(args)
            if args[0]=='info':
                text=IDENTITY if not change_identity or len(calls)<4 else IDENTITY.replace('0123','9999')
            else:
                text='OK'
                if args[0]=='save': Path(args[3]).write_bytes(b'\xff'*(4*1024*1024))
            return SimpleNamespace(returncode=0,stdout=text,stderr='')
        installer=Installer(root,runner=runner,backup_directory=Path(directory))
        # Firmware bytes/hash validation is tested by the actual release verifier;
        # use a small isolated image to test transaction ordering independently.
        image=Path(directory)/'image.uf2'; image.write_bytes(b'test image')
        import installer as module
        installer.firmware=lambda hid:(image,module.sha256(image))
        return installer,calls,image

    def test_verified_backup_precedes_load_and_every_operation_is_pinned(self):
        with tempfile.TemporaryDirectory() as directory:
            installer,calls,image=self.scenario(directory)
            prepared=installer.prepare(True); installer.flash(prepared)
            self.assertEqual([c[0] for c in calls],['info','save','info','info','load','reboot'])
            for call in calls[1:]: self.assertEqual(call[-2:],['--ser',prepared.serial])
            self.assertIn('-v',calls[1]); self.assertIn('-v',calls[-2])
            self.assertFalse(any(flag in call for call in calls for flag in ('-f','-F','erase','otp')))

    def test_changed_backup_stops_before_load(self):
        with tempfile.TemporaryDirectory() as directory:
            installer,calls,image=self.scenario(directory); prepared=installer.prepare(True)
            prepared.backup.write_bytes(b'damaged')
            with self.assertRaises(RuntimeError): installer.flash(prepared)
            self.assertNotIn('load',[c[0] for c in calls])

    def test_changed_firmware_stops_before_load(self):
        with tempfile.TemporaryDirectory() as directory:
            installer,calls,image=self.scenario(directory); prepared=installer.prepare(True)
            image.write_bytes(b'changed')
            with self.assertRaises(RuntimeError): installer.flash(prepared)
            self.assertNotIn('load',[c[0] for c in calls])

    def test_replaced_device_stops_before_load(self):
        with tempfile.TemporaryDirectory() as directory:
            installer,calls,image=self.scenario(directory,True); prepared=installer.prepare(True)
            with self.assertRaises(RuntimeError): installer.flash(prepared)
            self.assertNotIn('load',[c[0] for c in calls])

    def test_release_checksum_mismatch_is_rejected(self):
        root=Path(__file__).resolve().parents[1]
        installer=Installer(root)
        with patch('installer.inspect_uf2',return_value={'sha256':'wrong'}):
            with self.assertRaises(RuntimeError): installer.firmware(True)

    def test_failed_device_backup_is_not_installable(self):
        with tempfile.TemporaryDirectory() as directory:
            installer,calls,image=self.scenario(directory)
            underlying=installer.runner
            def failed_save(command,**kwargs):
                result=underlying(command,**kwargs)
                if command[1]=='save': result.returncode=1
                return result
            installer.runner=failed_save
            with self.assertRaises(RuntimeError): installer.prepare(True)
            self.assertNotIn('load',[c[0] for c in calls])

class MappingProtocol(unittest.TestCase):
    def test_older_firmware_is_read_only(self):
        class Old:
            def send(self,command):
                if command!='help': raise AssertionError('Old image received a map command')
                return 0
            def wait(self,*args,**kwargs): return 'LG BRIDGE version=0.11 pico2_w HID=1'
        self.assertIsNone(read_mappings(Old(),set(BUTTONS)))

    def test_unknown_button_and_pointer_click_override_are_rejected_before_send(self):
        bridge=SimpleNamespace()
        with self.assertRaises(ValueError): save_mapping(bridge,0xFFFF,('key',0x28),set(BUTTONS))
        with self.assertRaises(ValueError): save_mapping(bridge,0x8044,('pointer',0),set(BUTTONS))
        self.assertEqual(OUTPUTS['Keyboard F24'],('key',0x73))
        self.assertEqual(OUTPUTS['Keyboard Windows / Start'],('key',0xE3))

if __name__=='__main__': unittest.main()