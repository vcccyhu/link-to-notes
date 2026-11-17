"""Reusable local runtime. Setup is explicit; check never installs or changes security settings."""
import argparse,importlib.util,json,os,shutil,socket,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def emit(stage,**data):
 print(json.dumps(dict(stage=stage,**data),ensure_ascii=False,indent=2))

def write_probe(folder):
 try:
  with tempfile.NamedTemporaryFile(prefix='.xhs-write-check-',dir=str(folder),delete=True) as f:
   f.write(b'check');f.flush()
  return {'ok':True}
 except OSError as e:return {'ok':False,'error_type':type(e).__name__}

def validate_interface(value):
 if value not in [name for _,name in socket.if_nameindex()]:
  raise ValueError('指定网卡不在本机接口列表中；不要复制其他电脑的网卡名')
 return value

def command_args(script,args,interface):
 if script=='collect_link' and interface and '--interface' not in args:return args+['--interface',interface]
 return args

NO_PROXY_DOMAINS=['xiaohongshu.com','.xiaohongshu.com','xhslink.cn','xhslink.com','.xhscdn.com']

def collection_env(script,data):
 env=os.environ.copy()
 if script!='collect_link' or not data.get('no_proxy_domains'):return env
 domains=data['no_proxy_domains']
 if not isinstance(domains,list) or any(d not in NO_PROXY_DOMAINS for d in domains):
  raise ValueError('仅允许保存小红书相关域名的本机代理例外；不能使用通配符或其他站点')
 existing=env.get('NO_PROXY') or env.get('no_proxy','')
 value=','.join(dict.fromkeys([x for x in existing.split(',') if x]+domains))
 env['NO_PROXY']=value;env['no_proxy']=value
 return env

def supported_python():
 candidates=[sys.executable]+[shutil.which(n) for n in ['python3.12','python3.11','python3.10','python3','python']]
 candidates += [str(Path.home()/'.local/bin'/n) for n in ['python3.12','python3.11','python3.10']]
 for candidate in dict.fromkeys(x for x in candidates if x):
  try:
   r=subprocess.run([candidate,'-c','import sys;sys.exit(0 if sys.version_info >= (3,10) else 1)'],capture_output=True,timeout=10)
   if r.returncode==0:return candidate
  except (OSError,subprocess.TimeoutExpired):pass
 raise ValueError('未找到Python 3.10以上；先从官方渠道安装Python，再运行首次设置')

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--env',type=Path,default=ROOT/'.venv')
 p.add_argument('--setup',action='store_true')
 p.add_argument('--asr',action='store_true',help='仅setup时额外安装转写依赖；不安装ffmpeg')
 p.add_argument('--check',action='store_true')
 p.add_argument('--remember-interface',help='保存本机已核实可用接口；不修改系统网络')
 p.add_argument('--remember-no-proxy',action='store_true',help='仅在本机已核实并获准直连时保存小红书域名代理例外')
 p.add_argument('--run',choices=['doctor','collect_link','library_config','transcribe'])
 p.add_argument('args',nargs=argparse.REMAINDER)
 a=p.parse_args();env=a.env.expanduser().resolve();py=env/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
 if a.asr and not a.setup:p.error('--asr需要--setup')
 if a.setup:
  if not py.is_file():subprocess.run([supported_python(),'-m','venv',str(env)],check=True)
  uv=shutil.which('uv')
  install=[uv,'pip','install','--python',str(py)] if uv else [str(py),'-m','pip','install']
  subprocess.run(install+['-r',str(ROOT/'requirements.txt')],check=True)
  if a.asr:subprocess.run(install+['-r',str(ROOT/'requirements-asr.txt')],check=True)
 if not py.is_file():
  emit('runtime_missing',next_step='使用可用Python运行 scripts/bootstrap.py --setup；安装只需首次执行或依赖损坏时修复');return 2
 probe=subprocess.run([str(py),'-c','import sys,PIL,yaml;assert sys.version_info >= (3,10)'],capture_output=True)
 if probe.returncode:
  emit('runtime_invalid',python=str(py),next_step='运行 scripts/bootstrap.py --setup 修复依赖，不要改用随机系统Python');return 2
 pref=env/'xhs-network.json';data=json.loads(pref.read_text(encoding='utf-8')) if pref.is_file() else {}
 if a.remember_interface:
  data['interface']=validate_interface(a.remember_interface)
 if a.remember_no_proxy:data['no_proxy_domains']=NO_PROXY_DOMAINS.copy()
 if a.remember_interface or a.remember_no_proxy:
  pref.write_text(json.dumps(data,ensure_ascii=False)+'\n',encoding='utf-8')
 interface=data.get('interface')
 if interface:validate_interface(interface)
 if a.run:
  args=a.args[1:] if a.args[:1]==['--'] else a.args
  return subprocess.run([str(py),str(ROOT/'scripts'/(a.run+'.py'))]+command_args(a.run,args,interface),env=collection_env(a.run,data)).returncode
 cfg=Path(os.environ.get('XHS_LIBRARY_CONFIG',str(Path.home()/'.config/xiaohongshu-video-library/config.json'))).expanduser()
 value=os.environ.get('XHS_LIBRARY_ROOT')
 if not value and cfg.is_file():value=json.loads(cfg.read_text(encoding='utf-8')).get('root')
 write=write_probe(Path(value).expanduser()) if value else {'ok':False,'error_type':'library_not_configured'}
 emit('ready' if write['ok'] else 'library_check_failed',python=str(py),library_root=value,write_probe=write,
      interface=interface,no_proxy_domains=data.get('no_proxy_domains',[]),network='未实测；有访问权限不代表DNS/TLS可用',skill_version=(ROOT/'VERSION').read_text().strip())
 return 0 if write['ok'] else 2

if __name__=='__main__':
 try:sys.exit(main())
 except (OSError,ValueError,subprocess.CalledProcessError) as e:
  emit('setup_or_runtime_failed',error_type=type(e).__name__,next_step='检查Python、安装联网、配置及本机网卡；不得将网络错误直接归因为权限不足');sys.exit(2)
