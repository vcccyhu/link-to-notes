import sys,unittest,tempfile,json,base64,io
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import collect,library_config
PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=')
class ReleaseEdges(unittest.TestCase):
 def test_chinese_subtitle_fallback_after_foreign_source(self):
  note={'noteId':'1'*24,'video':{'mediaV2':json.dumps({'video':{'subtitles':{'source':[{'url':'en','language':'en'}],'zh-CN':[{'url':'zh','language':'zh-CN'}]}}})}}
  self.assertEqual(collect.metadata(note,'https://www.xiaohongshu.com/explore/'+'1'*24)['subtitle_url'],'zh')
 def test_invalid_minute_or_second_rejected(self):
  for start,end in [('00:00:61,000','00:01:03,000'),('00:60:00,000','01:00:02,000')]:
   with self.subTest(start=start),self.assertRaises(ValueError):collect.srt_transcript('1\n00:00:00,000 --> 00:00:02,000\n开头\n\n2\n'+start+' --> '+end+'\n文字',63 if start.startswith('00:00:') else 3602)
 def test_internal_gap_is_reported_for_content_review(self):
  _,report=collect.srt_transcript('1\n00:00:00,000 --> 00:00:02,000\n开头\n\n2\n00:00:27,000 --> 00:00:30,000\n结尾',30)
  self.assertEqual(report['max_gap_seconds'],25)
  self.assertTrue(report['requires_content_review'])
 def test_whitespace_title_never_counts_as_complete(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);c=root/'c.png';c.write_bytes(PNG)
   with self.assertRaises(ValueError):collect.save_note({'id':'1'*24,'title':'  ','source_url':'https://www.xiaohongshu.com/explore/'+'1'*24},'正文',c,root)
 def test_gap_review_is_partial_not_complete(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);c=root/'c.png';c.write_bytes(PNG)
   p=collect.save_note({'id':'1'*24,'title':'字幕需复核','author':'演示','published_at':'2026-11-15T00:00:00+08:00','likes':'0','source_url':'https://www.xiaohongshu.com/explore/'+'1'*24,'transcript_review_required':True},'[00:00–00:30] 文字稿有内部空档',c,root)
   self.assertIn('status: "partial"',p.read_text())
   self.assertIn('字幕内部空档待核对',p.read_text())
 def test_root_precedence_is_explicit_then_environment_then_config(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);cfg=p/'conf.json';cfg.write_text(json.dumps({'root':str(p/'configured')}))
   with patch.dict('os.environ',{'XHS_LIBRARY_ROOT':str(p/'env')}):
    self.assertEqual(library_config.resolve_root(p/'explicit',cfg),(p/'explicit').resolve())
    self.assertEqual(library_config.resolve_root(config_path=cfg),(p/'env').resolve())
 def test_malformed_config_stops_without_overwrite(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);(root/'索引').mkdir();p=root/'索引/收纳设置.json';p.write_text('{broken')
   with self.assertRaises(ValueError):library_config.settings(root)
   self.assertEqual(p.read_text(),'{broken')
 def test_duplicate_recognized_after_regular_yaml_rewrite(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);(root/'素材笔记').mkdir();p=root/'素材笔记/用户改名.md'
   p.write_text('---\nplatform: 小红书\nnote_id: '+('a'*24)+'\n素材编号: S0008\n---\n\n人工备注',encoding='utf-8')
   self.assertEqual(collect.find_existing_note(root,'a'*24),p.resolve())
 def test_missing_dependencies_are_reported_by_doctor(self):
  import subprocess
  p=Path(__file__).resolve().parents[1]/'scripts/doctor.py'
  proc=subprocess.run([sys.executable,'-S',str(p)],capture_output=True,text=True)
  self.assertNotEqual(proc.returncode,0)
  self.assertFalse(json.loads(proc.stdout)['pillow'])
