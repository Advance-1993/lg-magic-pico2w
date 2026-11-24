"""Regression checks for setup failures seen during real hardware testing."""
import contextlib
import io
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import manage


class Advertisements(unittest.TestCase):
    def test_observed_lg_manufacturer_and_name(self):
        data = manage.decode_advertisement('02010517FFC4005343442032312E322C42412033352C7765624F53')
        self.assertEqual(data['manufacturer'], 0xC4)
        self.assertEqual(manage.decode_advertisement('0B094C4745204D5232354741')['name'], 'LGE MR25GA')

    def test_truncated_fields_are_not_read_as_a_device_identity(self):
        self.assertEqual(manage.decode_advertisement('FF094142'), {})
        self.assertEqual(manage.decode_advertisement('01FF'), {})
        self.assertEqual(manage.decode_advertisement('00'), {})

    def test_terminal_control_characters_in_names_are_sanitized(self):
        self.assertEqual(manage.decode_advertisement('0409411B42')['name'], 'A?B')


class PairingMilestones(unittest.TestCase):
    def test_subscription_without_input_is_not_success(self):
        class NoReports:
            def wait(self, pattern, after, timeout):
                if pattern == 'HID_SUBSCRIBED':
                    return 'HID_SUBSCRIBED'
                raise TimeoutError('no input')
        with self.assertRaises(TimeoutError), contextlib.redirect_stdout(io.StringIO()):
            manage.pairing_result(NoReports(), 0)

    def test_unknown_model_is_not_paired_from_hid_image(self):
        bridge = SimpleNamespace(port=SimpleNamespace(pid=0x4005))
        with patch('builtins.input', return_value='MR26GA'), contextlib.redirect_stdout(io.StringIO()):
            manage.pair(bridge)  # no scan/send method exists: it must stop first.

    def test_late_success_does_not_disconnect_and_restart_good_link(self):
        class LateBridge:
            port = SimpleNamespace(pid=0x4005)
            def __init__(self):
                self.commands = []
                self.scan_calls = 0
                self.subscribe_checks = 0
            def scan_ready(self):
                self.scan_calls += 1
            def show_devices(self):
                return [(('02:00:00:00:00:01', 0), {})]
            def send(self, command):
                self.commands.append(command)
                return len(self.commands)
            def wait(self, pattern, after, timeout=8):
                if pattern == 'HID_SUBSCRIBED':
                    self.subscribe_checks += 1
                    if self.subscribe_checks <= 2:
                        raise TimeoutError('just before physical OK press')
                    return 'HID_SUBSCRIBED'
                if pattern == r'\bREPORT ':
                    return 'REPORT svc=0 id=FD len=20 offset=0 data=FD'
                return pattern
        bridge = LateBridge()
        answers = ['MR25GA', 'READY', '', '1', 'PAIR', 'YES']
        with patch('builtins.input', side_effect=answers), contextlib.redirect_stdout(io.StringIO()):
            manage.pair(bridge)
        self.assertEqual(bridge.scan_calls, 2)  # initial discovery + first attempt only.
        self.assertEqual(sum(c.startswith('pair ') for c in bridge.commands), 1)


if __name__ == '__main__':
    unittest.main()
