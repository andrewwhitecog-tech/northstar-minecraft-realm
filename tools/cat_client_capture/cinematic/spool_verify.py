"""Postclosure raw/index integrity only. Never a visual or real-time FPS acceptance."""
from pathlib import Path
import json,math,zlib

def verify_spool(base,frames,fps,start,end,*,frame_bytes=1280*720*4,expected_mode="OFFLINE_NATIVE_CINEMATIC"):
 if expected_mode not in ("OFFLINE_NATIVE_CINEMATIC","OFFLINE_NATIVE_ANIMATED_SUBJECT"):raise ValueError("explicit supported spool mode required")
 base=Path(base);raw=base.with_name(base.name+'.rgba');index=base.with_name(base.name+'.frames.jsonl')
 if not(2<=frames<=600 and 1<=fps<=60 and 0<frame_bytes<=1280*720*4):raise ValueError('finite raw cap')
 if len(start)!=5 or len(end)!=5 or not all(math.isfinite(x)for x in start+end):raise ValueError('pose bounds')
 if expected_mode=="OFFLINE_NATIVE_ANIMATED_SUBJECT" and any(a!=b for a,b in zip(start,end)):raise ValueError("animated subject requires exact fixed camera pose")
 if expected_mode=="OFFLINE_NATIVE_CINEMATIC" and math.dist(start[:3],end[:3])<.01:raise ValueError('real translating route required')
 for p in [raw,index]:
  if not p.is_file()or any(q.is_symlink()or q.is_junction()for q in[p,*p.parents]):raise ValueError('missing/linked spool')
 if raw.stat().st_size!=frames*frame_bytes or index.stat().st_size>frames*2048:raise ValueError('exact bounded spool length')
 last=-1
 with raw.open('rb')as r,index.open(encoding='utf-8')as idx:
  for i in range(frames):
   line=idx.readline(2049)
   if len(line)>2048 or not line.endswith('\n'):raise ValueError('bounded complete index line')
   row=json.loads(line);render=row.get('renderId');data=r.read(frame_bytes)
   if type(render)is not int or render<=last:raise ValueError('duplicate/reordered actual render identity')
   if row.get('mode')!=expected_mode or row.get('index')!=i or row.get('offset')!=i*frame_bytes or row.get('bytes')!=frame_bytes:raise ValueError('index order/offset/size')
   if row.get('crc32')!=zlib.crc32(data):raise ValueError('actual raw CRC mismatch')
   k=i/(frames-1);e=k*k*(3-2*k);delta=(end[3]-start[3]+180)%360-180
   expected=[start[j]+(end[j]-start[j])*e for j in range(5)];expected[3]=start[3]+delta*e;pose=row.get('pose')
   if not isinstance(pose,list)or len(pose)!=5 or not all(isinstance(x,(int,float))and math.isfinite(x)for x in pose)or any(abs(a-b)>1e-4 for a,b in zip(pose,expected)):raise ValueError('authored index pose mismatch')
   last=render
  if idx.read(1)or r.read(1):raise ValueError('extra index/raw payload')
 return {'mode':expected_mode,'frames':frames,'fps':fps,'outputSeconds':frames/fps,'rawBytes':frames*frame_bytes,'crcVerifiedFrames':frames,'contiguousIndices':True,'increasingRenderIdentities':True,'authoredPoseVerifiedFrames':frames,'scope':'raw/index integrity; native rendering and pixels require actual runtime and Root QC','humanVisualAccepted':False}
