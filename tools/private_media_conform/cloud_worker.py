"""Manual hosted-only private media worker. Default validation never downloads or launches media."""
import argparse,io,json,os,platform,re,sys,tempfile,zipfile
from pathlib import Path
from private_github import GitHub,GuardError,require,integer,sha,digest,MAX_ASSET
REPO='andrewwhitecog-tech/northstar-minecraft-realm'
WORKFLOW='.github/workflows/private-media-conform.yml'
NAMES={'base':'P4_RING_OPENS_9x16_v14R_YT_SFX_PICTURE_NOCARD.mp4','c6':'C6_best.mp4','p1':'P1_WAKE_9x16_v07.mp4','p2':'P2_SOMETHING_WOKE_9x16_v08.mp4','p3':'P3_THE_COST_9x16_v13.mp4'}
ROOT=Path(__file__).resolve().parent

def input_digest(c):return digest(json.dumps(c['inputs'],sort_keys=True,separators=(',',':')).encode())
def configured(c):
 require(c.get('schema')=='northstar.private-promo-media-config.v1' and c.get('repository')==REPO,'CONFIG_SCHEMA_REPOSITORY')
 require(integer(c.get('repository_id')) and integer(c.get('draft_release_id')),'CONFIG_NUMERIC_IDENTITIES_REQUIRED')
 require(isinstance(c.get('draft_tag'),str) and re.fullmatch('[A-Za-z0-9._-]{1,100}',c['draft_tag']) is not None and isinstance(c.get('draft_target'),str) and (c['draft_target']=='main' or re.fullmatch('[0-9a-f]{40}',c['draft_target'])),'CONFIG_DRAFT_IDENTITY')
 for group in ('allowed_actors','allowed_reviewers'):require(isinstance(c.get(group),list) and len(c[group])>0 and all(isinstance(a,str) and re.fullmatch('[A-Za-z0-9_-]{1,50}',a) for a in c[group]),'CONFIG_TRUSTED_ACTORS_REQUIRED')
 canary=c.get('canary',{});require(all(integer(canary.get(k)) for k in ('run_id','run_attempt','proof_asset_id')) and (canary.get('proof_size') is None or (integer(canary['proof_size']) and canary['proof_size']<=65536)) and sha(canary.get('proof_sha256')) and re.fullmatch('[0-9a-f]{40}',canary.get('source_sha','')),'CANARY_ROOT_PIN_REQUIRED')
 require(c['draft_target']==canary['source_sha'],'DRAFT_CANARY_TARGET_BINDING')
 require(set(c.get('inputs',{}))==set(NAMES),'INPUT_ALLOWLIST_ROLES');ids=[]
 for role,name in NAMES.items():
  item=c['inputs'][role];require(item.get('name')==name and integer(item.get('asset_id')) and integer(item.get('size')) and item['size']<=MAX_ASSET and sha(item.get('sha256')),'INPUT_IDENTITY_PIN');ids.append(item['asset_id'])
 require(len(set(ids))==5 and sum(i['size'] for i in c['inputs'].values())<=1024*1024*1024,'INPUT_DUPLICATE_OR_TOTAL_LIMIT')
 return c

def hosted(c,env,reviewed_sha,system=None,release=None):
 require((system or platform.system())=='Linux' and 'microsoft' not in (release or platform.release()).lower() and not env.get('WSL_INTEROP') and not env.get('WSL_DISTRO_NAME'),'HOSTED_LINUX_ONLY')
 for k,v in {'CI':'true','GITHUB_ACTIONS':'true','RUNNER_ENVIRONMENT':'github-hosted','RUNNER_OS':'Linux','ImageOS':'ubuntu24','GITHUB_EVENT_NAME':'workflow_dispatch','GITHUB_REF':'refs/heads/main','GITHUB_REPOSITORY':REPO}.items():require(env.get(k)==v,'HOST_CONTEXT_'+k)
 require(re.fullmatch('[0-9a-f]{40}',reviewed_sha or '') is not None,'REVIEWED_SOURCE_SHA_REQUIRED')
 require(env.get('GITHUB_SHA')==reviewed_sha and env.get('GITHUB_WORKFLOW_SHA')==reviewed_sha and env.get('GITHUB_WORKFLOW_REF')==REPO+'/'+WORKFLOW+'@refs/heads/main','WORKFLOW_SOURCE_BINDING')
 require(env.get('GITHUB_ACTOR') in c['allowed_actors'] and env.get('GITHUB_TRIGGERING_ACTOR') in c['allowed_actors'],'WORKFLOW_ACTOR')
 require(str(c['repository_id'])==env.get('GITHUB_REPOSITORY_ID') and env.get('GITHUB_RUN_ATTEMPT')=='1','WORKFLOW_REPOSITORY_OR_RETRY')
 require(env.get('GITHUB_WORKSPACE','').startswith('/home/runner/work/') and env.get('RUNNER_TEMP','').startswith('/home/runner/'),'HOSTED_WORKSPACE')
 root=ROOT.resolve();workspace=Path(env['GITHUB_WORKSPACE']).resolve();require(root==workspace or workspace in root.parents,'CHECKOUT_LOCATION')
 require(integer(int(env.get('GITHUB_RUN_ID','0'))),'CURRENT_RUN_ID')

def prior_source_pin(c):
 s=c.get('source_qc',{});require(all(integer(s.get(k)) for k in ('asset_id','size','run_id','run_attempt')) and s['size']<=MAX_ASSET and sha(s.get('sha256')) and re.fullmatch('[0-9a-f]{40}',s.get('source_sha','')) is not None,'SOURCE_QC_ROOT_PIN_REQUIRED')
 a=c.get('approval',{});require(a.get('decision')=='APPROVE_SOURCE_FOR_ISOLATED_CONFORM' and a.get('reviewer') in c['allowed_reviewers'],'ROOT_SOURCE_APPROVAL_REQUIRED')
 require(a.get('source_qc_asset_id')==s['asset_id'] and a.get('source_qc_zip_sha256')==s['sha256'] and a.get('source_qc_run_id')==s['run_id'] and a.get('input_manifest_sha256')==input_digest(c),'ROOT_APPROVAL_BINDING')
 require(a.get('source_frames_personally_viewed') is True and a.get('motion_and_reuse_personally_reviewed') is True and a.get('source_frames')==[83,147] and a.get('replacement_frames')==[878,942],'ROOT_REVIEW_DETAILS_REQUIRED')
 require(isinstance(a.get('reviewed_utc'),str) and re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ',a['reviewed_utc']) is not None,'ROOT_REVIEW_TIME');return s

def inspect_source_zip(blob,c):
 s=prior_source_pin(c);require(len(blob)==s['size'] and digest(blob)==s['sha256'],'SOURCE_QC_ZIP_INTEGRITY')
 try:
  with zipfile.ZipFile(io.BytesIO(blob)) as z:
   info=z.getinfo('SOURCE_QC.json');require(info.file_size<=2_000_000,'SOURCE_QC_RECEIPT_LIMIT');r=json.loads(z.read(info))
 except GuardError:raise
 except Exception:raise GuardError('SOURCE_QC_ZIP_RECEIPT') from None
 require(r.get('schema')=='northstar.promo.source-qc.v1' and r.get('phase')=='source-qc' and r.get('technical_source_eligible') is True and r.get('creative_approval') is False,'SOURCE_QC_TECHNICAL_STATUS')
 for key,value in {'repository':REPO,'repository_id':c['repository_id'],'draft_release_id':c['draft_release_id'],'workflow_run_id':s['run_id'],'workflow_run_attempt':s['run_attempt'],'source_sha':s['source_sha'],'input_manifest_sha256':input_digest(c)}.items():require(r.get(key)==value,'SOURCE_QC_RECEIPT_IDENTITY')
 return r

def zip_outputs(out):
 buffer=io.BytesIO()
 with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
  for f in sorted(out.iterdir()):
   require(f.is_file() and not f.is_symlink() and f.suffix in ('.json','.txt','.png','.m4a','.mp4'),'OUTPUT_FILE_ALLOWLIST');z.write(f,f.name)
 require(0<len(buffer.getbuffer())<=MAX_ASSET,'OUTPUT_ZIP_LIMIT');return buffer.getvalue()

def perform(c,phase,reviewed_sha):
 require(phase in ('source-qc','conform'),'UNSUPPORTED_MEDIA_PHASE')
 configured(c);hosted(c,os.environ,reviewed_sha)
 # The token is never saved, returned, echoed or inherited by FFmpeg.
 token=os.environ.pop('GITHUB_TOKEN',None);api=GitHub(c,token);run_id=int(os.environ['GITHUB_RUN_ID']);attempt=1
 api.repo_info();api.draft();api.run_identity(run_id,attempt,reviewed_sha,WORKFLOW,False);api.verify_canary()
 if phase=='conform':
  s=prior_source_pin(c);api.run_identity(s['run_id'],s['run_attempt'],s['source_sha'],WORKFLOW,True)
  inspect_source_zip(api.binary(s['asset_id'],{'name':'promo-v16-source-qc-'+str(s['run_id'])+'-'+str(s['run_attempt'])+'.zip','size':s['size'],'sha256':s['sha256']}),c)
 from media_pipeline import Media
 with tempfile.TemporaryDirectory(prefix='nsp-private-promo-',dir=os.environ['RUNNER_TEMP']) as temp:
  work=Path(temp);(work/'inputs').mkdir();inputs={}
  for role,item in c['inputs'].items():
   b=api.binary(item['asset_id'],item);p=work/'inputs'/item['name'];p.write_bytes(b);inputs[role]=Path('inputs')/item['name']
  media=Media(work);failed=False
  try:r=media.source_qc(inputs) if phase=='source-qc' else media.conform(inputs)
  except GuardError as e:r={'schema':'northstar.promo.technical-failure.v1','phase':phase,'status':'TECHNICAL_FAILURE_NOT_ACCEPTED','reason_code':e.code,'creative_approval':False};failed=True
  except Exception:r={'schema':'northstar.promo.technical-failure.v1','phase':phase,'status':'TECHNICAL_FAILURE_NOT_ACCEPTED','reason_code':'INTERNAL_MEDIA_FAILURE','creative_approval':False};failed=True
  r.update({'repository':REPO,'repository_id':c['repository_id'],'draft_release_id':c['draft_release_id'],'workflow_run_id':run_id,'workflow_run_attempt':attempt,'source_sha':reviewed_sha,'input_manifest_sha256':input_digest(c),'commands':media.commands,'native_world_written':False,'public_media_output':False,'root_personal_qc_required':True})
  (media.out/('SOURCE_QC.json' if phase=='source-qc' else 'CONFORM_QC.json')).write_text(json.dumps(r,indent=2),encoding='utf-8')
  blob=zip_outputs(media.out);name='promo-v16-'+phase+'-'+str(run_id)+'-'+str(attempt)+'.zip';result=api.upload_zip(name,blob)
  # Public logs contain only small identities/digests/status, never media, command logs or URLs.
  result.update({'status':'PRIVATE_TECHNICAL_FAILURE_BUNDLE' if failed else 'PRIVATE_TECHNICAL_BUNDLE_UPLOADED','phase':phase,'repository_id':c['repository_id'],'draft_release_id':c['draft_release_id'],'workflow_run_id':run_id,'source_sha':reviewed_sha,'creative_acceptance':False})
  print(json.dumps(result,separators=(',',':')));return 1 if failed else 0

def main():
 p=argparse.ArgumentParser();p.add_argument('--phase',choices=['validate','source-qc','conform'],default='validate');p.add_argument('--config',default='config.template.json');p.add_argument('--reviewed-sha');a=p.parse_args()
 try:
  config_path=(ROOT/a.config).resolve();require(config_path.parent==ROOT and config_path.name in ('config.template.json','media-config.json'),'CONFIG_LOCATION')
  c=json.loads(config_path.read_text(encoding='utf-8'))
  if a.phase=='validate':
   # Null placeholders are deliberate; this is payload/source validation, not canary evidence.
   require(c.get('schema')=='northstar.private-promo-media-config.v1' and c.get('repository')==REPO,'CONFIG_SCHEMA_REPOSITORY')
   print(json.dumps({'status':'SOURCE_PAYLOAD_ONLY_CONFIG_NOT_AUTHORIZED','media_started':False,'network_started':False}));return 0
  return perform(c,a.phase,a.reviewed_sha)
 except GuardError as e:print(json.dumps({'status':'BLOCKED_NO_ACCEPTANCE','reason_code':e.code}));return 2
 except Exception:print(json.dumps({'status':'BLOCKED_NO_ACCEPTANCE','reason_code':'UNEXPECTED_FAILURE'}));return 2
if __name__=='__main__':sys.exit(main())
