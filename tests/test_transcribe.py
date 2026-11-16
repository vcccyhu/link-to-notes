import sys
sys.path.insert(0,str(__import__("pathlib").Path(__file__).resolve().parents[1]/"scripts"))
import importlib.util
from pathlib import Path
import unittest
import tempfile,wave,struct
PATH=Path(__file__).resolve().parents[1]/'scripts'/'transcribe.py'
spec=importlib.util.spec_from_file_location('transcribe',PATH);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class LanguageTests(unittest.TestCase):
 def test_default_language_is_auto(self):
  args=module.build_parser().parse_args(['sample.wav','--out','out.txt'])
  self.assertEqual(args.language,'auto')
 def test_can_explicitly_transcribe_english(self):
  args=module.build_parser().parse_args(['sample.wav','--out','out.txt','--language','en'])
  self.assertEqual(args.language,'en')
 def test_audio_is_normalized_without_pyav_file_decoder(self):
  with tempfile.TemporaryDirectory() as d:
   source=Path(d)/'stereo.wav'
   with wave.open(str(source),'wb') as w:
    w.setnchannels(2);w.setsampwidth(2);w.setframerate(22050)
    w.writeframes(struct.pack('<hh',1000,-500)*22050)
   audio=module.prepare_audio(source,Path(d))
   self.assertEqual(audio.shape,(16000,))
   self.assertEqual(str(audio.dtype),'float32')
if __name__=='__main__':unittest.main()
