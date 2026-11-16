import sys
sys.path.insert(0,str(__import__("pathlib").Path(__file__).resolve().parents[1]/"scripts"))
import importlib.util
from pathlib import Path
import tempfile
import unittest
import base64
from unittest.mock import patch

PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=')

PATH = Path(__file__).resolve().parents[1]/'scripts'/'collect.py'

class ContractTests(unittest.TestCase):
    def test_readable_filename_and_dedup_after_rename(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);cover=root/'source.png';cover.write_bytes(PNG)
            data={'id':'0123456789abcdef01234567','title':'中文标题','author':'作者','source_url':'https://www.xiaohongshu.com/explore/0123456789abcdef01234567'}
            dest=self.m.save_note(data,'真实文字稿',cover,root/'库')
            self.assertEqual(dest.name,'中文标题 — 作者.md')
            renamed=dest.with_name('用户自己修改的标题.md');dest.rename(renamed)
            self.assertEqual(self.m.find_existing_note(root/'库',data['id']),renamed.resolve())
            with self.assertRaises(FileExistsError):self.m.save_note(data,'新转写',cover,root/'库')
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('collect', PATH)
        cls.m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.m)

    def test_share_text_and_query_are_preserved(self):
        url = 'https://www.xiaohongshu.com/explore/0123456789abcdef01234567?xsec_token=a%2Bb&xsec_source=pc_share'
        self.assertEqual(self.m.input_url('标题 '+url+' 复制打开'), url)
        self.assertEqual(self.m.input_url('标题 https://xhslink.cn/o/Abc。'), 'https://xhslink.cn/o/Abc')
        with self.assertRaises(ValueError): self.m.input_url('https://xiaohongshu.com.evil.org/a')

    def test_state_parser_does_not_modify_string_undefined(self):
        html = '<script>window.__INITIAL_STATE__={"a":undefined,"title":"undefined中文"}</script>'
        self.assertEqual(self.m.parse_state(html), {'a':None,'title':'undefined中文'})

    def test_mobile_page_source_subtitles_and_nickname(self):
        import json
        with tempfile.TemporaryDirectory() as d:
            nid='0123456789abcdef01234567'
            note={'noteId':nid,'title':'真实标题','user':{'nickName':'作者'},'imageList':[{'url':'https://sns-webpic-qc.xhscdn.com/cover.jpg'}],
                  'video':{'media':{'video':{'duration':12}},'mediaV2':json.dumps({'video':{'subtitles':{'source':[{'url':'https://sns-subtitle-s1.xhscdn.com/test.srt','language':'zh-CN'}]}}})}}
            html=Path(d)/'page.html';html.write_text('<script>window.__INITIAL_STATE__='+json.dumps({'noteData':{'data':{'noteData':note}}})+'</script>')
            result=self.m.inspect_url('https://www.xiaohongshu.com/discovery/item/'+nid,html)
            self.assertEqual(result['author'],'作者');self.assertEqual(result['duration_seconds'],12)
            self.assertEqual(result['subtitle_url'],'https://sns-subtitle-s1.xhscdn.com/test.srt')
            self.assertEqual(result['cover_url'],'https://sns-webpic-qc.xhscdn.com/cover.jpg')

    def test_srt_integrity_and_end_coverage(self):
        text='1\n00:00:00,000 --> 00:00:01,500\n中文\n\n2\n00:00:01,600 --> 00:00:02,800\n结束\n'
        transcript,report=self.m.srt_transcript(text,3.0)
        self.assertIn('中文',transcript);self.assertIn('结束',transcript)
        self.assertEqual(report['cue_count'],2)
        with self.assertRaises(ValueError): self.m.srt_transcript(text,100.0)
        with self.assertRaises(ValueError): self.m.srt_transcript('<html>error</html>',3.0)
        with self.assertRaises(ValueError): self.m.srt_transcript(text,None)
        with self.assertRaises(ValueError): self.m.srt_transcript(text,0)

    def test_metadata_zero_likes_and_source_publish_time(self):
        note = {'noteId':'0123456789abcdef01234567','title':'中文','time':1700000000000,
                'lastUpdateTime':1800000000000,'interactInfo':{'likedCount':'0'},'user':{'nickname':'作者'}}
        result = self.m.metadata(note, 'https://www.xiaohongshu.com/explore/'+note['noteId'])
        self.assertEqual(result['likes'], '0')
        self.assertTrue(result['published_at'].startswith('2023-11-15'))

    def test_missing_transcript_or_cover_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            data = {'id':'0123456789abcdef01234567','title':'标题','source_url':'https://www.xiaohongshu.com/explore/0123456789abcdef01234567'}
            with self.assertRaises(ValueError): self.m.save_note(data, '', None, Path(d))
            self.assertFalse(list(Path(d).rglob('*.md')))

    def test_integrated_utf8_note_safe_filename_duplicate_protection(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); cover=root/'source.png'; cover.write_bytes(PNG)
            data={'id':'0123456789abcdef01234567','title':'../../中文:标题','source_url':'https://www.xiaohongshu.com/explore/0123456789abcdef01234567','likes':'0','published_at':'未获取','author':'作者','description':'笔记文案'}
            note=self.m.save_note(data, '[00:00] 这是中文口播。', cover, root/'库')
            text=note.read_text(encoding='utf-8')
            self.assertIn('这是中文口播',text); self.assertIn('![封面](../',text)
            self.assertIn('点赞数',text); self.assertIn('笔记文案',text)
            self.assertEqual(note.parent,(root/'库'/'素材笔记').resolve())
            note.write_text(text+'\n人工备注',encoding='utf-8')
            with self.assertRaises(FileExistsError): self.m.save_note(data,'另一份口播',cover,root/'库')
            self.assertTrue(note.read_text(encoding='utf-8').endswith('人工备注'))

    def test_truncated_image_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            cover=Path(d)/'bad.jpg'; cover.write_bytes(b'\xff\xd8\xff')
            with self.assertRaises(ValueError): self.m.cover_extension(cover)

    def test_blank_metadata_cannot_be_complete(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); cover=root/'source.png'; cover.write_bytes(PNG)
            data={'id':'0123456789abcdef01234567','title':'标题','source_url':'https://www.xiaohongshu.com/explore/0123456789abcdef01234567','author':'  ','published_at':'','likes':''}
            dest=self.m.save_note(data,'真实口播',cover,root/'库')
            self.assertIn('status: "partial"',dest.read_text(encoding='utf-8'))

    def test_source_id_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); cover=root/'source.png'; cover.write_bytes(PNG)
            data={'id':'0123456789abcdef01234567','title':'标题','source_url':'https://www.xiaohongshu.com/explore/aaaaaaaaaaaaaaaaaaaaaaaa'}
            with self.assertRaises(ValueError): self.m.save_note(data,'真实口播',cover,root/'库')

    def test_commit_failure_does_not_leave_broken_note(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); cover=root/'source.png'; cover.write_bytes(PNG)
            data={'id':'0123456789abcdef01234567','title':'标题','source_url':'https://www.xiaohongshu.com/explore/0123456789abcdef01234567'}
            real_link=__import__('os').link
            def fail_note(src,dst):
                if str(dst).endswith('.md'): raise OSError('simulated disk failure')
                return real_link(src,dst)
            with patch.object(self.m.os,'link',side_effect=fail_note):
                with self.assertRaises(OSError): self.m.save_note(data,'真实口播',cover,root/'库')
            self.assertFalse(list((root/'库').rglob('*.md')))
            self.assertFalse(list((root/'库'/'封面附件').glob('*')))

if __name__ == '__main__': unittest.main()
