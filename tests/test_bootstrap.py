import importlib.util,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
SCRIPT=Path(__file__).resolve().parents[1]/'scripts/bootstrap.py'
class BootstrapTests(unittest.TestCase):
 def load(self):
  spec=importlib.util.spec_from_file_location('bootstrap',SCRIPT);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
 def test_missing_runtime_is_actionable_without_importing_dependencies(self):
  with tempfile.TemporaryDirectory() as t:
   p=subprocess.run([sys.executable,'-S',str(SCRIPT),'--env',str(Path(t)/'env'),'--check'],capture_output=True,text=True)
   self.assertEqual(p.returncode,2);self.assertEqual(json.loads(p.stdout)['stage'],'runtime_missing')
 def test_network_preference_rejects_nonexistent_interface(self):
  m=self.load()
  with patch.object(m.socket,'if_nameindex',return_value=[(1,'wifi')]):
   with self.assertRaises(ValueError):m.validate_interface('imaginary')
 def test_saved_interface_is_only_applied_to_collection(self):
  m=self.load()
  self.assertEqual(m.command_args('collect_link',['text'],'wifi'),['text','--interface','wifi'])
  self.assertEqual(m.command_args('doctor',[],'wifi'),[])
 def test_failed_write_probe_reports_actual_failure(self):
  m=self.load()
  with tempfile.TemporaryDirectory() as t:
   file=Path(t)/'not-a-directory';file.write_text('keep')
   result=m.write_probe(file)
   self.assertFalse(result['ok']);self.assertTrue(result['error_type']);self.assertEqual(file.read_text(),'keep')
 def test_write_probe_leaves_no_file(self):
  m=self.load()
  with tempfile.TemporaryDirectory() as t:
   self.assertTrue(m.write_probe(Path(t))['ok']);self.assertEqual(list(Path(t).iterdir()),[])
