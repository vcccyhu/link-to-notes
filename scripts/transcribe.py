"""Local CPU ASR; model downloads live only in a task-owned temporary directory.
Run: uv run --no-project --with faster-whisper python transcribe.py AUDIO --out TEXT
"""
import argparse
import json
from pathlib import Path
import tempfile
import subprocess
import wave
import time

def prepare_audio(source,task_dir):
    import numpy as np
    pcm=Path(task_dir)/'normalized.wav'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-i',str(source),'-vn','-ac','1','-ar','16000','-c:a','pcm_s16le','-y',str(pcm)],check=True)
    with wave.open(str(pcm),'rb') as wav:
        if (wav.getnchannels(),wav.getsampwidth(),wav.getframerate())!=(1,2,16000):
            raise ValueError('音频标准化失败')
        return np.frombuffer(wav.readframes(wav.getnframes()),dtype='<i2').astype(np.float32)/32768.0

def timestamp(seconds):
    seconds=int(seconds)
    return f'{seconds//60:02}:{seconds%60:02}'

def build_parser():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('audio',type=Path); p.add_argument('--out',type=Path,required=True)
    p.add_argument('--model',default='base',choices=['base','small'])
    p.add_argument('--language',default='auto',help='auto 自动识别；也可指定 en、zh 等语言代码')
    return p

def main():
    started=time.monotonic()
    p=build_parser()
    args=p.parse_args()
    if not args.audio.is_file(): p.error('音频文件不存在')
    from faster_whisper import WhisperModel
    with tempfile.TemporaryDirectory(prefix='xhs-asr-') as model_dir:
        samples=prepare_audio(args.audio,model_dir)
        model=WhisperModel(args.model,device='cpu',compute_type='int8',cpu_threads=2,download_root=model_dir)
        inference_started=time.monotonic()
        segments,info=model.transcribe(samples,language=None if args.language=='auto' else args.language,beam_size=5,vad_filter=True)
        rows=[{'start':s.start,'end':s.end,'text':s.text.strip()} for s in segments if s.text.strip()]
        if not rows: raise ValueError('没有识别到语音，不能提交空文字稿')
        args.out.write_text('\n\n'.join(f'[{timestamp(s["start"])}–{timestamp(s["end"])}] {s["text"]}' for s in rows)+'\n',encoding='utf-8')
        report={'model':args.model,'language':info.language,'language_probability':info.language_probability,'requested_language':args.language,'audio_duration':info.duration,
                'inference_seconds':round(time.monotonic()-inference_started,3),'total_seconds':round(time.monotonic()-started,3),
                'last_segment_end':rows[-1]['end'],'segments':rows}
        args.out.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'本地转写完成；模型临时目录已清理：{args.out}')

if __name__=='__main__': main()
