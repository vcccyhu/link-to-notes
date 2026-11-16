"""Offline end-to-end fixtures, not proof of live platform availability."""
import sys,json,tempfile,unittest,base64,io
from pathlib import Path
from unittest.mock import patch
from contextlib import redirect_stdout
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import collect_link,collect,library_config
PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=')
ID='0123456789abcdef01234567'
class FixtureFetcher:
 no_sub=False
 def __init__(self,*a):pass
 def page(self,url,dest):
  note={'noteId':ID,'title':'自制演示','user':{'nickName':'演示作者'},'time':1700000000000,'interactInfo':{'likedCount':'0'},'imageList':[{'url':'https://fixture.xhscdn.com/cover'}],
   'video':{'media':{'video':{'duration':3}},'mediaV2':json.dumps({'video':{'subtitles':{} if self.no_sub else {'source':[{'language':'zh-CN','url':'https://fixture.xhscdn.com/sub'}]}}})}}
  dest.write_text('<script>window.__INITIAL_STATE__='+json.dumps({'noteData':{'data':{'noteData':note}}})+'</script>',encoding='utf-8')
  return 'https://www.xiaohongshu.com/explore/'+ID
 def get(self,url,dest):
  if url.endswith('/sub'):dest.write_text('1\n00:00:00,000 --> 00:00:02,900\n这是一段自制字幕。\n',encoding='utf-8')
  else:dest.write_bytes(PNG)
  return 200,''
class PipelineTests(unittest.TestCase):
 def run_main(self,root):
  out=io.StringIO()
  with patch.object(collect_link,'Fetcher',FixtureFetcher),patch.object(sys,'argv',['collect_link.py','自制分享 https://xhslink.cn/o/fixture','--root',str(root)]),redirect_stdout(out):collect_link.main()
  return json.loads(out.getvalue())
 def test_new_library_collect_and_duplicate_keep_user_notes(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)/'有空格的 素材库';library_config.initialize(root,['学习'],Path(d)/'settings.json')
   result=self.run_main(root);self.assertEqual(result['status'],'saved')
   note=Path(result['path']);note.write_text(note.read_text()+'\n我的人工备注',encoding='utf-8')
   self.assertEqual(self.run_main(root)['status'],'already_saved')
   self.assertTrue(note.read_text().endswith('我的人工备注'))
   self.assertIn('这是一段自制字幕',note.read_text())
   self.assertTrue((root/'封面附件'/f'{ID}.jpg').is_file())
 def test_no_subtitle_never_creates_finished_note(self):
  with tempfile.TemporaryDirectory() as d,patch.object(FixtureFetcher,'no_sub',True):
   root=Path(d)/'库';library_config.initialize(root,[],Path(d)/'settings.json')
   with self.assertRaisesRegex(ValueError,'音频转写'):self.run_main(root)
   self.assertFalse(list((root/'素材笔记').glob('*.md')))
 def test_long_same_title_two_platform_ids_do_not_overwrite(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);cover=root/'cover.png';cover.write_bytes(PNG)
   for nid in ['1'*24,'2'*24]:
    p=collect.save_note({'id':nid,'title':'长标题'*100,'author':'作者','source_url':'https://www.xiaohongshu.com/explore/'+nid},'真实稿',cover,root)
    self.assertLessEqual(len(p.name.encode()),255)
   self.assertEqual(len(list((root/'素材笔记').glob('*.md'))),2)
