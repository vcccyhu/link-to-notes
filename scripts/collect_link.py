"""Collect a Xiaohongshu share link using its mobile page and bound source subtitles.
No account cookies, global network changes, ASR model, or retained media required.
"""
import argparse
import json
import yaml
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import urlparse, urljoin
from library_config import resolve_root, classification_due
from collect import input_url, inspect_url, srt_transcript, save_note, find_existing_note, DEFAULT_ROOT, HOSTS

MOBILE_UA='Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Version/18.0 Mobile/15E148 Safari/604.1'

class Fetcher:
    def __init__(self,interface=None,cache=None):
        self.interface=interface
        self.cache=cache or {}

    def resolve(self,host):
        if self.cache.get(host): return self.cache[host][0]
        resolvers=[f'https://cloudflare-dns.com/dns-query?name={host}&type=A',f'https://dns.google/resolve?name={host}&type=A']
        for address in resolvers:
            r=subprocess.run(['curl','-sS','--fail','--max-time','15','-H','accept: application/dns-json',address],capture_output=True,text=True)
            if r.returncode: continue
            try: ips=[a['data'] for a in json.loads(r.stdout).get('Answer',[]) if a['type']==1]
            except (ValueError,KeyError): continue
            if ips:
                self.cache[host]=ips
                return ips[0]
        raise RuntimeError(f'无法解析 {host} 的真实地址')

    def get(self,url,dest,timeout=30):
        p=urlparse(url)
        host=p.hostname or ''
        if p.scheme not in ('http','https') or not (host in HOSTS or host.endswith('.xhscdn.com') or host=='ci.xiaohongshu.com'):
            raise ValueError('拒绝非小红书页面/媒体地址')
        if p.username or p.password: raise ValueError('地址不能含登录凭据')
        args=['curl','-sS','--max-time',str(timeout),'-A',MOBILE_UA,'-e','https://www.xiaohongshu.com/','-o',str(dest),'-w','%{http_code}\n%{redirect_url}']
        if self.interface:
            ip=self.resolve(host)
            args.extend(['--interface',self.interface,'--resolve',f'{host}:{p.port or (443 if p.scheme=="https" else 80)}:{ip}'])
        r=subprocess.run([*args,url],capture_output=True,text=True)
        if r.returncode: raise RuntimeError(f'{host} 请求失败：{r.stderr.strip()}')
        status,_,redirect=r.stdout.partition('\n')
        if status not in ('200','206','301','302','303','307','308'):
            raise RuntimeError(f'{host} HTTP {status}')
        return int(status),redirect

    def page(self,url,dest):
        for _ in range(6):
            if urlparse(url).hostname not in HOSTS: raise ValueError('页面跳转超出小红书域名')
            status,redirect=self.get(url,dest)
            if status in (200,206): return url
            if not redirect: raise ValueError('重定向缺少目标地址')
            url=urljoin(url,redirect)
        raise ValueError('页面重定向过多')

def convert_cover(source,dest):
    from PIL import Image, ImageOps
    with Image.open(source) as image:
        image=ImageOps.exif_transpose(image)
        image.thumbnail((720,720))
        image.convert('RGB').save(dest,format='JPEG',quality=78)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('share_text');p.add_argument('--root',type=Path,default=DEFAULT_ROOT)
    p.add_argument('--interface',help='仅该请求使用指定网卡；不更改系统设置，例如本机 en0')
    p.add_argument('--dns-cache',type=Path,help='可选：本次任务已验证的临时 DNS JSON；不要长期固定 IP')
    args=p.parse_args()
    args.root=resolve_root(args.root)
    cache=json.loads(args.dns_cache.read_text()) if args.dns_cache else {}
    fetch=Fetcher(args.interface,cache)
    with tempfile.TemporaryDirectory(prefix='xhs-collect-') as temp:
        temp=Path(temp);page=temp/'page.html';url=fetch.page(input_url(args.share_text),page)
        m=inspect_url(url,page)
        m['share_url']=input_url(args.share_text)
        existing=find_existing_note(args.root,m['id'])
        if existing:
            print(json.dumps({'status':'already_saved','path':str(existing.resolve())},ensure_ascii=False));return
        if not m.get('subtitle_url') or m.get('subtitle_language') not in ('zh','zh-CN','zh-Hans'):
            raise ValueError('该视频没有可用的中文平台字幕，需要音频转写；未生成成品笔记')
        if not m.get('cover_url'): raise ValueError('没有取得封面')
        subtitle=temp/'source.srt';status,_=fetch.get(m['subtitle_url'],subtitle)
        if status!=200: raise ValueError('字幕不是直接可读资源')
        transcript,report=srt_transcript(subtitle.read_text(encoding='utf-8-sig'),m.get('duration_seconds'))
        m['transcript_review_required']=report['requires_content_review']
        original=temp/'cover-original';status,_=fetch.get(m['cover_url'],original)
        if status!=200: raise ValueError('封面不是直接可读资源')
        cover=temp/'cover.jpg'
        convert_cover(original,cover)
        method='小红书视频绑定的中文 source 字幕（自动识别，未逐字人工校对）'
        proof=f'字幕来源：该视频页面绑定的中文平台字幕。共 {report["cue_count"]} 段，约 {report["characters"]} 字符；起止 {report["start_seconds"]:.3f}–{report["end_seconds"]:.3f} 秒；平台视频时长 {m.get("duration_seconds")} 秒。最大内部空档 {report['max_gap_seconds']:.3f} 秒。已检查格式、顺序与首尾覆盖；未经逐字人工校对，可能有同音字错误。\n\n'
        path=save_note(m,proof+transcript,cover,args.root,method)
        saved=yaml.safe_load(path.read_text(encoding='utf-8').split('---',2)[1])
        print(json.dumps({'status':'partial' if saved['status']=='partial' else 'saved','classification_review_due':classification_due(args.root),'path':str(path),'title':m['title'],'author':m['author'],'published_at':m['published_at'],'likes':m['likes'],**report},ensure_ascii=False))

if __name__=='__main__':
    try: main()
    except (ValueError,RuntimeError,OSError) as exc:
        import sys
        print(json.dumps({'status':'failed','reason':str(exc),'next_step':'按 references/workflow.md 判断是否需浏览器访问或音频转写；不得将失败报成成功'},ensure_ascii=False),file=sys.stderr)
        sys.exit(2)
