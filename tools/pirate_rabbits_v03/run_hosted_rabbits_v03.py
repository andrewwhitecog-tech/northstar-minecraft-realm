"""Hosted export of four replacement rabbits only; no native/world/provider activity."""
from __future__ import annotations
import datetime,json,os,platform,subprocess,sys,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def require(ok,message):
 if not ok:raise RuntimeError(message)
def main():
 require(sys.platform=='linux' and platform.machine()=='x86_64' and os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted','Genuine GitHub-hosted Linux only')
 require(os.environ.get('GITHUB_EVENT_NAME')=='workflow_dispatch' and os.environ.get('GITHUB_REF')=='refs/heads/main','Explicit main dispatch only')
 approved=os.environ.get('REVIEWED_SOURCE_COMMIT','');require(len(approved)==40 and all(c in '0123456789abcdef' for c in approved) and approved==os.environ.get('GITHUB_SHA'),'Exact reviewed source commit required')
 event=json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text());require(event.get('repository',{}).get('private') is False and event['repository']['owner']['login']=='andrewwhitecog-tech','Public owner repository only')
 import PIL
 require(sys.version_info[:2]==(3,12) and PIL.__version__=='12.3.0','Pinned Python3.12 and Pillow12.3.0 required')
 require('VERSION_ID="24.04"' in Path('/etc/os-release').read_text(),'Ubuntu24.04 required')
 out=ROOT/'generated_rabbits_v03';require(not out.exists(),'Fresh four-model output only')
 report={'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'commit':os.environ.get('GITHUB_SHA'),'python':sys.version,'pillow':PIL.__version__,'steps':[],'success':False,'native_verified':False,'visual_accepted':False,'world_writes':0,'provider_calls':0,'unchanged_models_reexported':0}
 def save(): (ROOT/'HOSTED_RABBITS_V03_ACTUAL.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
 def run(label,args):
  start=time.monotonic();p=subprocess.run([sys.executable,'-B','-X','utf8',*args],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=300)
  (ROOT/(label+'.stdout')).write_text(p.stdout,encoding='utf-8');(ROOT/(label+'.stderr')).write_text(p.stderr,encoding='utf-8')
  report['steps'].append({'label':label,'exit_code':p.returncode,'elapsed_seconds':time.monotonic()-start});save()
  if p.returncode:print(p.stdout);print(p.stderr,file=sys.stderr)
  require(p.returncode==0,label+' failed; full actual logs retained')
 save()
 try:
  run('source_tests_v03',['-m','unittest','-v','test_rabbits_v03.py'])
  run('four_rabbit_export_v03',['build_rabbits_v03.py','--output',str(out)])
  run('four_rabbit_validation_v03',['validate_rabbits_v03.py','--output',str(out),'--receipt',str(ROOT/'RABBIT_EXPORT_VALIDATION_V03_ACTUAL.json')])
  report['success']=True
 except BaseException:
  report['error']=traceback.format_exc();print(report['error'],file=sys.stderr,flush=True)
 finally:
  files=[p for p in out.rglob('*') if p.is_file()] if out.exists() else []
  size=sum(p.stat().st_size for p in files)+sum(p.stat().st_size for p in ROOT.glob('*.stdout'))+sum(p.stat().st_size for p in ROOT.glob('*.stderr'))
  report['actual_generated_bytes']=size;report['artifact_upload_allowed']=not any(p.is_symlink() for p in files) and size+1024*1024<=32*1024*1024
  if not report['artifact_upload_allowed']:report['success']=False;report['artifact_error']='32MiB ceiling or symlink guard rejected upload'
  report['finished_at']=datetime.datetime.now(datetime.timezone.utc).isoformat();save()
  if os.environ.get('GITHUB_OUTPUT'):
   with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8') as f:f.write('upload_allowed='+str(report['artifact_upload_allowed']).lower()+'\n')
 print(json.dumps({'success':report['success'],'actual_generated_bytes':size,'native_verified':False,'visual_accepted':False}))
 return 0 if report['success'] else 1
if __name__=='__main__':raise SystemExit(main())
