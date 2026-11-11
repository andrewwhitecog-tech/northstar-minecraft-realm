"""Original finite FFmpeg QC/conform. Importing this module performs no media work."""
import hashlib,json,math,os,statistics,subprocess,time
from pathlib import Path
from private_github import GuardError,require,digest
CROP='crop=trunc(ih*9/16/2)*2:ih:(iw-trunc(ih*9/16/2)*2)/2:0'
START_FRAME,END_FRAME,SOURCE_FRAME,TOTAL_FRAMES=878,942,83,1200
SOURCE_START,SOURCE_DURATION=83/30,64/30
COS=[[math.cos((2*x+1)*u*math.pi/64) for x in range(32)] for u in range(8)]
def source_window():
 # One canonical decoded-frame selector for source QC and final conform. No input seeking.
 return 'fps=30,trim=start_frame=83:end_frame=147,setpts=PTS-STARTPTS,'+CROP
def signature(frame):
 rows=[[sum(frame[y*32+x]*COS[u][x] for x in range(32)) for y in range(32)] for u in range(8)]
 values=[sum(rows[u][y]*COS[v][y] for y in range(32)) for v in range(8) for u in range(8) if (u,v)!=(0,0)];med=statistics.median(values)
 return sum(1<<i for i,value in enumerate(values) if value>med)
def fingerprints(frames):return [(signature(f),f) for f in frames]
def reuse(samples,other):
 hits=[]
 for i,(h,a) in enumerate(samples):
  for j,(g,b) in enumerate(other):
   if (h^g).bit_count()<=8 and sum(abs(x-y) for x,y in zip(a,b))/1024<=12:
    hits.append({'time':i/4,'comparison_time':j/4});break
 return {'estimated_seconds':len(hits)/4,'sample_times':hits,'method':'4fps32x32 grayscale;63bit DCT pHash distance<=8 plus pixelMAE<=12; estimate only'}
class Media:
 def __init__(self,work):self.work=Path(work);self.out=self.work/'out';self.out.mkdir();self.start=time.monotonic();self.commands=[]
 def run(self,exe,args,label,binary=False,timeout=420):
  remaining=1200-(time.monotonic()-self.start);require(remaining>1,'MEDIA_DEADLINE')
  # Never give ffmpeg GitHub credentials, job-control tokens or caller-supplied command strings.
  env={k:os.environ[k] for k in ('PATH','LANG','LC_ALL','TMPDIR') if k in os.environ}
  env.update({k:'1' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')})
  try:r=subprocess.run([exe,*args],cwd=self.work,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=min(timeout,remaining))
  except subprocess.TimeoutExpired:raise GuardError('MEDIA_COMMAND_TIMEOUT') from None
  except Exception:raise GuardError('MEDIA_COMMAND_START') from None
  (self.out/(label+'.stderr.txt')).write_bytes(r.stderr);self.commands.append({'tool':exe,'label':label,'returncode':r.returncode})
  require(r.returncode==0,'MEDIA_COMMAND_NONZERO');return r.stdout if binary else r.stdout.decode('utf-8','replace')
 def ff(self,args,label,binary=False):return self.run('ffmpeg',['-hide_banner','-nostdin','-threads','1','-filter_threads','1','-filter_complex_threads','1',*args],label,binary)
 def probe(self,p,label):
  try:r=json.loads(self.run('ffprobe',['-v','error','-threads','1','-show_format','-show_streams','-of','json',str(p)],label))
  except GuardError:raise
  except Exception:raise GuardError('MEDIA_PROBE_JSON') from None
  return r
 def raw(self,p,label,start=None,duration=None,crop=False,window=False):
  require(not window or (start is None and duration is None),'CANONICAL_WINDOW_NO_SEEK')
  args=['-v','error']
  if start is not None:args+=['-ss',str(start)]
  args+=['-i',str(p)]
  if duration is not None:args+=['-t',str(duration)]
  vf=(source_window()+',' if window else (CROP+',' if crop else ''))+'fps=4,scale=32:32:flags=area,format=gray'
  b=self.ff(args+['-vf',vf,'-an','-f','rawvideo','pipe:1'],label,True);require(len(b)%1024==0,'ANALYSIS_FRAME_LENGTH')
  return [b[i:i+1024] for i in range(0,len(b),1024)]
 def images(self,p,frames,prefix,start=None,crop=False,window=False):
  require(not window or start is None,'CANONICAL_WINDOW_NO_SEEK')
  frames=sorted(set(frames));args=['-v','error']
  if start is not None:args+=['-ss',str(start)]
  args+=['-i',str(p)];vf=(source_window()+',' if window else (CROP+',' if crop else '')+'fps=30,')+'scale=540:960:flags=lanczos,select='+'+'.join('eq(n\\,'+str(n)+')' for n in frames)
  self.ff(args+['-vf',vf,'-fps_mode','vfr','-threads','1',str(Path('out')/(prefix+'_%02d.png'))],prefix)
  paths=sorted(self.out.glob(prefix+'_*.png'));require(len(paths)==len(frames),'REVIEW_FRAME_COUNT')
  return [{'frame':n,'seconds':(SOURCE_START if window else (start or 0))+n/30,'file':p.name,**({'source_frame':SOURCE_FRAME+n} if window else {})} for n,p in zip(frames,paths)]
 def audio(self,p,prefix):
  self.ff(['-v','info','-i',str(p),'-vn','-af','ebur128=peak=true:framelog=verbose','-f','null','-'],prefix+'_loudness')
  self.ff(['-v','error','-i',str(p),'-filter_complex','[0:a]showwavespic=s=1600x360:colors=gold:split_channels=1[wave]','-map','[wave]','-frames:v','1','-threads','1','out/'+prefix+'_waveform.png'],prefix+'_waveform')
  audio=Path('out')/(prefix+'_audio.m4a');self.ff(['-v','error','-i',str(p),'-map','0:a:0','-c','copy','-vn',str(audio)],prefix+'_audio_extract')
  h=self.ff(['-v','error','-i',str(p),'-map','0:a:0','-c','copy','-f','hash','-hash','sha256','-'],prefix+'_audio_packet_hash').strip()
  extracted=self.ff(['-v','error','-i',str(audio),'-map','0:a:0','-c','copy','-f','hash','-hash','sha256','-'],prefix+'_extracted_packet_hash').strip();require(h==extracted,'AUDIO_EXTRACT_PACKET_MISMATCH')
  log=(self.out/(prefix+'_loudness.stderr.txt')).read_text(encoding='utf-8',errors='replace')
  return {'packet_sha256_muxer':h,'waveform':prefix+'_waveform.png','audition_file':audio.name,'loudness_summary':log[log.rfind('Summary:'):],'auditory_listening':False}
 def base_contract(self,p):
  r=self.probe(p,'base_probe');v=next((s for s in r['streams'] if s['codec_type']=='video'),{});a=next((s for s in r['streams'] if s['codec_type']=='audio'),{})
  require((v.get('width'),v.get('height'),v.get('r_frame_rate'),int(v.get('nb_frames',0)))==(1080,1920,'30/1',1200),'BASE_VIDEO_CONTRACT')
  require(abs(float(v.get('duration',0))-40)<.002 and abs(float(a.get('duration',0))-40)<.03,'BASE_DURATION_CONTRACT');return r
 def source_qc(self,inputs):
  base=inputs['base'];source=inputs['c6'];r={'schema':'northstar.promo.source-qc.v1','phase':'source-qc','creative_approval':False,'base_probe':self.base_contract(base),'source_probe':self.probe(source,'c6_probe')}
  f=self.raw(source,'c6_motion',window=True);require(len(f)>=8,'SOURCE_SAMPLE_COUNT')
  steps=[sum(abs(a-b) for a,b in zip(x,y))/1024 for x,y in zip(f,f[1:])];sd=[statistics.pstdev(v) for v in f]
  r['motion']={'mean_abs_luma_step':statistics.mean(steps),'steps':steps,'frame_luma_stddev':sd,'sampled_frames':len(f),'source_seconds':[SOURCE_START,SOURCE_START+SOURCE_DURATION]}
  old={role:fingerprints(self.raw(inputs[role],role+'_comparison')) for role in ('p1','p2','p3')};base_frames=fingerprints(self.raw(base,'base_reuse'))
  r['window_reuse']={role:reuse(fingerprints(f),v) for role,v in old.items()};r['base_reuse']={role:reuse(base_frames,v) for role,v in old.items()}
  r['source_frames']=self.images(source,[0,16,32,48,63],'source',window=True)
  r['base_frames']=self.images(base,[0,300,600,878,909,941,900,1134,1135,1199],'base')
  r['base_audio']=self.audio(base,'base')
  r['edl_binding']={'replacement_frames':[878,942],'c6_source_frames':[83,147],'fps':30,'known_existing_40s_c6_windows_seconds':[[1.5,2.5666666667],[5.48,7.6133333333]],'candidate_window_not_in_existing_c6_edl':True,'cross_previous_cut_reuse_is_measured_estimate':True}
  r['technical_source_eligible']=statistics.mean(steps)>=.75 and min(sd)>=8 and all(x['estimated_seconds']==0 for x in r['window_reuse'].values())
  r['status']='TECHNICAL_SOURCE_BUNDLE_REQUIRES_ROOT_REVIEW';return r
 def conform(self,inputs):
  base=inputs['base'];source=inputs['c6'];self.base_contract(base);p=Path('out/P4_V16_NATIVE_MOTION_NO_TEXT_REVIEW.mp4')
  graph='[0:v]split=2[l][r];[l]trim=start_frame=0:end_frame=878,setpts=PTS-STARTPTS[a];[1:v]'+source_window()+',scale=1080:1920:flags=lanczos,setsar=1[b];[r]trim=start_frame=942:end_frame=1200,setpts=PTS-STARTPTS[c];[a][b][c]concat=n=3:v=1:a=0[out]'
  self.ff(['-v','warning','-i',str(base),'-i',str(source),'-filter_complex',graph,'-map','[out]','-map','0:a:0','-c:v','libx264','-threads','1','-crf','16','-preset','veryfast','-pix_fmt','yuv420p','-fps_mode','cfr','-r','30','-c:a','copy','-movflags','+faststart',str(p)],'conform')
  result={'schema':'northstar.promo.conform.v1','phase':'conform','creative_approval':False,'probe':self.probe(p,'final_probe')};v=next(s for s in result['probe']['streams'] if s['codec_type']=='video');a=next(s for s in result['probe']['streams'] if s['codec_type']=='audio')
  require(int(v.get('nb_frames',0))==1200 and abs(float(v.get('duration',0))-40)<.002 and abs(float(a.get('duration',0))-40)<.03,'FINAL_VIDEO_AUDIO_DURATION')
  result['audio']=self.audio(p,'candidate');base_hash=self.ff(['-v','error','-i',str(base),'-map','0:a:0','-c','copy','-f','hash','-hash','sha256','-'],'base_audio_packet_hash').strip();require(base_hash==result['audio']['packet_sha256_muxer'],'FINAL_AUDIO_PACKET_MISMATCH')
  frames=fingerprints(self.raw(p,'final_reuse'));result['reuse']={role:reuse(frames,fingerprints(self.raw(inputs[role],role+'_comparison'))) for role in ('p1','p2','p3')}
  result['technical_reuse_within_limit']=all(x['estimated_seconds']<=1 for x in result['reuse'].values())
  ids=sorted({0,300,600,900,1199,878,909,941,1134,1135});result['review_frames']=self.images(p,ids,'final');result['timeline_five_frames']=[v for v in result['review_frames'] if v['frame'] in (0,300,600,900,1199)]
  self.ff(['-v','error','-i',str(p),'-map','0:v:0','-map','0:a:0','-f','null','-'],'final_full_decode')
  binary=(self.work/p).read_bytes();result['candidate']={'file':p.name,'size':len(binary),'sha256':digest(binary)};result['status']='TECHNICAL_CANDIDATE_REQUIRES_ROOT_PERSONAL_QC' if result['technical_reuse_within_limit'] else 'TECHNICAL_REUSE_EXCEEDED_NOT_FOR_RELEASE';return result
