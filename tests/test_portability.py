import sys,json,tempfile,unittest,base64
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import library_config
import collect
PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=')
class PortableTests(unittest.TestCase):
 def test_setup_custom_categories_and_existing_rules_preserved(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)/'用户的库'; cfg=Path(d)/'config.json'
   library_config.initialize(root,['英语','销售'],cfg)
   self.assertEqual(library_config.resolve_root(config_path=cfg),root.resolve())
   self.assertEqual(library_config.settings(root)['categories'],['英语','销售','待分类'])
   rule=root/'索引/分类规则.md';rule.write_text('用户手写规则',encoding='utf-8')
   library_config.initialize(root,['英语','销售'],cfg)
   self.assertEqual(rule.read_text(),'用户手写规则')
   self.assertTrue((root/'索引/素材总览.base').is_file())
 def test_missing_root_never_writes_to_someone_elses_path(self):
  with tempfile.TemporaryDirectory() as d,patch.dict('os.environ',{},clear=True):
   with self.assertRaises(ValueError):library_config.resolve_root(config_path=Path(d)/'absent.json')
 def test_category_deferred_reminder_and_preserve_notes(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);library_config.initialize(root,[],root/'config.json')
   cover=root/'cover.png';cover.write_bytes(PNG)
   for n in range(10):
    nid=f'{n:024x}';data={'id':nid,'title':'同名标题','author':'同一作者','source_url':'https://www.xiaohongshu.com/explore/'+nid}
    note=collect.save_note(data,'[00:00–00:03] 自制测试文字稿',cover,root)
   self.assertTrue(library_config.classification_due(root))
   note.write_text(note.read_text()+'\n我的备注',encoding='utf-8')
   with self.assertRaises(FileExistsError):collect.save_note(data,'新稿',cover,root)
   self.assertTrue(note.read_text().endswith('我的备注'))
   text=note.read_text();self.assertIn('S0010',text);self.assertIn('主分类: "待分类"',text)
 def test_invalid_custom_category_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);library_config.initialize(root,['销售'],root/'config.json')
   cover=root/'cover.png';cover.write_bytes(PNG)
   data={'id':'1'*24,'title':'演示','author':'演示','source_url':'https://www.xiaohongshu.com/explore/'+'1'*24,'主分类':'擅自新增'}
   with self.assertRaises(ValueError):collect.save_note(data,'文字稿',cover,root)
   self.assertFalse(list((root/'素材笔记').glob('*.md')))
 def test_cover_conversion_without_mac_tool(self):
  from collect_link import convert_cover
  with tempfile.TemporaryDirectory() as d:
   a=Path(d)/'source';a.write_bytes(PNG);b=Path(d)/'cover.jpg'
   with patch('shutil.which',return_value=None):convert_cover(a,b)
   self.assertEqual(collect.cover_extension(b),'.jpg')
