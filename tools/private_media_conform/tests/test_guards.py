"""SOURCE CONTRACT TESTS ONLY: synthetic HTTP/ZIP data; no media or GitHub calls."""
import ast,contextlib,copy,io,json,sys,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import private_github as pg
import cloud_worker as cw

class FakeTransport:
 def __init__(self,responses):self.responses=list(responses);self.calls=[]
 def request(self,method,url,headers,body=None,limit=pg.MAX_JSON):
  self.calls.append((method,url,dict(headers),body,limit))
  if not self.responses:raise AssertionError('unexpected synthetic transport request')
  return self.responses.pop(0)

def config():
 c=json.loads((cw.ROOT/'config.template.json').read_text());c.update(repository_id=1,draft_release_id=2,draft_tag='private-test',draft_target='a'*40,allowed_actors=['test-owner'],allowed_reviewers=['test-owner'])
 c['canary'].update(run_id=3,run_attempt=1,source_sha='a'*40,proof_asset_id=4,proof_size=None,proof_sha256='b'*64)
 for n,item in enumerate(c['inputs'].values(),10):item.update(asset_id=n,size=10,sha256='c'*64)
 return c

def asset(asset_id=10,data=b'bounded synthetic bytes',name='fixture.txt'):
 return {'id':asset_id,'name':name,'size':len(data),'state':'uploaded','url':'https://api.github.com/'+cw.REPO+'/releases/assets/'+str(asset_id),'browser_download_url':'https://github.com/'+cw.REPO+'/releases/download/private-test/'+name}

def expected(a,data):return {'name':a['name'],'size':len(data),'sha256':pg.digest(data)}

def approval(c):
 c['source_qc']={'asset_id':30,'size':10,'sha256':'d'*64,'run_id':31,'run_attempt':1,'source_sha':'e'*40}
 c['approval'].update(decision='APPROVE_SOURCE_FOR_ISOLATED_CONFORM',reviewer='test-owner',reviewed_utc='2026-11-11T00:00:00Z',source_qc_asset_id=30,source_qc_zip_sha256='d'*64,source_qc_run_id=31,input_manifest_sha256=cw.input_digest(c),source_frames_personally_viewed=True,motion_and_reuse_personally_reviewed=True)
 return c

class GuardTests(unittest.TestCase):
 def test_unsupported_phase_rejects_before_any_configuration(self):
  with patch.object(cw,'configured',side_effect=AssertionError('configuration must not run')):
   for phase in ('source-study','unknown'):
    with self.subTest(phase=phase):
     with self.assertRaisesRegex(pg.GuardError,'UNSUPPORTED_MEDIA_PHASE'):cw.perform({},phase,'a'*40)
 def denied(self,fn,code):
  with self.assertRaises(pg.GuardError) as e:fn()
  self.assertEqual(e.exception.code,code)
 def test_source_files_parse(self):
  for name in ('cloud_worker.py','private_github.py','media_pipeline.py'):
   with self.subTest(name=name):ast.parse((cw.ROOT/name).read_text(),filename=name)
 def test_default_validation_is_offline(self):
  with patch.object(sys,'argv',['cloud_worker.py']),patch.object(pg.Transport,'request',side_effect=AssertionError('network forbidden')),patch('subprocess.run',side_effect=AssertionError('media forbidden')),contextlib.redirect_stdout(io.StringIO()) as out:
   self.assertEqual(cw.main(),0)
  self.assertEqual(json.loads(out.getvalue()),{'status':'SOURCE_PAYLOAD_ONLY_CONFIG_NOT_AUTHORIZED','media_started':False,'network_started':False})
 def test_template_not_authorized_for_work(self):
  c=json.loads((cw.ROOT/'config.template.json').read_text())
  self.denied(lambda:cw.configured(c),'CONFIG_NUMERIC_IDENTITIES_REQUIRED')
 def test_complete_pin_contract_and_distinct_canary_sha(self):
  c=config();self.assertIs(cw.configured(c),c);self.assertNotEqual(c['canary']['source_sha'],'f'*40)
 def test_input_allowlist_and_duplicate_pins(self):
  c=config();c['inputs']['c6']['name']='other.mp4';self.denied(lambda:cw.configured(c),'INPUT_IDENTITY_PIN')
  c=config();c['inputs']['c6']['asset_id']=c['inputs']['base']['asset_id'];self.denied(lambda:cw.configured(c),'INPUT_DUPLICATE_OR_TOTAL_LIMIT')
 def test_missing_canary_pin_and_wrong_target_deny(self):
  c=config();c['canary']['proof_asset_id']=None;self.denied(lambda:cw.configured(c),'CANARY_ROOT_PIN_REQUIRED')
  c=config();c['draft_target']='main';self.denied(lambda:cw.configured(c),'DRAFT_CANARY_TARGET_BINDING')
 def test_published_release_denied(self):
  g=pg.GitHub(config(),'synthetic-test-token');g.control=lambda _:dict(id=2,draft=False,published_at='now',tag_name='private-test',target_commitish='a'*40)
  self.denied(g.draft,'DRAFT_IDENTITY_OR_PUBLISHED')
 def test_foreign_release_asset_denied(self):
  g=pg.GitHub(config(),'synthetic-test-token');g.draft=lambda:None;g.assets=lambda:[asset(99)]
  self.denied(lambda:g.asset(10),'ASSET_NOT_IN_SAME_DRAFT')
 def test_cdn_redirect_strips_auth_and_cookies(self):
  data=b'bounded synthetic bytes';a=asset(data=data);t=FakeTransport([(302,{'location':'https://release-assets.githubusercontent.com/synthetic?opaque=example'},b''),(200,{},data)])
  g=pg.GitHub(config(),'synthetic-test-token',t);g.asset=lambda *_:a;g.draft=lambda:None
  self.assertEqual(g.binary(10,expected(a,data)),data)
  self.assertIn('Authorization',t.calls[0][2]);self.assertNotIn('Authorization',t.calls[1][2]);self.assertNotIn('Cookie',t.calls[1][2])
 def test_rogue_redirect_never_requested(self):
  data=b'bounded synthetic bytes';a=asset(data=data);t=FakeTransport([(302,{'location':'https://untrusted.example/private'},b'')]);g=pg.GitHub(config(),'synthetic-test-token',t);g.asset=lambda *_:a;g.draft=lambda:None
  self.denied(lambda:g.binary(10,expected(a,data)),'REDIRECT_HOST');self.assertEqual(len(t.calls),1)
 def test_binary_hash_mismatch_denied(self):
  data=b'bounded synthetic bytes';a=asset(data=data);g=pg.GitHub(config(),'synthetic-test-token',FakeTransport([(200,{},b'x'*len(data))]));g.asset=lambda *_:a;g.draft=lambda:None
  self.denied(lambda:g.binary(10,expected(a,data)),'BINARY_INTEGRITY')
 def test_asset_anonymous_401_404_only(self):
  data=b'bounded synthetic bytes';a=asset(data=data)
  for statuses in ((401,404),(404,401),(404,404)):
   with self.subTest(statuses=statuses):
    t=FakeTransport([(s,{},b'') for s in statuses]);g=pg.GitHub(config(),'synthetic-test-token',t);g.asset=lambda *_:a;g.draft=lambda:None;self.assertTrue(g.anonymous_denied(10,expected(a,data)));self.assertTrue(all('Authorization' not in x[2] for x in t.calls))
  for statuses in ((403,404),(404,403),(200,404),(302,404)):
   with self.subTest(statuses=statuses):
    t=FakeTransport([(s,{},b'') for s in statuses]);g=pg.GitHub(config(),'synthetic-test-token',t);g.asset=lambda *_:a;g.draft=lambda:None;self.denied(lambda:g.anonymous_denied(10,expected(a,data)),'CANARY_ANONYMOUS_ACCESS_INCONCLUSIVE_OR_ACCESSIBLE')
 def proof(self,c):
  return dict(schema='northstar.private-media-canary.v1',status='CANARY_PRIVATE_ACCESS_VERIFIED',private_media_uploaded=False,repository=cw.REPO,repository_id=1,draft_release_id=2,source_workflow_path='.github/workflows/private-media-canary.yml',source_sha='a'*40,workflow_run_id=3,workflow_run_attempt=1,checks=dict.fromkeys(pg.CHECKS,True))
 def test_proof_cannot_override_failed_actual_run(self):
  g=pg.GitHub(config(),'synthetic-test-token');g.repo_info=lambda:None;g.draft=lambda:None;g.control=lambda _:dict(id=3,run_attempt=1,event='workflow_dispatch',head_branch='main',head_sha='a'*40,path='.github/workflows/private-media-canary.yml',repository={'id':1,'full_name':cw.REPO},actor={'login':'test-owner'},triggering_actor={'login':'test-owner'},status='completed',conclusion='failure');g.binary=lambda *_:self.fail('proof/input read before successful run')
  self.denied(g.verify_canary,'RUN_STATUS')
 def test_release_403_inconclusive_before_synthetic_or_private_inputs(self):
  c=config();proof=self.proof(c);reads=[];g=pg.GitHub(c,'synthetic-test-token',FakeTransport([(403,{},b'')]));g.repo_info=lambda:None;g.draft=lambda:None;g.run_identity=lambda *_:None;g.asset=lambda *_:{'name':'CANARY_PROOF.json','size':1}
  def binary(asset_id,_):reads.append(asset_id);return json.dumps(proof).encode()
  g.binary=binary;self.denied(g.verify_canary,'CANARY_RELEASE_ANONYMOUS_INCONCLUSIVE_OR_ACCESSIBLE');self.assertEqual(reads,[4])
 def test_successful_canary_contract_rechecks_harmless_bytes(self):
  c=config();p=self.proof(c)
  for n,role in enumerate(('input','output'),50):
   b=('harmless '+role).encode();p['canary_'+role+'_asset_id']=n;p['canary_'+role]={'name':'synthetic-'+role+'-v1.txt','size':len(b),'sha256':pg.digest(b)}
  for release_status in (401,404):
   with self.subTest(release_status=release_status):
    t=FakeTransport([(release_status,{},b'')]);g=pg.GitHub(c,'synthetic-test-token',t);g.repo_info=lambda:None;g.draft=lambda:None;runs=[];reads=[];anon=[]
    g.run_identity=lambda *args:runs.append(args);g.asset=lambda *_:{'name':'CANARY_PROOF.json','size':1}
    def binary(asset_id,e):
     reads.append(asset_id)
     if asset_id==4:return json.dumps(p).encode()
     role='input' if asset_id==50 else 'output';b=('harmless '+role).encode();self.assertEqual(e,p['canary_'+role]);return b
    g.binary=binary;g.anonymous_denied=lambda asset_id,e:anon.append(asset_id)
    self.assertEqual(g.verify_canary(),p);self.assertEqual(reads,[4,50,51]);self.assertEqual(anon,[50,51]);self.assertTrue(runs[0][-1])
 def test_perform_privacy_failure_precedes_private_inputs(self):
  c=config();events=[]
  class FakeAPI:
   def __init__(self,*_):pass
   def repo_info(self):pass
   def draft(self):pass
   def run_identity(self,*_):pass
   def verify_canary(self):raise pg.GuardError('CANARY_RELEASE_ANONYMOUS_INCONCLUSIVE_OR_ACCESSIBLE')
   def binary(self,*_):events.append('forbidden-private-input');raise AssertionError('private input read')
  with patch.object(cw,'hosted'),patch.object(cw,'GitHub',FakeAPI),patch.dict(cw.os.environ,{'GITHUB_RUN_ID':'101','GITHUB_TOKEN':'synthetic-test-token'}):
   self.denied(lambda:cw.perform(c,'source-qc','f'*40),'CANARY_RELEASE_ANONYMOUS_INCONCLUSIVE_OR_ACCESSIBLE')
  self.assertEqual(events,[])
 def test_approval_binds_hash_manifest_and_personal_review(self):
  c=approval(config());self.assertEqual(cw.prior_source_pin(c)['run_id'],31)
  for key,value,code in [('source_qc_zip_sha256','0'*64,'ROOT_APPROVAL_BINDING'),('input_manifest_sha256','0'*64,'ROOT_APPROVAL_BINDING'),('source_frames_personally_viewed',False,'ROOT_REVIEW_DETAILS_REQUIRED'),('motion_and_reuse_personally_reviewed',False,'ROOT_REVIEW_DETAILS_REQUIRED')]:
   with self.subTest(key=key):
    d=copy.deepcopy(c);d['approval'][key]=value;self.denied(lambda:cw.prior_source_pin(d),code)
 def test_source_zip_requires_exact_hash_and_identity(self):
  c=approval(config());receipt=dict(schema='northstar.promo.source-qc.v1',phase='source-qc',technical_source_eligible=True,creative_approval=False,repository=cw.REPO,repository_id=1,draft_release_id=2,workflow_run_id=31,workflow_run_attempt=1,source_sha='e'*40,input_manifest_sha256=cw.input_digest(c));b=io.BytesIO()
  with zipfile.ZipFile(b,'w') as z:z.writestr('SOURCE_QC.json',json.dumps(receipt))
  blob=b.getvalue();c['source_qc'].update(size=len(blob),sha256=pg.digest(blob));c['approval']['source_qc_zip_sha256']=pg.digest(blob);self.assertEqual(cw.inspect_source_zip(blob,c)['workflow_run_id'],31)
  self.denied(lambda:cw.inspect_source_zip(blob+b'x',c),'SOURCE_QC_ZIP_INTEGRITY')
  c['source_qc']['source_sha']='f'*40;self.denied(lambda:cw.inspect_source_zip(blob,c),'SOURCE_QC_RECEIPT_IDENTITY')
 def test_local_or_self_hosted_context_rejected(self):
  self.denied(lambda:cw.hosted(config(),{},'f'*40,system='Windows',release='11'),'HOSTED_LINUX_ONLY')
  self.denied(lambda:cw.hosted(config(),{'WSL_INTEROP':'yes'},'f'*40,system='Linux',release='kernel'),'HOSTED_LINUX_ONLY')
  self.denied(lambda:cw.hosted(config(),{'CI':'true','GITHUB_ACTIONS':'true','RUNNER_ENVIRONMENT':'self-hosted'},'f'*40,system='Linux',release='kernel'),'HOST_CONTEXT_RUNNER_ENVIRONMENT')
 def test_output_zip_allowlist(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'receipt.json').write_text('{}');blob=cw.zip_outputs(p)
   with zipfile.ZipFile(io.BytesIO(blob)) as z:self.assertEqual(z.namelist(),['receipt.json'])
   (p/'not-allowed.exe').write_bytes(b'x');self.denied(lambda:cw.zip_outputs(p),'OUTPUT_FILE_ALLOWLIST')
 def test_output_upload_requires_anonymous_denial_before_success(self):
  data=b'synthetic private output contract';name='promo-v16-source-qc-101-1.zip';a=asset(88,data,name)
  for statuses,allowed in [((401,404),True),((403,404),False),((404,403),False),((200,404),False)]:
   with self.subTest(statuses=statuses):
    t=FakeTransport([(201,{},json.dumps({'id':88}).encode()),*[(s,{},b'') for s in statuses]]);g=pg.GitHub(config(),'synthetic-test-token',t);g.draft=lambda:None;g.assets=lambda:[];g.asset=lambda *_:a;readbacks=[];g.binary=lambda asset_id,e:readbacks.append((asset_id,e))
    if allowed:self.assertEqual(g.upload_zip(name,data),{'asset_id':88,'size':len(data),'sha256':pg.digest(data)})
    else:self.denied(lambda:g.upload_zip(name,data),'CANARY_ANONYMOUS_ACCESS_INCONCLUSIVE_OR_ACCESSIBLE')
    self.assertEqual(readbacks,[(88,{'name':name,'size':len(data),'sha256':pg.digest(data)})]);self.assertEqual(t.calls[0][0],'POST');self.assertTrue(all('Authorization' not in call[2] for call in t.calls[1:]))
 def test_canonical_frame_chain_in_qc_and_conform_commands(self):
  import media_pipeline as mp
  class Captured(Exception):pass
  with tempfile.TemporaryDirectory() as d:
   m=mp.Media(Path(d));calls=[]
   def capture(args,*_):calls.append(args);raise Captured()
   m.ff=capture
   for call in (lambda:m.raw(Path('source.mp4'),'motion',window=True),lambda:m.images(Path('source.mp4'),[0,63],'source',window=True)):
    with self.assertRaises(Captured):call()
   m.base_contract=lambda _:None
   with self.assertRaises(Captured):m.conform({'base':Path('base.mp4'),'c6':Path('source.mp4')})
   chain=mp.source_window();self.assertEqual(chain.split(',')[:3],['fps=30','trim=start_frame=83:end_frame=147','setpts=PTS-STARTPTS'])
   self.assertTrue(calls[0][calls[0].index('-vf')+1].startswith(chain+','));self.assertTrue(calls[1][calls[1].index('-vf')+1].startswith(chain+','));self.assertIn('[1:v]'+chain+',',calls[2][calls[2].index('-filter_complex')+1]);self.assertTrue(all('-ss' not in call and '-t' not in call for call in calls))
   self.denied(lambda:m.raw(Path('source.mp4'),'motion',start=1,window=True),'CANONICAL_WINDOW_NO_SEEK')
 def test_workflow_uses_pinned_uv_and_no_artifact_cache(self):
  text=(cw.ROOT/'workflow.template.yml').read_text();self.assertIn('actions/checkout@11d5960a326750d5838078e36cf38b85af677262',text);self.assertIn('astral-sh/setup-uv@37802adc94f370d6bfd71619e3f0bf239e1f3b78',text);self.assertIn('UV_PYTHON_DOWNLOADS: never',text);self.assertNotIn('run: python3',text);self.assertNotIn('upload-artifact@',text);self.assertIn('enable-cache: false',text)

  execution_lines=[line for line in text.splitlines() if 'python -B' in line]
  self.assertTrue(execution_lines)
  for line in execution_lines:self.assertIn('nice -n 19 uv run --no-project --python 3.12 python -B',line)
 def test_media_commands_are_not_started_on_import_or_validate(self):
  with patch('subprocess.run',side_effect=AssertionError('no media execution')):
   import media_pipeline
   self.assertEqual((media_pipeline.START_FRAME,media_pipeline.END_FRAME,media_pipeline.SOURCE_FRAME,media_pipeline.TOTAL_FRAMES),(878,942,83,1200))

if __name__=='__main__':unittest.main()
