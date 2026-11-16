"""User-owned library setup; no machine-specific defaults or authentication data."""
import argparse,json,os,shutil
from pathlib import Path

PRESET=['自媒体方法','AI辅助创作','爆款拆解','对标作品','账号运营','商业变现','待分类']

def config_file():
 return Path(os.environ.get('XHS_LIBRARY_CONFIG',str(Path.home()/'.config'/'xiaohongshu-video-library'/'config.json'))).expanduser()

def resolve_root(explicit=None,config_path=None):
 value=explicit or os.environ.get('XHS_LIBRARY_ROOT')
 if not value:
  path=Path(config_path) if config_path else config_file()
  if path.is_file(): value=json.loads(path.read_text(encoding='utf-8')).get('root')
 if not value: raise ValueError('尚未设置素材库位置：请先运行 library_config.py init --root 保存文件夹，或显式传入 --root')
 return Path(value).expanduser().resolve()

def settings(root):
 p=Path(root)/'索引/收纳设置.json'
 if p.is_file():
  result=json.loads(p.read_text(encoding='utf-8'))
  cats=result.get('categories')
  if not isinstance(cats,list) or not cats or any(not isinstance(c,str) or not c.strip() for c in cats):
   raise ValueError('分类设置无效，请检查索引/收纳设置.json')
  return result
 return {'schema_version':1,'categories':['待分类'],'classification_mode':'deferred','review_after':10}

def initialize(root,categories=None,config_path=None):
 root=Path(root).expanduser().resolve()
 cats=list(dict.fromkeys([c.strip() for c in (categories or []) if c.strip()]+['待分类']))
 for c in cats:
  if len(c)>80 or any(ord(x)<32 for x in c):raise ValueError('分类名称应为80字以内的单行文本')
 for name in ['素材笔记','封面附件','索引','分析清单','测试记录']:(root/name).mkdir(parents=True,exist_ok=True)
 assets=Path(__file__).resolve().parents[1]/'assets/vault'
 for src in assets.rglob('*'):
  if src.is_file():
   dst=root/src.relative_to(assets);dst.parent.mkdir(parents=True,exist_ok=True)
   if not dst.exists():shutil.copyfile(src,dst)
 p=root/'索引/收纳设置.json'
 if not p.exists():
  p.write_text(json.dumps({'schema_version':1,'categories':cats,'classification_mode':'custom' if len(cats)>1 else 'deferred','review_after':10},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 rules=root/'索引/分类规则.md'
 if not rules.exists():
  rules.write_text('# 素材分类规则\n\n可用主分类：'+ '、'.join(settings(root)['categories'])+'。\n\n每条素材只保存一份，只选一个主分类。按全文主线及收藏目的判断；作者、形式、用途分别记录。无法判断或不在现有类别内时归待分类，写明原因。\n\n新用户可以先待分类；积累10条时建议复核。先提出分类方案，用户确认后再批量修改，不自动搬动、复制或重写用户备注。\n',encoding='utf-8')
 cfg=Path(config_path) if config_path else config_file();cfg.parent.mkdir(parents=True,exist_ok=True)
 cfg.write_text(json.dumps({'root':str(root)},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 return root

def classification_due(root):
 cfg=settings(root)
 return cfg.get('classification_mode')=='deferred' and len(list((Path(root)/'素材笔记').glob('*.md')))>=cfg.get('review_after',10)

def main():
 p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
 init=sub.add_parser('init');init.add_argument('--root',required=True,type=Path);init.add_argument('--categories',nargs='*');init.add_argument('--preset',choices=['creator']);init.add_argument('--config',type=Path)
 sub.add_parser('show')
 a=p.parse_args()
 try:
  if a.command=='init':
   if a.preset and a.categories:p.error('--preset 与 --categories 只能选一个')
   root=initialize(a.root,PRESET if a.preset else a.categories,a.config)
  else:root=resolve_root()
  print(json.dumps({'root':str(root),'settings':settings(root)},ensure_ascii=False,indent=2))
 except (ValueError,OSError) as e:p.exit(2,str(e)+'\n')
if __name__=='__main__':main()
