import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from collect import input_url
import bootstrap
from unittest.mock import patch
class ShareInputTests(unittest.TestCase):
 def test_markdown_url_label_and_destination(self):
  u='https://xhslink.cn/o/demo'
  self.assertEqual(input_url('标题 ['+u+']('+u+') 打开小红书'),u)
 def test_markdown_label_and_full_signed_url(self):
  u='https://www.xiaohongshu.com/explore/'+'a'*24+'?xsec_token=a%2Bb%3D&xsec_source=pc_share'
  self.assertEqual(input_url('[打开笔记]('+u+')'),u)
 def test_bad_port_before_valid_share_is_skipped(self):
  self.assertEqual(input_url('https://xhslink.cn:bad/o/no https://xhslink.cn/o/yes'),'https://xhslink.cn/o/yes')
 def test_proxy_preference_is_opt_in_and_collection_only(self):
  with patch.dict(bootstrap.os.environ,{'NO_PROXY':'localhost','no_proxy':'localhost'},clear=True):
   self.assertEqual(bootstrap.collection_env('collect_link',{})['NO_PROXY'],'localhost')
   pref={'no_proxy_domains':['xhslink.cn','.xhscdn.com']}
   env=bootstrap.collection_env('collect_link',pref)
   self.assertEqual(env['NO_PROXY'],'localhost,xhslink.cn,.xhscdn.com')
   self.assertEqual(env['no_proxy'],env['NO_PROXY'])
   self.assertEqual(bootstrap.collection_env('doctor',pref)['NO_PROXY'],'localhost')
   self.assertEqual(bootstrap.os.environ['NO_PROXY'],'localhost')
 def test_proxy_preference_cannot_bypass_unrelated_hosts(self):
  for hosts in [['*'],['example.com'],'xhslink.cn']:
   with self.assertRaises(ValueError):bootstrap.collection_env('collect_link',{'no_proxy_domains':hosts})
 def test_new_library_creates_only_core_directories_and_preserves_existing(self):
  import tempfile
  from library_config import initialize
  with tempfile.TemporaryDirectory() as t:
   root=Path(t)/'素材库';cfg=Path(t)/'config.json'
   initialize(root,config_path=cfg)
   self.assertEqual({p.name for p in root.iterdir() if p.is_dir()},{'素材笔记','封面附件','索引'})
   optional=root/'分析清单';optional.mkdir();(optional/'保留.md').write_text('keep')
   initialize(root,config_path=cfg)
   self.assertEqual((optional/'保留.md').read_text(),'keep')
