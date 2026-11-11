"""Draft-only GitHub transport. Tokens stay in memory; errors never contain URLs/body."""
import hashlib,json,re,urllib.request,urllib.error,urllib.parse
MAX_JSON=2_000_000
MAX_ASSET=512*1024*1024
CDN_HOSTS=frozenset({'release-assets.githubusercontent.com','objects.githubusercontent.com'})
CHECKS=('repository_identity_verified','draft_unpublished','input_authenticated_bytes_equal','output_authenticated_bytes_equal','anonymous_release_metadata_denied','input_anonymous_api_denied','input_anonymous_browser_denied','output_anonymous_api_denied','output_anonymous_browser_denied')
class GuardError(Exception):
 def __init__(self,code):self.code=code;super().__init__(code)
def require(ok,code):
 if not ok:raise GuardError(code)
def integer(v):return type(v) is int and v>0
def sha(v):return isinstance(v,str) and re.fullmatch('[0-9a-f]{64}',v) is not None
def digest(b):return hashlib.sha256(b).hexdigest()
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None
class Transport:
 def request(self,method,url,headers,body=None,limit=MAX_JSON):
  req=urllib.request.Request(url,data=body,headers=headers,method=method)
  try:
   try:r=urllib.request.build_opener(NoRedirect()).open(req,timeout=60)
   except urllib.error.HTTPError as e:r=e
   with r:
    status=r.code;hs={k.lower():v for k,v in r.headers.items()}
    if status in (301,302,303,307,308,401,403,404):return status,hs,b''
    length=hs.get('content-length');require(not length or int(length)<=limit,'RESPONSE_SIZE_LIMIT')
    data=r.read(limit+1);require(len(data)<=limit,'RESPONSE_SIZE_LIMIT');return status,hs,data
  except GuardError:raise
  except Exception:raise GuardError('NETWORK_FAILURE') from None
class GitHub:
 def __init__(self,c,token,transport=None):
  require(isinstance(token,str) and len(token)>10,'MISSING_JOB_TOKEN');self.c=c;self.token=token;self.t=transport or Transport();self.repo=c['repository'];self.prefix='/repos/'+self.repo
 def headers(self,auth=True,binary=False):
  h={'Accept':'application/octet-stream' if binary else 'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'northstar-private-promo-source-worker'}
  if auth:h['Authorization']='Bearer '+self.token
  return h
 def control(self,suffix):
  require(suffix.startswith('/') and not suffix.startswith('//') and '://' not in suffix,'CONTROL_ROUTE')
  status,h,b=self.t.request('GET','https://api.github.com'+self.prefix+suffix,self.headers())
  require(status==200,'CONTROL_HTTP_'+str(status))
  try:return json.loads(b)
  except Exception:raise GuardError('CONTROL_JSON') from None
 def repo_info(self):
  status,h,b=self.t.request('GET','https://api.github.com'+self.prefix,self.headers());require(status==200,'REPOSITORY_HTTP')
  try:r=json.loads(b)
  except Exception:raise GuardError('REPOSITORY_JSON') from None
  require(r.get('full_name')==self.repo and r.get('id')==self.c['repository_id'] and r.get('private') is False and r.get('visibility')=='public' and r.get('default_branch')=='main','REPOSITORY_IDENTITY');return r
 def draft(self):
  r=self.control('/releases/'+str(self.c['draft_release_id']))
  require(r.get('id')==self.c['draft_release_id'] and r.get('draft') is True and r.get('published_at') is None and r.get('tag_name')==self.c['draft_tag'] and r.get('target_commitish')==self.c['draft_target'],'DRAFT_IDENTITY_OR_PUBLISHED');return r
 def assets(self):
  self.draft();out=[]
  for page in range(1,11):
   rows=self.control('/releases/'+str(self.c['draft_release_id'])+'/assets?per_page=100&page='+str(page));require(isinstance(rows,list),'ASSET_LIST');out+=rows
   if len(rows)<100:return out
  raise GuardError('ASSET_LIST_LIMIT')
 def asset(self,asset_id,expected=None):
  self.draft();matches=[a for a in self.assets() if a.get('id')==asset_id];require(len(matches)==1,'ASSET_NOT_IN_SAME_DRAFT');a=matches[0]
  require(a.get('state')=='uploaded' and integer(a.get('size')) and a['size']<=MAX_ASSET,'ASSET_STATE_OR_SIZE')
  require(a.get('url')=='https://api.github.com'+self.prefix+'/releases/assets/'+str(asset_id),'ASSET_API_URL')
  if expected:
   require(a['name']==expected['name'] and a['size']==expected['size'],'ASSET_METADATA_MISMATCH')
   if a.get('digest'):require(a['digest']=='sha256:'+expected['sha256'],'PUBLISHED_DIGEST_MISMATCH')
  return a
 def binary(self,asset_id,expected):
  a=self.asset(asset_id,expected);self.draft()
  url='https://api.github.com'+self.prefix+'/releases/assets/'+str(asset_id)
  status,h,data=self.t.request('GET',url,self.headers(binary=True),limit=expected['size'])
  redirects=0
  while status in (301,302,303,307,308):
   redirects+=1;require(redirects<=3,'REDIRECT_LIMIT');location=h.get('location','');u=urllib.parse.urlsplit(location)
   require(u.scheme=='https' and u.hostname in CDN_HOSTS and u.port in (None,443) and not u.username and not u.password,'REDIRECT_HOST')
   self.draft()
   # Never forward Authorization, cookies or API token to a signed CDN location.
   status,h,data=self.t.request('GET',location,{'Accept':'application/octet-stream','User-Agent':'northstar-private-promo-source-worker'},limit=expected['size'])
  require(status==200,'BINARY_HTTP_'+str(status));require(len(data)==expected['size'] and digest(data)==expected['sha256'],'BINARY_INTEGRITY');self.draft();return data
 def anonymous_denied(self,asset_id,expected):
  a=self.asset(asset_id,expected);browser=a.get('browser_download_url','');u=urllib.parse.urlsplit(browser)
  require(u.scheme=='https' and u.hostname=='github.com' and not u.username and not u.password and u.path.startswith('/'+self.repo+'/releases/download/') and not u.query and not u.fragment,'CANARY_BROWSER_URL')
  for url in ['https://api.github.com'+self.prefix+'/releases/assets/'+str(asset_id),browser]:
   self.draft();status,h,b=self.t.request('GET',url,self.headers(auth=False,binary=True),limit=65536)
   require(status in (401,404),'CANARY_ANONYMOUS_ACCESS_INCONCLUSIVE_OR_ACCESSIBLE')
  return True
 def run_identity(self,run_id,attempt,source_sha,workflow_path,complete):
  r=self.control('/actions/runs/'+str(run_id)+'/attempts/'+str(attempt))
  require(r.get('id')==run_id and r.get('run_attempt')==attempt and r.get('event')=='workflow_dispatch' and r.get('head_branch')=='main' and r.get('head_sha')==source_sha and r.get('path')==workflow_path,'RUN_IDENTITY')
  repo=r.get('repository',{});require(repo.get('id')==self.c['repository_id'] and repo.get('full_name')==self.repo,'RUN_REPOSITORY')
  require(r.get('actor',{}).get('login') in self.c['allowed_actors'] and r.get('triggering_actor',{}).get('login') in self.c['allowed_actors'],'RUN_ACTOR')
  require((r.get('status')=='completed' and r.get('conclusion')=='success') if complete else r.get('status')=='in_progress','RUN_STATUS');return r
 def verify_canary(self):
  c=self.c['canary'];self.repo_info();self.draft();self.run_identity(c['run_id'],c['run_attempt'],c['source_sha'],'.github/workflows/private-media-canary.yml',True)
  proof_meta=self.asset(c['proof_asset_id']);require(proof_meta.get('name')=='CANARY_PROOF.json' and proof_meta['size']<=65536,'CANARY_PROOF_METADATA')
  if c.get('proof_size') is not None:require(proof_meta['size']==c['proof_size'],'CANARY_PROOF_SIZE')
  p=json.loads(self.binary(c['proof_asset_id'],{'name':'CANARY_PROOF.json','size':proof_meta['size'],'sha256':c['proof_sha256']}))
  require(p.get('schema')=='northstar.private-media-canary.v1' and p.get('status')=='CANARY_PRIVATE_ACCESS_VERIFIED' and p.get('private_media_uploaded') is False,'CANARY_PROOF_STATUS')
  for key,want in {'repository':self.repo,'repository_id':self.c['repository_id'],'draft_release_id':self.c['draft_release_id'],'source_workflow_path':'.github/workflows/private-media-canary.yml','source_sha':c['source_sha'],'workflow_run_id':c['run_id'],'workflow_run_attempt':c['run_attempt']}.items():require(p.get(key)==want,'CANARY_PROOF_IDENTITY')
  require(all(p.get('checks',{}).get(k) is True for k in CHECKS),'CANARY_CHECKS_INCOMPLETE')
  status,h,b=self.t.request('GET','https://api.github.com'+self.prefix+'/releases/'+str(self.c['draft_release_id']),self.headers(auth=False));require(status in (401,404),'CANARY_RELEASE_ANONYMOUS_INCONCLUSIVE_OR_ACCESSIBLE')
  for role in ('input','output'):
   e=p.get('canary_'+role,{});asset_id=p.get('canary_'+role+'_asset_id');require(integer(asset_id) and e.get('name')=='synthetic-'+role+'-v1.txt' and integer(e.get('size')) and e['size']<=65536 and sha(e.get('sha256')),'CANARY_ASSET_CONTRACT')
   self.binary(asset_id,e);self.anonymous_denied(asset_id,e)
  self.draft();return p
 def upload_zip(self,name,data):
  require(re.fullmatch(r'promo-(v16-(source-qc|source-study|conform)|v17-review-render)-[0-9]+-[0-9]+\.zip',name) is not None and 0<len(data)<=MAX_ASSET,'OUTPUT_NAME_OR_SIZE')
  self.draft();require(not any(a.get('name')==name for a in self.assets()),'OUTPUT_ALREADY_EXISTS')
  url='https://uploads.github.com'+self.prefix+'/releases/'+str(self.c['draft_release_id'])+'/assets?'+urllib.parse.urlencode({'name':name})
  h=self.headers();h['Content-Type']='application/zip';self.draft();status,headers,body=self.t.request('POST',url,h,data,MAX_JSON);require(status==201,'OUTPUT_UPLOAD_HTTP')
  try:a=json.loads(body)
  except Exception:raise GuardError('OUTPUT_UPLOAD_JSON') from None
  require(integer(a.get('id')),'OUTPUT_ASSET_ID');output_sha=digest(data);expected={'name':name,'size':len(data),'sha256':output_sha};self.draft();self.binary(a['id'],expected);self.anonymous_denied(a['id'],expected);self.draft();return {'asset_id':a['id'],'size':len(data),'sha256':output_sha}
