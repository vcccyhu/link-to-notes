"""Validate and save local notes. Network acquisition and ASR remain separate stages."""
import argparse
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import json
from pathlib import Path
import re
import shutil
import os
import subprocess
import tempfile
import math
from urllib.parse import urlparse, quote
from urllib.request import Request, urlopen

TZ = ZoneInfo('Asia/Shanghai')
from library_config import resolve_root, settings
import yaml
DEFAULT_ROOT = None
HOSTS = {'xiaohongshu.com','www.xiaohongshu.com','xhslink.cn','www.xhslink.cn','xhslink.com','www.xhslink.com'}
ID_RE = re.compile(r'/(?:explore|discovery/item|search_result)/([a-fA-F0-9]{24})(?:[/?#]|$)')

def now():
    return datetime.now(TZ).isoformat(timespec='seconds')

def input_url(text):
    for match in re.finditer(r'https?://[^\s<>"\u201c\u201d]+',text):
        url = match.group().rstrip('。；，、）)]}')
        p = urlparse(url)
        if p.hostname in HOSTS and not p.username and not p.password and p.port in (None,80,443):
            return url
    raise ValueError('没有找到受支持的小红书链接')

def parse_state(html):
    # Replace JavaScript undefined only outside JSON string literals; never execute page code.
    match=re.search(r'window\.__INITIAL_STATE__\s*=\s*',html)
    if not match: raise ValueError('页面没有可读取的笔记状态；需要浏览器访问验证')
    source=html[match.end():].split('</script>',1)[0]
    source=re.sub(r'"(?:\\.|[^"\\])*"|\bundefined\b',lambda m:'null' if m.group()=='undefined' else m.group(),source)
    return json.JSONDecoder().raw_decode(source)[0]

def metadata(note,url):
    note_id=note.get('noteId') or (ID_RE.search(url).group(1) if ID_RE.search(url) else None)
    if not note_id or not re.fullmatch('[a-fA-F0-9]{24}',note_id): raise ValueError('无法验证笔记 ID')
    published=note.get('time')
    if isinstance(published,(int,float)) and published>0:
        published=datetime.fromtimestamp(published/1000 if published>1e11 else published,TZ).isoformat(timespec='seconds')
    else: published=None
    likes=note.get('interactInfo',{}).get('likedCount')
    image=(note.get('imageList') or [{}])[0]
    cover=image.get('urlDefault') or image.get('urlPre') or image.get('url')
    if not cover:
        choices=image.get('infoList') or []
        cover=next((x.get('url') for x in choices if x.get('url')),None)
    streams=note.get('video',{}).get('media',{}).get('stream',{})
    candidates=[]
    for group in streams.values():
        if isinstance(group,list):
            candidates.extend(x for x in group if isinstance(x,dict) and x.get('masterUrl'))
    candidates.sort(key=lambda x:x.get('size') or 10**15)
    media_v2=note.get('video',{}).get('mediaV2') or '{}'
    if isinstance(media_v2,str): media_v2=json.loads(media_v2)
    subtitles=media_v2.get('video',{}).get('subtitles',{})
    choices=(subtitles.get('source') or [])+(subtitles.get('zh-CN') or [])
    subtitle=next((x for x in choices if x.get('url') and x.get('language') in ('zh','zh-CN','zh-Hans')),{})
    duration=note.get('video',{}).get('media',{}).get('video',{}).get('duration')
    return {'schema_version':1,'id':note_id.lower(),'title':note.get('title'),
            'author':note.get('user',{}).get('nickname') or note.get('user',{}).get('nickName'),'published_at':published,
            'likes':None if likes is None else str(likes),'collected_at':now(),
            'source_url':url,'description':note.get('desc') or '',
            'tags':[t['name'] for t in note.get('tagList',[]) if t.get('name')],
            'cover_url':cover,'video_url':candidates[0]['masterUrl'] if candidates else None,
            'duration_seconds':duration,'subtitle_url':subtitle.get('url'),'subtitle_language':subtitle.get('language')}

def inspect_url(text,html_file=None):
    url=input_url(text)
    if html_file:
        html=Path(html_file).read_text(encoding='utf-8')
    else:
        request=Request(url,headers={'User-Agent':'Mozilla/5.0','Referer':'https://www.xiaohongshu.com/'})
        with urlopen(request,timeout=25) as response:
            url=response.url
            if urlparse(url).hostname not in HOSTS: raise ValueError('跳转到了小红书以外的域名')
            raw=response.read(8*1024*1024+1)
            if len(raw)>8*1024*1024: raise ValueError('页面超出大小上限')
            html=raw.decode('utf-8',errors='strict')
    target=ID_RE.search(url)
    if not target: raise ValueError('链接未能跳转到具体笔记；需要同一视频的完整链接')
    state=parse_state(html)
    note=state.get('note',{}).get('noteDetailMap',{}).get(target.group(1),{}).get('note')
    if not note: note=state.get('noteData',{}).get('data',{}).get('noteData')
    if not note: raise ValueError('页面没有目标笔记数据，可能需要登录或正常浏览器访问')
    result=metadata(note,url)
    if result['id']!=target.group(1).lower(): raise ValueError('目标链接与笔记 ID 不一致')
    return result

def srt_transcript(text,duration=None):
    if isinstance(duration,bool) or not isinstance(duration,(int,float)) or not math.isfinite(duration) or duration<=0:
        raise ValueError('缺少有效视频时长，无法验证字幕覆盖；请先取得真实媒体时长')
    def seconds(t):
        h,m,s=t.replace(',','.').split(':')
        if not (0<=int(m)<60 and 0<=float(s)<60): raise ValueError('字幕分钟或秒数超出范围')
        return int(h)*3600+int(m)*60+float(s)
    cues=[]
    for block in re.split(r'\n\s*\n',text.replace('\r\n','\n').strip()):
        lines=block.splitlines()
        i=next((i for i,line in enumerate(lines) if '-->' in line),None)
        if i is None: raise ValueError('字幕不是完整的 SRT 格式')
        match=re.fullmatch(r'(\d\d:\d\d:\d\d[,\.]\d{3})\s*-->\s*(\d\d:\d\d:\d\d[,\.]\d{3})',lines[i])
        if not match or not lines[i+1:]: raise ValueError('字幕时间或正文缺失')
        start,end=match.groups();content='\n'.join(lines[i+1:]).strip()
        if not content or seconds(end)<seconds(start): raise ValueError('字幕段落为空或时间逆序')
        if cues and seconds(start)<seconds(cues[-1][0]): raise ValueError('字幕未按时间排序')
        cues.append((start,end,content))
    if not cues: raise ValueError('字幕为空')
    if duration and (seconds(cues[0][0])>5 or abs(float(duration)-seconds(cues[-1][1]))>5):
        raise ValueError('字幕未覆盖视频首尾，需要核对音频后补全')
    max_gap=max((seconds(cues[i][0])-seconds(cues[i-1][1]) for i in range(1,len(cues))),default=0)
    transcript='\n\n'.join(f'**[{s.replace(chr(44),chr(46))}–{e.replace(chr(44),chr(46))}]**\n\n{t}' for s,e,t in cues)
    return transcript,{'max_gap_seconds':round(max(0,max_gap),3),'requires_content_review':max_gap>10,'cue_count':len(cues),'start_seconds':seconds(cues[0][0]),'end_seconds':seconds(cues[-1][1]),'characters':sum(len(c[2]) for c in cues)}

def cover_extension(path):
    data=Path(path).read_bytes()[:16]
    if data.startswith(b'\xff\xd8\xff'): ext='.jpg'
    elif data.startswith(b'\x89PNG\r\n\x1a\n'): ext='.png'
    elif data.startswith(b'RIFF') and data[8:12]==b'WEBP': ext='.webp'
    else: raise ValueError('封面不是支持的 JPEG、PNG 或 WebP；请先验证/转换图片')
    if shutil.which('sips'):
        with tempfile.TemporaryDirectory(prefix='xhs-image-check-') as temp:
            decoded=Path(temp)/'decoded.png'
            result=subprocess.run(['sips','-s','format','png',str(Path(path).resolve()),'--out',str(decoded)],capture_output=True,timeout=30)
            if result.returncode or not decoded.is_file() or decoded.stat().st_size<32:
                raise ValueError('封面图片无法完整解码')
    else:
        try:
            from PIL import Image
        except ImportError as exc: raise ValueError('需要 sips 或 Pillow 验证本地封面') from exc
        try:
            with Image.open(path) as im:
                im.load()
                if min(im.size)<=0: raise ValueError('图片尺寸为空')
        except Exception as exc: raise ValueError('封面图片无法完整解码') from exc
    return ext

def display(value):
    return '未获取' if value is None or not str(value).strip() else str(value)

def readable_filename(title,author):
    def clean(value):
        return re.sub(r'[\x00-\x1f/\\:*?"<>|]', ' ',str(value)).strip(' .')
    stem=clean(title)+' — '+clean(author or '作者未获取')
    stem=stem.encode('utf-8')[:230].decode('utf-8',errors='ignore').rstrip(' .')
    return (stem or '未命名素材')+'.md'

def find_existing_note(root,note_id):
    matches=[]
    for path in (Path(root).resolve()/'素材笔记').rglob('*.md'):
        text=path.read_text(encoding='utf-8')
        if not text.startswith('---\n'): continue
        parts=text.split('\n---',1)
        if len(parts)<2: continue
        front=yaml.safe_load(parts[0][4:]) or {}
        if not isinstance(front,dict): continue
        if str(front.get('note_id',''))==note_id and front.get('platform','小红书')=='小红书': matches.append(path)
    if len(matches)>1: raise ValueError('发现多份相同平台 ID 的笔记，请先核对')
    return matches[0] if matches else None

def save_note(data,transcript,cover,root,method='音频自动转写（未人工逐字校对）'):
    note_id=data.get('id','')
    if not re.fullmatch('[a-f0-9]{24}',note_id): raise ValueError('笔记 ID 无效')
    if not transcript.strip(): raise ValueError('没有音频文字稿，不能写成已收纳笔记')
    if '\ufffd' in transcript or '\ufffd' in (data.get('title') or ''): raise ValueError('发现编码替换字符')
    if not str(data.get('title') or '').strip() or not data.get('source_url'): raise ValueError('缺少标题或原链接')
    source=input_url(data['source_url'])
    source_id=ID_RE.search(source)
    if not source_id or source_id.group(1).lower()!=note_id: raise ValueError('原链接与笔记 ID 不一致')
    if not cover or not Path(cover).is_file(): raise ValueError('缺少本地封面')
    ext=cover_extension(cover)
    root=resolve_root(root)
    notes=root/'素材笔记'; images=root/'封面附件'; index=root/'索引'
    for folder in (notes,images,index): folder.mkdir(parents=True,exist_ok=True)
    existing=find_existing_note(root,note_id)
    if existing: raise FileExistsError(f'该笔记已存在，保留原文件：{existing}')
    dest=notes/readable_filename(data['title'],data.get('author'))
    if dest.exists(): dest=notes/(dest.stem.encode('utf-8')[:200].decode('utf-8',errors='ignore').rstrip(' .')+' — '+note_id+'.md')
    if dest.exists(): raise FileExistsError(f'该笔记已存在，保留原文件：{dest}')
    image_path=images/f'{note_id}{ext}'
    if image_path.exists(): raise FileExistsError(f'封面已存在，请检查上次运行：{image_path}')
    missing=[key for key in ('published_at','likes','author') if data.get(key) is None or not str(data.get(key)).strip() or data.get(key)=='未获取']
    if 'published_at' not in missing:
        try: datetime.fromisoformat(data['published_at'])
        except (ValueError,TypeError) as exc: raise ValueError('发布时间不是 ISO 日期/时间') from exc
    if data.get('transcript_review_required'): missing.append('字幕内部空档待核对')
    status='partial' if missing else 'complete'
    category=data.get('主分类','待分类')
    if category not in settings(root)['categories']: raise ValueError('主分类不在当前素材库的分类设置内')
    serials=[]
    for path in notes.glob('*.md'):
        text=path.read_text(encoding='utf-8')
        if text.startswith('---\n') and '\n---' in text:
            props=yaml.safe_load(text.split('\n---',1)[0][4:]) or {}
            if isinstance(props,dict):
                match=re.fullmatch(r'S(\d+)',str(props.get('素材编号','')))
                if match: serials.append(int(match.group(1)))
    serial=f'S{max(serials,default=0)+1:04d}'
    front={'schema_version':1,'platform':'小红书','note_id':note_id,'status':status,'title':data['title'],
           'author':data.get('author'),'published_at':data.get('published_at'),
           'likes_snapshot':data.get('likes'),'collected_at':data.get('collected_at') or now(),
           'source_url':data['source_url'],'tags':data.get('tags',[]),'transcript_method':method}
    front.update({'素材编号':serial,'主分类':category,'子主题':data.get('子主题',''),'收藏用途':data.get('收藏用途',[]),'内容形式':data.get('内容形式',[]),'分类依据':data.get('分类依据','待阅读全文并按用户规则分类'),'本次分析':False,'分析批次':[],'aliases':[serial]})
    if data.get('share_url'): front['share_url']=data['share_url']
    # JSON scalar syntax is valid YAML; Chinese remains literal UTF-8.
    yaml_text='\n'.join(f'{key}: {json.dumps(value,ensure_ascii=False)}' for key,value in front.items())
    title=data['title'].replace('\n',' ')
    body=f'''---
{yaml_text}
---

# {title}

![封面](../封面附件/{note_id}{ext})

| 信息 | 内容 |
| --- | --- |
| 备用编号 | {serial} |
| 主分类 | {category} |
| 作者 | {display(data.get('author'))} |
| 发布时间 | {display(data.get('published_at'))} |
| 点赞数（采集时） | {display(data.get('likes'))} |
| 采集时间 | {front['collected_at']} |
| 原始链接 | [打开原视频]({data['source_url']}) |
| 分享链接 | {('[原始分享短链]('+data['share_url']+')') if data.get('share_url') else '见原始链接'} |
| 收纳状态 | {'字段待补充：'+', '.join(missing) if missing else '资料已获取'} |

## 作者发布的笔记文案

{data.get('description') or '未提供'}

## 视频音频文字稿

转写方式：{method}

{transcript.strip()}

## 我的参考备注

'''
    if '\ufffd' in body: raise ValueError('笔记包含无法解码的字符')
    with tempfile.TemporaryDirectory(prefix='.staging-',dir=root) as temp:
        stage=Path(temp); staged_note=stage/'note.md'; staged_image=stage/('cover'+ext)
        shutil.copyfile(cover,staged_image)
        staged_note.write_text(body,encoding='utf-8',newline='\n')
        if staged_note.read_text(encoding='utf-8')!=body: raise ValueError('UTF-8 回读不一致')
        created=[]
        try:
            # Hard links commit already-verified bytes without overwriting existing files.
            os.link(staged_image,image_path); created.append(image_path)
            os.link(staged_note,dest); created.append(dest)
        except Exception:
            for path in reversed(created): path.unlink(missing_ok=True)
            raise
    try: rebuild_index(root)
    except OSError as exc:
        print(f'笔记和封面已保存，但索引更新失败，需要重建：{exc}')
    return dest

def rebuild_index(root):
    root=Path(root).resolve()
    rows=['# 小红书素材索引','','按内容查找：搜索整个“素材笔记”文件夹中的文字稿；主题也记录在每篇笔记的 tags 中。','']
    for path in sorted((root/'素材笔记').glob('*.md')):
        text=path.read_text(encoding='utf-8')
        title=next((line[2:] for line in text.splitlines() if line.startswith('# ')),path.stem)
        rows.append(f'- [{title.replace(chr(91),"（").replace(chr(93),"）") }](../素材笔记/{quote(path.name)})')
    index=root/'索引'/'素材索引.md'
    tmp=index.with_suffix('.tmp')
    tmp.write_text('\n'.join(rows)+'\n',encoding='utf-8'); tmp.replace(index)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('inspect'); p.add_argument('input'); p.add_argument('--html'); p.add_argument('--out',required=True)
    p=sub.add_parser('save'); p.add_argument('--metadata',required=True); p.add_argument('--transcript',required=True); p.add_argument('--cover',required=True); p.add_argument('--root',type=Path,default=DEFAULT_ROOT); p.add_argument('--method',default='音频自动转写（未人工逐字校对）')
    args=parser.parse_args()
    if args.command=='inspect':
        result=inspect_url(args.input,args.html)
        Path(args.out).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print('目标笔记元数据已写入：'+args.out)
    else:
        data=json.loads(Path(args.metadata).read_text(encoding='utf-8'))
        transcript=Path(args.transcript).read_text(encoding='utf-8')
        print(save_note(data,transcript,args.cover,args.root,args.method))

if __name__=='__main__': main()
