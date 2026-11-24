import unittest,threading
from unittest.mock import Mock
from timeout_settings import TIMEOUT_CHOICES,TIMEOUT_SECONDS,LONG_TIMEOUT_SECONDS,timeout_label,timeout_choices_for_version,TimeoutSetting,parse_timeout,read_timeout,save_timeout
from connection_events import parse_event,ConnectionTimeline,read_history,uptime_label
class TimeoutTests(unittest.TestCase):
 def test_requested_choices(self):
  self.assertEqual(TIMEOUT_SECONDS,(30,60,90,180,240,300,360,420,480,540,600,660,720,780,1800,2700,3600,7200,14400,21600,43200))
  self.assertEqual(len(TIMEOUT_CHOICES),21)
 def test_long_choices_labels_and_legacy(self):
  self.assertEqual([timeout_label(v) for v in LONG_TIMEOUT_SECONDS],['30 minutes','45 minutes','1 hour','2 hours','4 hours','6 hours','12 hours'])
  self.assertEqual(len(timeout_choices_for_version('0.22')),14)
  self.assertEqual(len(timeout_choices_for_version('0.23')),21)
  self.assertNotIn('12 hours',timeout_choices_for_version('0.21'))
  for seconds in LONG_TIMEOUT_SECONDS:
   b=Mock();b.send.return_value=1;b.wait.side_effect=[f'TIMEOUT_STORE rc=0 readback=1 applied=1 seconds={seconds}',f'TIMEOUT seconds={seconds} source=flash supported=1']
   self.assertEqual(save_timeout(b,seconds),TimeoutSetting(seconds,'flash'))
 def test_read_and_verified_save(self):
  b=Mock();b.send.return_value=1;b.wait.side_effect=['[5] TIMEOUT_STORE rc=0 readback=1 applied=1 seconds=300','TIMEOUT seconds=300 source=flash supported=1']
  self.assertEqual(save_timeout(b,300),TimeoutSetting(300,'flash'))
  self.assertEqual([call.args[0] for call in b.send.call_args_list],['power timeout 300','power timeout'])
 def test_failure_never_claims_saved(self):
  for line in ['TIMEOUT_REJECT bad','TIMEOUT_STORE rc=0 readback=0 applied=0 seconds=90','TIMEOUT_STORE rc=-1 readback=1 applied=0 seconds=90']:
   b=Mock();b.wait.return_value=line
   with self.assertRaises(RuntimeError):save_timeout(b,90)
  b=Mock();b.wait.side_effect=['TIMEOUT_STORE rc=0 readback=1 applied=1 seconds=90','TIMEOUT seconds=60 source=flash supported=1']
  with self.assertRaises(RuntimeError):save_timeout(b,90)
 def test_rejects_invalid_without_serial_write(self):
  b=Mock()
  for value in [True,90.0,'90',0,31,100000]:
   with self.assertRaises(ValueError):save_timeout(b,value)
  b.send.assert_not_called()
 def test_diagnostic_and_malformed(self):
  self.assertIsNone(parse_timeout('TIMEOUT seconds=90 source=default supported=0'))
  self.assertIsNone(parse_timeout('unrelated'))
  with self.assertRaises(ValueError):parse_timeout('TIMEOUT seconds=31 source=flash supported=1')
class HistoryTests(unittest.TestCase):
 def line(self,seq,event='connected',detail=25,boot='1234ABCD'):
  return f'[100] [BLE] HISTORY boot={boot} seq={seq} uptime_ms=100 event={event} detail={detail}'
 def test_validation_dedup_and_order(self):
  t=ConnectionTimeline(3);a=parse_event(self.line(3));self.assertTrue(t.add(a));self.assertFalse(t.add(a))
  t.add(parse_event(self.line(1)));t.add(parse_event(self.line(2)))
  self.assertEqual([e.sequence for e in t.events()],[1,2,3])
  t.add(parse_event(self.line(4)));self.assertEqual(len(t.events()),3)
  self.assertIsNone(parse_event(self.line(0)));self.assertIsNone(parse_event(self.line(1).replace('uptime_ms=100','uptime_ms=4294967296')))
 def test_reasons_durations_boots(self):
  self.assertIn('Pico closed',parse_event(self.line(1,'disconnected',22)).description)
  self.assertIn('90 seconds',parse_event(self.line(1,'idle_timeout',90)).description)
  self.assertEqual(uptime_label(90029),'00:01:30.029')
  t=ConnectionTimeline();t.add(parse_event(self.line(1)));t.add(parse_event(self.line(1,boot='00000001')));self.assertEqual(len(t.events()),2)
 def test_snapshot_validation(self):
  b=Mock();b.condition=threading.Condition();b.send.return_value=0
  b.wait.return_value='HISTORY_END boot=1234ABCD count=2'
  b.history=[(1,'HISTORY_BEGIN boot=1234ABCD count=2'),(2,self.line(1)),(3,self.line(2,'idle_timeout',90)),(4,b.wait.return_value)]
  self.assertEqual(len(read_history(b)),2)
  b.history.pop(2)
  with self.assertRaises(RuntimeError):read_history(b)
