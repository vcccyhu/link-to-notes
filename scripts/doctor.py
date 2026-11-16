"""Report environment readiness without installing anything or accessing accounts."""
import sys,shutil,json,importlib.util
from library_config import resolve_root
checks={'python_3_10_or_newer':sys.version_info>=(3,10),'curl':bool(shutil.which('curl')),
 'pillow':importlib.util.find_spec('PIL') is not None,'pyyaml':importlib.util.find_spec('yaml') is not None,
 'ffmpeg_optional_for_asr':bool(shutil.which('ffmpeg')),'ffprobe_optional_for_asr':bool(shutil.which('ffprobe')),
 'faster_whisper_optional_for_asr':importlib.util.find_spec('faster_whisper') is not None}
try: checks['library_root']=str(resolve_root())
except ValueError:checks['library_root']='尚未设置；可在首次使用时设置'
print(json.dumps(checks,ensure_ascii=False,indent=2))
sys.exit(0 if all(checks[x] for x in ['python_3_10_or_newer','curl','pillow','pyyaml']) else 1)
