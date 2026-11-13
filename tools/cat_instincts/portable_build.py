#!/usr/bin/env python3
"""Pinned public GitHub-hosted Java source/JUnit build only. Never starts Minecraft."""
import argparse,hashlib,json,os,pathlib,platform,re,shutil,subprocess,sys,time,traceback,urllib.parse,urllib.request,xml.etree.ElementTree as ET,zipfile
HOME=pathlib.Path(__file__).resolve().parent
REPO=HOME.parents[1]
REPOSITORY='andrewwhitecog-tech/northstar-minecraft-realm'
HOSTS={'piston-data.mojang.com','libraries.minecraft.net','maven.fabricmc.net','repo.maven.apache.org'}

def need(ok,msg):
 if not ok:raise RuntimeError(msg)
def digest(path,algorithm='sha256'):
 h=hashlib.new(algorithm)
 with path.open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execute',action='store_true');ap.add_argument('--output',type=pathlib.Path);ap.add_argument('--expected-commit');a=ap.parse_args()
 packet=HOME/'PUBLIC_SOURCE.json';pins=json.loads(packet.read_text(encoding='utf-8'))
 for rel,sha in pins['files'].items():
  path=(HOME/rel).resolve();need(path.is_relative_to(HOME) and path.is_file() and not path.is_symlink() and digest(path)==sha,'Source drift: '+rel)
 if not a.execute:print(json.dumps({'sourceVerified':True,'executed':False}));return 0
 need(platform.system()=='Linux' and os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted','Genuine Linux hosted source job required; local work uses admitted local runner')
 need(os.environ.get('GITHUB_REPOSITORY')==REPOSITORY and os.environ.get('GITHUB_EVENT_NAME') in ('pull_request','workflow_dispatch'),'Wrong repository/event')
 event=json.loads(pathlib.Path(os.environ['GITHUB_EVENT_PATH']).read_text(encoding='utf-8'));need(event['repository']['private'] is False,'Public standard-runner source route only')
 need(a.expected_commit and re.fullmatch('[0-9a-f]{40}',a.expected_commit) and a.expected_commit==os.environ.get('GITHUB_SHA'),'Exact hosted commit required')
 actual_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip();need(actual_head==a.expected_commit,'Checkout drift')
 root=a.output.resolve();temp=pathlib.Path(os.environ['RUNNER_TEMP']).resolve();need(root.is_relative_to(temp) and root!=temp and not root.exists(),'Fresh hosted output required')
 root.mkdir();evidence=root/'evidence';evidence.mkdir();cache=root/'dependencies';cache.mkdir()
 report={'commit':actual_head,'sourcePacketSha256':digest(packet),'success':False,'nativeExecuted':False,'liveInstalled':False,'downloads':[],'steps':[],'errors':[]}
 def save():(evidence/'BUILD_TEST_ACTUAL.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
 def env():return {k:v for k,v in os.environ.items() if k in ('PATH','JAVA_HOME','HOME','TMPDIR','LANG','LC_ALL')}
 def command(name,argv,timeout=90):
  r=subprocess.run([str(v) for v in argv],cwd=HOME,env=env(),capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
  (evidence/(name+'.stdout.log')).write_text(r.stdout,encoding='utf-8');(evidence/(name+'.stderr.log')).write_text(r.stderr,encoding='utf-8')
  report['steps'].append({'name':name,'exitCode':r.returncode});save();return r
 try:
  version=command('java_version',['java','-version']);need(version.returncode==0 and re.search(r'version "25(?:\.|\")',version.stderr+version.stdout),'Actual Java25 required')
  lock=json.loads((HOME/'DEPENDENCIES.json').read_text(encoding='utf-8'));need(len(lock['artifacts'])<=64,'Unbounded dependency list')
  total=0;deadline=time.monotonic()+600
  for item in lock['artifacts']:
   url=urllib.parse.urlparse(item['url']);need(url.scheme=='https' and url.hostname in HOSTS and not url.username and not url.password and not url.query,'Unexpected dependency source')
   path=(cache/item['path']).resolve();need(path.is_relative_to(cache),'Dependency path escape');path.parent.mkdir(parents=True,exist_ok=True)
   size=item['size'];total+=size;need(type(size) is int and 0<size<=64*1024*1024 and total<=256*1024*1024,'Dependency byte cap exceeded')
   need(time.monotonic()<deadline,'Bounded dependency download deadline')
   with urllib.request.urlopen(urllib.request.Request(item['url'],headers={'User-Agent':'NorthStar-source-build'}),timeout=45) as response,path.open('wb') as output:
    need(urllib.parse.urlparse(response.url).hostname in HOSTS,'Unapproved redirect')
    count=0
    while True:
     block=response.read(1024*1024)
     if not block:break
     count+=len(block);need(count<=size,'Oversize dependency');output.write(block)
   algorithm='sha256' if 'sha256' in item else 'sha1';need(path.stat().st_size==size and digest(path,algorithm)==item[algorithm],'Dependency byte pin mismatch: '+item['name'])
   report['downloads'].append({'path':item['path'],'bytes':size,'algorithm':algorithm,'digest':item[algorithm]});save()
  junit=cache/lock['junitPath'];cp=os.pathsep.join(str(cache/item['path']) for item in lock['artifacts'] if item['path']!=lock['junitPath'])
  production=sorted((HOME/'src').rglob('*.java'));tests=sorted((HOME/'tests').rglob('*.java'));need(len(production)==16 and len(tests)==4,'Source census mismatch')
  classes=root/'classes';classes.mkdir();testclasses=root/'testclasses';testclasses.mkdir()
  def javac(name,files,classpath,dest):
   args=root/(name+'.args');values=['--release','25','-encoding','UTF-8','-proc:none','-cp',classpath,'-d',str(dest),*[str(f) for f in files]]
   args.write_text('\n'.join('"'+v.replace('\\','/')+'"' for v in values),encoding='utf-8')
   return command(name,['javac','-J-XX:ActiveProcessorCount=2','-J-Xmx512M','@'+str(args)],120)
  need(javac('production',production,cp,classes).returncode==0,'Actual production javac failed')
  need(javac('test_compile',tests,str(classes)+os.pathsep+str(junit),testclasses).returncode==0,'Actual test javac failed')
  xml=evidence/'junit'
  result=command('junit',['java','-XX:ActiveProcessorCount=2','-Xmx256M','-jar',junit,'execute','--class-path',str(classes)+os.pathsep+str(testclasses),'--select-class','net.northstar.cat.InstinctPolicyTest','--select-class','net.northstar.cat.InstinctLimitsTest','--select-class','net.northstar.cat.InstinctMotionTest','--select-class','net.northstar.cat.InstinctScopeTest','--reports-dir',xml,'--disable-ansi-colors'],60)
  counts={'tests':0,'failures':0,'errors':0,'skipped':0}
  for file in xml.glob('TEST-*.xml'):
   suite=ET.parse(file).getroot()
   for key in counts:counts[key]+=int(suite.attrib.get(key,0))
  report['junitActual']=counts;save();need(result.returncode==0 and counts=={'tests':22,'failures':0,'errors':0,'skipped':0},'Actual JUnit outcome not22clean tests')
  jar=evidence/'northstar_cat_instincts-0.1.1-26.3-scoped-candidate.jar'
  with zipfile.ZipFile(jar,'w',zipfile.ZIP_DEFLATED) as z:
   for file in sorted(classes.rglob('*.class')):z.write(file,file.relative_to(classes).as_posix())
   for name in ('fabric.mod.json','northstar_cat.mixins.json'):z.write(HOME/'resources'/name,name)
  report['jar']={'name':jar.name,'sha256':digest(jar),'bytes':jar.stat().st_size,'nativeVerified':False};report['success']=True;return 0
 except BaseException:report['errors'].append(traceback.format_exc());raise
 finally:
  save();size=sum(p.stat().st_size for p in evidence.rglob('*') if p.is_file());allowed=size<=2*1024*1024
  output=os.environ.get('GITHUB_OUTPUT')
  if output:
   with open(output,'a',encoding='utf-8') as f:f.write('upload_allowed='+str(allowed).lower()+'\n')
  need(allowed,'Evidence exceeds2MiB: artifact upload withheld, no truncation')
  print(json.dumps({'receipt':str(evidence/'BUILD_TEST_ACTUAL.json'),'success':report['success'],'nativeExecuted':False}))
if __name__=='__main__':raise SystemExit(main())
