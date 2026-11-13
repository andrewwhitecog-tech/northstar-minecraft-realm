"""Hosted-only original asset export. No Git, API, world, native client/server or paid provider."""
from __future__ import annotations
import datetime,json,os,platform,subprocess,sys,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parent
MAX_BYTES=32*1024*1024

def need(ok,message):
 if not ok:raise RuntimeError(message)
def main():
 #Guard before any asset generation. Source import is inert.
 need(sys.platform=='linux' and platform.machine()=='x86_64' and os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted' and os.environ.get('RUNNER_OS')=='Linux','Only genuine GitHub-hosted Linux allowed; no local export fallback')
 need(os.environ.get('GITHUB_EVENT_NAME')=='workflow_dispatch','Explicit owner workflow dispatch required')
 need(os.environ.get('GITHUB_REF')=='refs/heads/main','Actual exports allowed only on main')
 approved=os.environ.get('REVIEWED_SOURCE_COMMIT','');need(len(approved)==40 and all(c in '0123456789abcdef' for c in approved) and approved==os.environ.get('GITHUB_SHA'),'Exact reviewed source commit required')
 event=json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text());need(event.get('repository',{}).get('private') is False and event['repository']['owner']['login']=='andrewwhitecog-tech','Public owner repository only')
 need(sys.version_info[:2]==(3,12),'Python3.12 required')
 import PIL
 need(PIL.__version__=='12.3.0','Pinned Pillow version required')
 osrelease=Path('/etc/os-release').read_text();need('VERSION_ID="24.04"' in osrelease,'Ubuntu24.04 required')
 base=ROOT/'generated_base_v01';extra=ROOT/'generated_expansion_v02';need(not base.exists() and not extra.exists(),'Fresh output directories required')
 report={'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':sys.version,'pillow':PIL.__version__,'runner':'ubuntu-24.04 GitHub-hosted x86_64','commit':os.environ.get('GITHUB_SHA'),'scope':'Original geometry/textures/animations and actual software previews only','steps':[],'success':False,'native_verified':False,'human_visual_approved':False,'world_writes':0,'paid_provider_calls':0,'numeric_registry_allocations':0}
 def save(): (ROOT/'HOSTED_EXPORT_ACTUAL.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
 def run(label,args):
  start=time.monotonic();p=subprocess.run([sys.executable,'-X','utf8',*args],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=300)
  (ROOT/(label+'.stdout')).write_text(p.stdout,encoding='utf-8');(ROOT/(label+'.stderr')).write_text(p.stderr,encoding='utf-8');report['steps'].append({'label':label,'exit_code':p.returncode,'elapsed_seconds':time.monotonic()-start,'stdout_file':label+'.stdout','stderr_file':label+'.stderr'});save()
  if p.returncode:print(p.stdout);print(p.stderr,file=sys.stderr)
  need(p.returncode==0,'Actual '+label+' failed; preserved full logs')
 save()
 try:
  run('source_tests',['-m','unittest','-v','test_fauna_sources.py'])
  run('base_export',['build_original_fauna.py','--output',str(base)])
  from validate_fauna_exports import inspect_set,BASE
  report['base_actual_validation']=inspect_set(base,BASE);save()
  run('expansion_export',['build_fauna_expansion.py','--output',str(extra)])
  run('actual_export_validation',['validate_fauna_exports.py','--base',str(base),'--expansion',str(extra),'--receipt',str(ROOT/'EXPORTED_ASSET_VALIDATION_ACTUAL.json')])
  report['success']=True
 except BaseException:
  report['error']=traceback.format_exc();print(report['error'],file=sys.stderr,flush=True)
 finally:
  files=[p for d in [base,extra] if d.exists() for p in d.rglob('*') if p.is_file()]
  symlinks=any(p.is_symlink() for p in files)
  if symlinks:report['success']=False;report['artifact_limit_error']='Symlink output refused'
  size=sum(p.stat().st_size for p in files)+sum(p.stat().st_size for p in ROOT.glob('*.stdout'))+sum(p.stat().st_size for p in ROOT.glob('*.stderr'))
  report['actual_generated_bytes']=size;report['artifact_upload_allowed']=not symlinks and size+1024*1024<=MAX_BYTES
  if not report['artifact_upload_allowed']:report['success']=False;report['artifact_limit_error']='Actual artifact bytes exceed32MiB cap; upload withheld'
  report['finished_at']=datetime.datetime.now(datetime.timezone.utc).isoformat();save()
  if os.environ.get('GITHUB_OUTPUT'):
   with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8') as f:f.write('upload_allowed='+str(report['artifact_upload_allowed']).lower()+'\n')
 print(json.dumps({'success':report['success'],'actual_generated_bytes':report['actual_generated_bytes'],'native_verified':False,'human_visual_approved':False}))
 return 0 if report['success'] else 1
if __name__=='__main__':raise SystemExit(main())
