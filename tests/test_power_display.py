import unittest
from companion import power_description
class PowerDisplay(unittest.TestCase):
 def test_long_countdown(self):
  self.assertIn('12:00:00',power_description('POWER state=awake usb_flags=1 idle_ms=0 limit_ms=43200000 armed=0 enabled=1'))
  self.assertIn('11:59:59',power_description('POWER state=awake usb_flags=1 idle_ms=1000 limit_ms=43200000 armed=0 enabled=1'))
 def test_meaningful_status(self):
  self.assertIn('0:03',power_description('POWER state=awake usb_flags=1 idle_ms=87001 limit_ms=90000 armed=0 enabled=1'))
  self.assertIn('press a remote button',power_description('POWER state=idle usb_flags=1 idle_ms=90001 limit_ms=90000 armed=1 enabled=1'))
  self.assertIn('USB host unavailable',power_description('POWER state=usb_off usb_flags=3 idle_ms=3000 limit_ms=90000 armed=0 enabled=1'))
  self.assertIn('disabled',power_description('POWER state=awake usb_flags=1 idle_ms=0 limit_ms=90000 armed=0 enabled=0'))
  self.assertIsNone(power_description('STATUS state=5'))
