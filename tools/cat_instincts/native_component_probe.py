"""Fresh hosted loopback cat component proof. Source preparation only until Root dispatch.
Real scoped-goal/contact and save/restart proof only after actual hosted execution.
No client/Bedrock/whole-species/live acceptance implied.
"""
from __future__ import annotations
import argparse,copy,datetime,hashlib,importlib.util,json,math,os,pathlib,re,secrets,shutil,signal,socket,struct,subprocess,sys,time,traceback,uuid,zipfile
HOME=pathlib.Path(__file__).resolve().parent
REPO=HOME.parents[1]
RUNTIME=REPO/'tools/cloud_survival_calibration'
REPOSITORY='andrewwhitecog-tech/northstar-minecraft-realm'
OWNER='CatProofOwner';GUEST='CatProofGuest'
CANARY='nsp_cat.instincts.canary'
CAT='@e[type=minecraft:cat,tag=nsp_cat.proof.cat,limit=1]'
VICTIM='@e[tag=nsp_cat.proof.victim,limit=1]'
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def need(ok,why):
 if not ok:raise RuntimeError(why)
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def source_guard(native_sha,cat_sha):
 need(all(isinstance(x,str)and re.fullmatch('[0-9a-f]{64}',x)for x in [native_sha,cat_sha]),'Full reviewed native and current cat source packet SHA256 required')
 p=HOME/'NATIVE_SOURCE.json';need(sha(p)==native_sha,'Native source packet drift');packet=json.loads(p.read_text())
 for rel,pin in packet['files'].items():
  path=(REPO/rel).resolve();need(not pathlib.Path(rel).is_absolute()and '..'not in pathlib.Path(rel).parts and path.is_relative_to(REPO.resolve()),'Source path escape')
  need(path.is_file()and not path.is_symlink()and sha(path)==pin,'Native source drift: '+rel)
 cat=HOME/'PUBLIC_SOURCE.json';need(sha(cat)==cat_sha,'Current reviewed cat source packet drift')
 for rel,pin in json.loads(cat.read_text())['files'].items():
  path=(HOME/rel).resolve();need(path.is_relative_to(HOME)and path.is_file()and not path.is_symlink()and sha(path)==pin,'Cat source drift: '+rel)
 return packet

def hosted_guard(expected):
 need(sys.platform=='linux'and os.uname().machine=='x86_64'and os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'and os.environ.get('RUNNER_OS')=='Linux','Only genuine standard hosted Linux; no local/native fallback')
 need(os.environ.get('GITHUB_REPOSITORY')==REPOSITORY and os.environ.get('GITHUB_REF')=='refs/heads/main'and os.environ.get('GITHUB_ACTOR')=='andrewwhitecog-tech'and os.environ.get('GITHUB_EVENT_NAME')=='workflow_dispatch','Owner manual dispatch on public main only')
 event=json.loads(pathlib.Path(os.environ['GITHUB_EVENT_PATH']).read_text());need(event['repository']['full_name']==REPOSITORY and event['repository']['private']is False,'Actual public repository required')
 need(isinstance(expected,str)and re.fullmatch('[0-9a-f]{40}',expected)and expected==os.environ.get('GITHUB_SHA'),'Exact reviewed main commit required')
 actual=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True,timeout=10).strip();need(actual==expected,'Actual checkout drift');return actual

class Rcon:
    def __init__(self,port,password):
        self.s=socket.create_connection(('127.0.0.1',port),timeout=5);self.s.settimeout(5);self.i=0
        try:
            self.send(3,password)
            for _ in range(2):
                ident,kind,_=self.recv()
                if kind==2:need(ident==self.i,'Private RCON authentication failed');return
            raise RuntimeError('No RCON authentication response')
        except BaseException:
            self.s.close();raise
    def exact(self,n):
        result=b''
        while len(result)<n:
            block=self.s.recv(n-len(result));need(bool(block),'RCON socket closed');result+=block
        return result
    def send(self,kind,text):
        self.i+=1;data=struct.pack('<ii',self.i,kind)+text.encode('utf-8')+b'\0\0';self.s.sendall(struct.pack('<i',len(data))+data)
    def recv(self):
        size=struct.unpack('<i',self.exact(4))[0];need(10<=size<=1048576,'Bounded RCON packet required');data=self.exact(size)
        need(data[-2:]==b'\0\0','RCON terminator mismatch')
        return struct.unpack('<ii',data[:8])+(data[8:-2].decode('utf-8','replace'),)
    def cmd(self,text):
        self.send(2,text);ident,kind,result=self.recv();need(ident==self.i and kind==0,'RCON response mismatch');return result
    def close(self):self.s.close()

def group_alive(pgid):
    try:os.killpg(pgid,0);return True
    except ProcessLookupError:return False


def prepare_server(root):
 """Reuse pinned downloader/transport, excluding all client assets/native libraries and Flan."""
 lock=json.loads((RUNTIME/'LOCK.json').read_text())
 # server-transport.json is separately pinned in NATIVE_SOURCE; the shared LOCK has no row for it.
 for name in ['minecraft-26.3.json','fabric-server-0.20.1.json']:
  need(sha(RUNTIME/'metadata'/name)==lock['metadata'][name]['sha256'],'Runtime metadata drift: '+name)
 spec=importlib.util.spec_from_file_location('cat_public_runtime_download',RUNTIME/'download_runtime.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 root.mkdir();down=m.Downloader(root,lock['limits']);profile=json.loads((RUNTIME/'metadata/fabric-server-0.20.1.json').read_text());transport=json.loads((RUNTIME/'metadata/server-transport.json').read_text());meta=json.loads((RUNTIME/'metadata/minecraft-26.3.json').read_text())
 need(profile['mainClass']=='net.fabricmc.loader.impl.launch.knot.KnotServer'and meta['id']=='26.3'and meta['javaVersion']['majorVersion']==25,'Exact server version required')
 cp=[]
 for lib in profile['libraries']:
  relative=m.gav_path(lib['name']);hashes={'sha256':lib.get('sha256')or lock['loaderSha256']}
  need(lib.get('sha256')or lib['name']=='net.fabricmc:fabric-loader:0.20.1','Unpinned Fabric library')
  path=m.safe_child(root/'fabric',relative);down.get(lib['url'].rstrip('/')+'/'+relative,path,hashes,lib.get('size'));cp.append(str(path))
 outer=transport['outer'];need(outer['sha1']==meta['downloads']['server']['sha1'],'Official server bundle mismatch')
 bundle=down.get(outer['url'],root/'server-bundle.jar',{'sha1':outer['sha1'],'sha256':outer['sha256']},outer['size'])
 with zipfile.ZipFile(bundle)as z:
  need(len(z.namelist())==len(set(z.namelist())),'Duplicate server bundle member')
  for item in transport['classpath_members']:
   path=m.safe_child(root/'server-libraries',item['relative']);path.parent.mkdir(parents=True,exist_ok=True);entry=z.getinfo(item['member']);need(entry.file_size==item['bytes'],'Server member size drift')
   with z.open(entry)as src,path.open('xb')as dst:shutil.copyfileobj(src,dst,1024*1024)
   need(sha(path)==item['sha256'],'Server member hash drift');cp.append(str(path))
 api=[r for r in lock['mods']if r['filename'].startswith('fabric-api-')];need(len(api)==1,'Exact existing Fabric API row required')
 carpet=json.loads((HOME/'fixtures/CARPET_RUNTIME.json').read_text());need(carpet['game_versions']==['26.3']and carpet['loaders']==['fabric']and len(carpet['files'])==1,'Exact Carpet metadata required')
 mods=api+[carpet['files'][0]];paths=[]
 for row in mods:paths.append(down.get(row['url'],root/'mods'/row['filename'],row['hashes'],row['size']))
 return {'classpath':os.pathsep.join(cp),'mainClass':profile['mainClass'],'mods':paths,'downloadedBytes':down.total,'javaPin':lock['java'],'clientAssetsDownloaded':False,'flanIncluded':False}

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execute',action='store_true');ap.add_argument('--reviewed-source-sha256',required=True);ap.add_argument('--reviewed-cat-source-sha256',required=True);ap.add_argument('--expected-commit');ap.add_argument('--cat-build-receipt',type=pathlib.Path);ap.add_argument('--output',type=pathlib.Path);a=ap.parse_args()
 source_guard(a.reviewed_source_sha256,a.reviewed_cat_source_sha256)
 from audited_log_records import audit_log_records  # Import only after the reviewed NATIVE_SOURCE graph passed.
 if not a.execute:print(json.dumps({'sourceVerified':True,'executed':False,'nativeVerified':False}));return 0
 commit=hosted_guard(a.expected_commit);temp=pathlib.Path(os.environ['RUNNER_TEMP']).resolve();need(a.output is not None and a.cat_build_receipt is not None,'Fresh output and actual same-run cat build receipt required');root=a.output.resolve();build=a.cat_build_receipt.resolve()
 need(root.is_relative_to(temp)and root!=temp and not root.exists()and build.is_relative_to(temp)and build.is_file(),'Hosted fresh containment required')
 built=json.loads(build.read_text());need(built['success']is True and built['commit']==commit and built['sourcePacketSha256']==a.reviewed_cat_source_sha256,'Actual current reviewed source-built JAR required; no old PR32 or external binary')
 counts=built.get('junitActual',{});need(counts.get('tests',0)>0 and all(counts.get(x)==0 for x in ['failures','errors','skipped']),'Actual clean source JUnit receipt required; no native inference from it')
 jar=(build.parent/built['jar']['name']).resolve();need(jar.is_relative_to(build.parent)and jar.is_file()and sha(jar)==built['jar']['sha256'],'Actual source-built JAR identity mismatch')
 root.mkdir();evidence=root/'evidence';evidence.mkdir();report={'startedAt':utc(),'commit':commit,'nativeSourcePacket':a.reviewed_source_sha256,'catSourcePacket':a.reviewed_cat_source_sha256,'jar':{'sha256':sha(jar),'bytes':jar.stat().st_size},'checks':[],'commands':[],'tickSteps':[],'errors':[],'success':False,'scope':'fresh loopback server/Carpet entity AI component only','humanClientProven':False,'bedrockProven':False,'lyingPoseProven':False,'allSpeciesProven':False,'saveReloadProven':False,'naturalSpawnClassifierPositiveProven':False,'liveInstalled':False,'masterWrites':False}
 server=rcon=None;log=None;native_end=time.monotonic()+1200;password=secrets.token_hex(24);probe_dir=None;action_sequence=0;boot_name='';runtime=None;boot_end=None
 def save():
  p=evidence/'CAT_NATIVE_ACTUAL.json.tmp';p.write_text(json.dumps(report,indent=2)+'\n');p.replace(evidence/'CAT_NATIVE_ACTUAL.json')
 def cmd(text):
  if native_end is not None:need(time.monotonic()<native_end and (boot_end is None or time.monotonic()<boot_end),'Actual native overall1200/per-boot720 deadline expired')
  reply=rcon.cmd(text);report['commands'].append({'at':utc(),'command':text,'reply':reply})
  need(re.search(r'Unknown (?:or incomplete command|function|block|item|entity)|Incorrect argument|Expected (?:integer|double|float|literal)|Invalid (?:command|argument)',reply,re.I)is None,'Actual command parse failure: '+reply);return reply
 def check(ok,label,actual):
  report['checks'].append({'pass':bool(ok),'label':label,'actual':actual});save();need(ok,'Actual native check failed: '+label+'; actual='+str(actual))
 def score():
  text=cmd('scoreboard players get #obs ncp');m=re.search(r'\bhas (-?\d+)\b',text);need(m is not None,'Actual score unreadable: '+text);return int(m.group(1))
 def observe(condition):
  # A zero-fork execute relation invokes no store callback: absent relation remains false.
  # Real positive ownership and negative absent-entity controls independently test the observation.
  need(condition.startswith('execute ')and 'run say'not in condition,'Boolean execute required');cmd('scoreboard players set #obs ncp 0');cmd('execute store success score #obs ncp run '+condition);n=score();need(n in(0,1),'Actual boolean score not0/1');return n
 def scalar(query):
  text=cmd('data get '+query);m=re.search(r':\s*(-?\d+(?:\.\d+)?)[bdfLs]?\s*$',text);need(m is not None,'Actual NBT scalar unreadable: '+text);return float(m.group(1))
 def pos(entity):return [scalar('entity '+entity+' Pos['+str(i)+']')for i in range(3)]
 def hp(entity):return scalar('entity '+entity+' Health')
 def distance(p,q):return math.dist(p,q)
 def max_hp(entity):
  cmd('execute store result score #obs ncp run attribute '+entity+' minecraft:max_health get 1000');n=score();need(n>0,'Actual positive max health required');return n/1000
 def ticks(n):
  need(type(n)is int and 1<=n<=200,'Bounded tick step');before=int(re.findall(r'-?\d+',cmd('time query gametime'))[-1]);cmd('tick step '+str(n));end=min(native_end,time.monotonic()+max(10,n*.25))
  while time.monotonic()<end:
   after=int(re.findall(r'-?\d+',cmd('time query gametime'))[-1])
   if after-before>=n:need(after-before==n,'Clock advanced beyond requested frozen ticks');report['tickSteps'].append({'before':before,'after':after,'requested':n});return
   need(server.poll()is None,'Server closed during actual ticks');time.sleep(.05)
  raise RuntimeError('Actual frozen clock did not advance requested ticks')
 def relation(name,entity=CAT):return observe('execute as '+entity+' on '+name+' if entity @s')
 def targets(entity=VICTIM):
  selector='@s[tag=nsp_cat.proof.victim]'if entity==VICTIM else '@s[name='+entity+']'if entity in(OWNER,GUEST)else None
  need(selector is not None,'Only exact proof victim/player target relations are allowed');return observe('execute as '+CAT+' on target if entity '+selector)
 def actual_uuid(name):
  text=cmd('data get entity '+name+' UUID');m=re.search(r'\[I;\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*\]',text);need(m is not None,'Actual typed player UUID unreadable');return [int(x)for x in m.groups()]
 def ready_actor(name):
  end=min(native_end,time.monotonic()+30);rows=[]
  while time.monotonic()<end:
   present=observe('execute if entity @a[name='+name+',gamemode=survival]');ops=json.loads((srv/'ops.json').read_text());need(ops==[],'Fresh proof actor must remain non-op');rows.append({'at':utc(),'survivalPresence':present,'ops':ops})
   if present:
    actual=actual_uuid(name);expected=list(struct.unpack('>iiii',uuid.UUID(offline(name)).bytes));need(actual==expected,'Actual synthetic actor UUID differs from deterministic offline identity');report.setdefault('actors',{})[name]={'readiness':rows,'actualUuidInts':actual,'offlineUuidMatched':True,'actualPosition':pos(name),'realHumanClient':False};check(True,'actual non-op Carpet owner/guest ready '+name,report['actors'][name]);return
   time.sleep(.1)
  check(False,'bounded actual Carpet actor readiness '+name,rows)
 def reset():
  cmd('kill @e[type=!minecraft:player,tag=nsp_cat.proof]');cmd('tp '+OWNER+' 32.5 65 32.5');cmd('tp '+GUEST+' 30.5 65 36.5')
  for name in [OWNER,GUEST]:
   for tag in ['nsp_cat.hostile','nsp_cat.wild']:cmd('tag '+name+' remove '+tag)
   cmd('item replace entity '+name+' weapon.mainhand with minecraft:air')
 def owned(entity):
  cmd('data modify entity '+entity+' Owner set from entity '+OWNER+' UUID')
  raw=cmd('data get entity '+entity+' Owner');match=re.search(r'\[I;\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*\]',raw);need(match is not None and [int(x)for x in match.groups()]==actual_uuid(OWNER),'Actual Owner typed UUID did not match observed owner')
  own=observe('execute as '+entity+' on owner if entity @s[name='+OWNER+']');check(own==1,'actual owner relation for '+entity,{'ownerUuid':actual_uuid(OWNER),'relationSuccess':own})
 def cat(x=34.5,z=32.5,scoped=True):
  tags=['nsp_cat.proof','nsp_cat.proof.cat']+([CANARY]if scoped else[])
  cmd('summon minecraft:cat '+str(x)+' 65 '+str(z)+' {Tags:'+json.dumps(tags,separators=(',',':'))+',Sitting:0b,Age:0,PersistenceRequired:1b,Silent:1b}')
  check(observe('execute if entity '+CAT)==1,'actual primary cat exists',pos(CAT));owned(CAT);check(hp(CAT)>max_hp(CAT)*.5,'actual primary cat healthy',{'health':hp(CAT),'maximum':max_hp(CAT)})
 def victim(kind='minecraft:zombie',tags=(),owned_pet=False,x=42.5,z=32.5):
  actual_tags=['nsp_cat.proof','nsp_cat.proof.victim',*tags];cmd('summon '+kind+' '+str(x)+' 65 '+str(z)+' {Tags:'+json.dumps(actual_tags,separators=(',',':'))+',NoAI:1b,PersistenceRequired:1b,Silent:1b}')
  cmd('attribute '+VICTIM+' minecraft:max_health base set 100');cmd('data merge entity '+VICTIM+' {Health:100f}')
  if owned_pet:owned(VICTIM)
  need(hp(VICTIM)>0,'Actual victim health must be readable');return VICTIM
 def hunt(kind='minecraft:zombie',tags=()):
  reset();cat();victim(kind,tags);start=pos(CAT);initial=hp(VICTIM);rows=[]
  for _ in range(60):
   ticks(1);p=pos(CAT);active=targets();rows.append({'pos':p,'targetRelation':active,'victimHealth':hp(VICTIM)})
   if active==1 and distance(start,p)>.25:check(True,'actual navigation and quarry acquisition '+kind,{'start':start,'samples':rows});return initial
  check(False,'actual navigation and quarry acquisition '+kind,{'start':start,'samples':rows})
 def track(n,target=VICTIM):
  rows=[]
  for _ in range(n):ticks(1);rows.append({'cat':pos(CAT),'victimHealth':hp(target),'quarryActive':targets(target)})
  return rows
 def positive(kind,tags):
  before=hunt(kind,tags);rows=[]
  for _ in range(160):
   ticks(1);rows.append({'cat':pos(CAT),'health':hp(VICTIM)})
   if rows[-1]['health']<before:check(True,'actual unprivileged cat contact health drop '+kind,{'before':before,'samples':rows});return
  check(False,'actual unprivileged cat contact health drop '+kind,{'before':before,'samples':rows})
 def protection(kind,name,pet=False):
  reset()
  if kind=='player':
   subject=name;cmd('tp '+name+' 35.5 65 32.5');cmd('tag '+name+' add nsp_cat.hostile');cmd('tag '+name+' add nsp_cat.wild')
  else:subject=victim(kind,['nsp_cat.hostile','nsp_cat.wild']+(['nsp_friendly']if name=='friendly animal'else[]),pet,x=35.5)
  before=hp(subject);cmd('damage '+subject+' 1 minecraft:generic');ticks(1);damaged=hp(subject);check(damaged<before,'actual protected fixture damageable positive control '+name,{'before':before,'after':damaged})
  if kind=='player':cmd('effect give '+name+' minecraft:instant_health 1 4 true');ticks(2)
  else:cmd('data merge entity '+subject+' {Health:100f}')
  baseline=hp(subject);cat();rows=track(40,subject);check(all(r['victimHealth']==baseline and r['quarryActive']==0 for r in rows),'native protected role despite hostile/wild tags '+name,{'baseline':baseline,'samples':rows})
 def cancel(which):
  hunt();before=hp(VICTIM)
  if which in('healthy recall','low health'):cmd('tp '+OWNER+' 28.5 65 32.5')
  start=pos(CAT);ownerpos=pos(OWNER)
  if which=='friendship':
   cmd('tag '+VICTIM+' add nsp_friendly');p=pos(CAT);cmd('tp '+VICTIM+' '+str(p[0]+.7)+' 65 '+str(p[2]))
  elif which=='sitting':cmd('data merge entity '+CAT+' {Sitting:1b}');check(scalar('entity '+CAT+' Sitting')==1,'actual Sitting NBT set',1)
  elif which=='healthy recall':
   check(hp(CAT)>max_hp(CAT)*.5,'actual healthy before recall',{'health':hp(CAT),'maximum':max_hp(CAT)});cmd('tag '+CAT+' add nsp_cat.recall')
  elif which=='low health':cmd('data merge entity '+CAT+' {Health:'+str(max_hp(CAT)*.2)+'f}')
  elif which=='leash':
   p=pos(CAT);cmd('tp '+OWNER+' '+str(p[0]-2)+' 65 '+str(p[2]));cmd('item replace entity '+OWNER+' weapon.mainhand with minecraft:lead');cmd('player '+OWNER+' look at '+str(p[0])+' 65.35 '+str(p[2]));cmd('player '+OWNER+' use once')
   attachment=[];last_health=before
   for _ in range(2):
    ticks(1);current=hp(VICTIM);attached=observe('execute as '+CAT+' on leasher if entity @s[name='+OWNER+']');row={'cat':pos(CAT),'ownerLeasher':attached,'victimHealth':current,'previousHealth':last_health,'quarryActive':targets()};attachment.append(row)
    if attached:
     check(current==last_health and row['quarryActive']==0,'actual first observed attached tick veto',row);break
    last_health=current
   check(bool(attachment[-1]['ownerLeasher']),'actual Carpet lead interaction attached to owner',attachment)
   baseline=attachment[-1]['victimHealth'];rows=track(19);check(all(r['victimHealth']==baseline and r['quarryActive']==0 for r in rows),'actual20 observed-attached ticks pursuit cancellation leash',{'attachmentSamples':attachment,'following19Ticks':rows});return
  rows=track(20);check(all(r['victimHealth']==before and r['quarryActive']==0 for r in rows),'actual20-tick pursuit cancellation '+which,{'healthBefore':before,'samples':rows})
  if which in('healthy recall','low health'):check(distance(start,ownerpos)-distance(rows[-1]['cat'],ownerpos)>=.25,'actual return movement '+which,{'start':start,'end':rows[-1]['cat'],'owner':ownerpos})
 def outside_return():
  reset();floor=[]
  for x in range(32,51):floor.append({'x':x,'stone':observe('execute if block '+str(x)+' 64 32 minecraft:stone'),'headClear':[observe('execute if block '+str(x)+' '+str(y)+' 32 minecraft:air')for y in(65,66,67)]})
  check(all(r['stone']==1 and r['headClear']==[1,1,1]for r in floor),'actual entire straight18m return floor/headroom samples',floor);cat(50.5);start=pos(CAT);o=pos(OWNER);check(abs(distance(start,o)-18)<.01,'actual outside16m return fixture starts18m from owner',{'cat':start,'owner':o})
  rows=[start]
  for _ in range(140):
   ticks(1);rows.append(pos(CAT))
   if distance(rows[-1],o)<=4:break
  deltas=[distance(x,y)for x,y in zip(rows,rows[1:])];check(distance(rows[-1],o)<=4 and max(deltas,default=0)<1.5 and all(abs(p[1]-65)<.6 for p in rows),'actual safe outside16m owner return without teleport-sized steps',{'owner':o,'positions':rows,'maxSingleActualTickMovement':max(deltas,default=0)})
 def play():
  reset();cat();victim('minecraft:wolf',['nsp_cat.playmate'],True,x=39.5);before=hp(VICTIM);start=pos(CAT);rows=track(100)
  check(max(distance(start,r['cat'])for r in rows)>.5 and all(r['victimHealth']==before and r['quarryActive']==0 for r in rows),'actual friendly-companion movement without damage',{'start':start,'healthBefore':before,'samples':rows,'lyingPoseObserved':False,'exactGoalAttributionInstrumented':False})
 def compile_observer(rt):
  source=HOME/'native_scope_observer/src/net/northstar/scopeprobe/ScopeObserverMixin.java'
  classes=root/'scope-observer-classes';classes.mkdir()
  result=subprocess.run(['javac','-J-XX:ActiveProcessorCount=2','-J-Xmx512M','--release','25','-encoding','UTF-8','-proc:none','-cp',rt['classpath'],'-d',str(classes),str(source)],capture_output=True,text=True,timeout=120)
  (evidence/'scope-observer-javac.stdout.log').write_text(result.stdout);(evidence/'scope-observer-javac.stderr.log').write_text(result.stderr)
  report['observerCompile']={'exitCode':result.returncode,'sourceSha256':sha(source)};save();need(result.returncode==0,'Actual server scope-observer javac failed')
  out=root/'northstar-cat-scope-observer.jar'
  with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED)as z:
   for p in classes.rglob('*.class'):z.write(p,p.relative_to(classes).as_posix())
   for name in ['fabric.mod.json','northstar_scope_probe.mixins.json']:z.write(HOME/'native_scope_observer/resources'/name,name)
  report['observerJarSha256']=sha(out);return out
 def start_boot(name,enabled):
  nonlocal server,rcon,log,probe_dir,action_sequence,boot_name,boot_end
  need(server is None or server.poll()is not None,'Previous owned server must be actually closed before restart')
  boot_name=name;probe_dir=root/('observer_'+name);probe_dir.mkdir();action_sequence=0
  logpath=evidence/('server.actual.log'if name=='enabled_initial'else'server.'+name+'.log');log=logpath.open('xb')
  env={k:v for k,v in os.environ.items()if k in('PATH','JAVA_HOME','HOME','TMPDIR','LANG','LC_ALL')}
  flags=['-Dnsp.cat.instincts.enabled=true']if enabled else[]
  argv=['java','-Xms256M','-Xmx2G','-XX:ActiveProcessorCount=2','-Dmax.bg.threads=1','-Dfile.encoding=UTF-8','-Djava.awt.headless=true','-Djava.net.preferIPv4Stack=true',*flags,'-Dnsp.cat.scope.probe.dir='+str(probe_dir),'-cp',runtime['classpath'],runtime['mainClass'],'--nogui']
  server=subprocess.Popen(argv,cwd=srv,env=env,stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);boot_end=min(native_end,time.monotonic()+720)
  boot={'name':name,'pid':server.pid,'enabledPropertyExplicit':enabled,'observerDir':str(probe_dir),'log':str(logpath),'startedAt':utc()};report.setdefault('boots',[]).append(boot);report['serverPid']=server.pid
  end=min(boot_end,time.monotonic()+360);rcon=None
  while time.monotonic()<end:
   need(server.poll()is None,'Actual scoped server exited during '+name+' startup')
   try:rcon=Rcon(rconport,password);rcon.cmd('list');break
   except(OSError,RuntimeError):
    if rcon:rcon.close();rcon=None
    time.sleep(.5)
  need(rcon is not None,'Actual startup deadline '+name)
  expected='NSP_CAT_INSTINCTS loaded; enabled='+str(enabled).lower()
  check(expected in logpath.read_text(errors='replace'),'actual source-built property state '+name,{'jarSha256':sha(jar),'expectedLogFragment':expected})
  check(json.loads((srv/'ops.json').read_text())==[],'actual no operators '+name,[])
 def close_boot():
  nonlocal server,rcon,log,boot_end
  need(server is not None and server.poll()is None,'Owned running boot required for normal save/restart')
  save_reply=rcon.cmd('save-all flush');stop_error=None
  try:rcon.cmd('stop')
  except(OSError,RuntimeError)as error:stop_error=str(error)
  if rcon:rcon.close();rcon=None
  server.wait(timeout=min(60,max(1,native_end-time.monotonic())))
  closure={'name':boot_name,'exitCode':server.returncode,'forced':False,'processGroupAlive':group_alive(server.pid),'saveReply':save_reply,'stopResponseError':stop_error}
  if server.stdin:server.stdin.close()
  if log:log.close();log=None
  report['boots'][-1]['closure']=closure;save()
  need(server.returncode==0 and not closure['processGroupAlive'],'Actual normal closure before restart required')
  need(json.loads((srv/'ops.json').read_text())==[],'No operator change across restart');server=None;boot_end=None
 def uuid_string(entity):return str(uuid.UUID(bytes=struct.pack('>iiii',*actual_uuid(entity))))
 def observer_state():
  ticks(2);ident=uuid_string(CAT);path=probe_dir/(ident+'.json');need(not (probe_dir/'OBSERVER_ERROR.json').exists(),'Actual server observer error')
  need(path.is_file(),'Actual transformed Mob/GoalSelector observer did not emit cat state')
  row=json.loads(path.read_text());now=int(re.findall(r'-?\d+',cmd('time query gametime'))[-1])
  need(row['uuid']==ident and now-1<=row['tick']<=now and row['implementsScopedCat']is True,'Fresh actual scoped Cat interface/selector snapshot required')
  return row
 def exact_goal(state,name):
  found=[g for g in state['goals']if g['class']==name];need(len(found)==1,'Exactly one observed goal required: '+name);return found[0]
 def vanilla_goals(state):
  bed=exact_goal(state,'net.minecraft.world.entity.ai.goal.CatLieOnBlockGoal');follow=exact_goal(state,'net.minecraft.world.entity.ai.goal.FollowOwnerGoal')
  need(bed['priority']==5 and follow['priority']==6,'Authentic26.3 vanilla bed/follow priorities required')
  need(not any(g['class']=='net.northstar.cat.InstinctVanillaFollowGoal'for g in state['goals']),'Unscoped cat must retain exact vanilla follow class')
  return {'bed':bed,'follow':follow}
 def contact_control(expect_veto,label):
  nonlocal action_sequence
  cmd('kill '+VICTIM);p=pos(CAT);victim(x=p[0]+.7,z=p[2]);before=hp(VICTIM)
  action_sequence+=1;request={'sequence':action_sequence,'mode':'contact','catUuid':uuid_string(CAT),'victimUuid':uuid_string(VICTIM)}
  temp=probe_dir/'action.json.tmp';temp.write_text(json.dumps(request));temp.replace(probe_dir/'action.json');ticks(2)
  need(not (probe_dir/'OBSERVER_ERROR.json').exists(),'Actual observer contact action failed');path=probe_dir/'CONTACT_ACTUAL.json';need(path.is_file(),'Actual direct contact response missing');actual=json.loads(path.read_text())
  need(actual['sequence']==action_sequence and actual['catUuid']==request['catUuid'] and actual['victimUuid']==request['victimUuid'],'Exact current action response required')
  expected=(actual['returned']is False and actual['after']==actual['before']==before)if expect_veto else(actual['returned']is True and actual['after']<actual['before']==before)
  check(expected,label,actual)
 def scope_controls():
  reset();cat(scoped=False);victim();before=hp(VICTIM);rows=track(40)
  check(all(r['victimHealth']==before and r['quarryActive']==0 for r in rows),'actual untagged no custom quarry despite enabled property',rows)
  cmd('kill '+VICTIM);cmd('data merge entity '+CAT+' {Sitting:1b}');baseline=observer_state();original=vanilla_goals(baseline)
  check(CANARY not in baseline['tags'] and baseline['enabledProperty']is True,'actual fresh untagged vanilla goal objects/priorities',baseline)
  contact_control(False,'actual untagged sitting cat contact uses vanilla damage, no global veto')
  cmd('tag '+CAT+' add '+CANARY);active=observer_state();bed=exact_goal(active,'net.minecraft.world.entity.ai.goal.CatLieOnBlockGoal');follow=exact_goal(active,'net.northstar.cat.InstinctVanillaFollowGoal')
  check(bed['objectId']==original['bed']['objectId'] and bed['priority']==7 and follow['priority']==6 and not any(g['class']=='net.minecraft.world.entity.ai.goal.FollowOwnerGoal'for g in active['goals']),'actual live tag activation reprioritizes same bed and replaces exact follow instance',{'baseline':baseline,'active':active})
  contact_control(True,'actual tagged sitting cat transformed contact veto')
  cmd('tag '+CAT+' remove '+CANARY);revoked=observer_state();restored=vanilla_goals(revoked)
  check(restored==original,'actual revocation restores original same-instance vanilla goals and priorities',{'original':original,'restored':restored,'state':revoked})
  contact_control(False,'actual revoked cat contact returns to vanilla semantics');report['scopeGoalRestorationProven']=True
 def revocation_during_hunt():
  hunt();active=observer_state();before=hp(VICTIM);cmd('tag '+CAT+' remove '+CANARY);rows=track(20);revoked=observer_state();vanilla_goals(revoked)
  check(all(r['victimHealth']==before and r['quarryActive']==0 for r in rows),'actual20-tick tag revocation during pursuit clears target without damage',{'active':active,'samples':rows,'revoked':revoked})
 def attach_saved_fence_leash():
  p=pos(CAT);cmd('tp '+OWNER+' '+str(p[0]-2)+' 65 '+str(p[2]));cmd('item replace entity '+OWNER+' weapon.mainhand with minecraft:lead');cmd('player '+OWNER+' look at '+str(p[0])+' 65.35 '+str(p[2]));cmd('player '+OWNER+' use once')
  attached=[]
  for _ in range(3):
   ticks(1);attached.append(relation('leasher'))
   if observe('execute as '+CAT+' on leasher if entity @s[name='+OWNER+']')==1:break
  check(observe('execute as '+CAT+' on leasher if entity @s[name='+OWNER+']')==1,'actual saved fixture lead attached by Carpet use',attached)
  cmd('setblock 32 65 34 minecraft:oak_fence');cmd('player '+OWNER+' look at 32.5 65.75 34.5');cmd('player '+OWNER+' use once');ticks(2)
  check(observe('execute as '+CAT+' on leasher if entity @s[type=minecraft:leash_knot]')==1,'actual player use transfers lead to saved fence knot',cmd('data get entity '+CAT))
  cmd('item replace entity '+OWNER+' weapon.mainhand with minecraft:air')
 def recover_actors():
  cmd('carpet commandPlayer true');cmd('tick freeze');cmd('forceload add 16 16 96 96')
  for name,x,z in [(OWNER,32.5,32.5),(GUEST,30.5,36.5)]:
   cmd('player '+name+' spawn at '+str(x)+' 65 '+str(z)+' facing 0 0 in minecraft:overworld in survival');ready_actor(name)
 def saved_state_ready(before,label):
  rows=[];report.setdefault('savedLeashReadiness',{})[label]=rows
  for _ in range(20):
   row=observer_state();rows.append(row);save()
   need(row['uuid']==before['uuid'] and row['ownerUuid']==before['ownerUuid'] and CANARY in row['tags'] and row['sitting']is True and abs(row['health']-before['health'])<.01,'Saved identity/tag/sit/health mismatch; only holder resolution may settle')
   if row['leashed']is True and observe('execute as '+CAT+' on leasher if entity @s[type=minecraft:leash_knot]')==1:return row
  check(False,'actual saved fence leash resolves within40 frozen ticks '+label,rows)
 def persistence_and_default_off():
  reset();cat(35.5);cmd('data merge entity '+CAT+' {Sitting:1b,Health:2.0f}');attach_saved_fence_leash();before=observer_state()
  check(CANARY in before['tags'] and before['sitting']is True and before['leashed']is True and abs(before['health']-2)<.01,'actual tagged save fixture sits/leashes/low health before normal save',before)
  check(exact_goal(before,'net.northstar.cat.InstinctVanillaFollowGoal')['priority']==6,'actual active scoped goal before saved restart',before['goals'])
  report['persistedFixtureBefore']=before;close_boot();start_boot('enabled_reload',True);recover_actors();loaded=saved_state_ready(before,'enabled_reload')
  check(loaded['uuid']==before['uuid'] and loaded['ownerUuid']==before['ownerUuid'] and CANARY in loaded['tags'] and loaded['sitting']is True and loaded['leashed']is True and abs(loaded['health']-before['health'])<.01,'actual same saved cat UUID owner tag sit leash health survive normal stop/restart',{'before':before,'loaded':loaded})
  check(observe('execute as '+CAT+' on owner if entity @s[name='+OWNER+']')==1 and observe('execute as '+CAT+' on leasher if entity @s[type=minecraft:leash_knot]')==1,'actual loaded owner and persistent fence-leasher relations',{'owner':relation('owner'),'leasher':relation('leasher')})
  check(exact_goal(loaded,'net.northstar.cat.InstinctVanillaFollowGoal')['priority']==6 and exact_goal(loaded,'net.minecraft.world.entity.ai.goal.CatLieOnBlockGoal')['priority']==7,'actual loaded tag activates transformed goals after NBT read',loaded)
  first=json.loads((probe_dir/(loaded['uuid']+'.first.json')).read_text());check(first['uuid']==before['uuid'] and first['ownerUuid']==before['ownerUuid'] and CANARY in first['tags'] and exact_goal(first,'net.northstar.cat.InstinctVanillaFollowGoal')['priority']==6 and exact_goal(first,'net.minecraft.world.entity.ai.goal.CatLieOnBlockGoal')['priority']==7,'actual first loaded selector tick already uses saved canary scope',first)
  report['saveReloadProven']=True;report['persistedFixtureLoaded']=loaded;report['persistedFixtureFirstLoaded']=first
  close_boot();start_boot('default_off',False);recover_actors();off=saved_state_ready(before,'default_off');vanilla_goals(off)
  check(off['enabledProperty']is False and off['uuid']==before['uuid'] and CANARY in off['tags'] and off['ownerUuid']==before['ownerUuid'],'actual separate JVM default-off retains tagged saved cat vanilla goals',off)
  contact_control(False,'actual default-off tagged sitting cat contact remains vanilla');report['defaultOffProven']=True
 def interrupted(signum,frame):raise InterruptedError('Owned native controller interrupted')
 for sig in (signal.SIGTERM,signal.SIGINT):signal.signal(sig,interrupted)
 try:
  jv=subprocess.run(['java','-version'],capture_output=True,text=True,timeout=10);java_pin=json.loads((RUNTIME/'LOCK.json').read_text())['java'];report['java']={'exitCode':jv.returncode,'stdout':jv.stdout,'stderr':jv.stderr};need(jv.returncode==0 and java_pin in jv.stdout+jv.stderr,'Exact native Java pin required')
  runtime=prepare_server(root/'runtime');report['runtime']={k:v for k,v in runtime.items()if k not in('classpath','mods')};srv=root/'server';srv.mkdir();(srv/'mods').mkdir()
  for path in runtime['mods']:shutil.copyfile(path,srv/'mods'/path.name)
  shutil.copyfile(jar,srv/'mods'/jar.name)
  ports=[]
  for _ in range(2):
   with socket.socket()as s:s.bind(('127.0.0.1',0));ports.append(s.getsockname()[1])
  need(ports[0]!=ports[1],'Fresh loopback port collision');gameport,rconport=ports
  generator={'biome':'minecraft:plains','layers':[{'block':'minecraft:bedrock','height':1},{'block':'minecraft:stone','height':62},{'block':'minecraft:grass_block','height':1}],'features':False,'lakes':False}
  props={'server-ip':'127.0.0.1','server-port':gameport,'enable-rcon':'true','rcon.port':rconport,'rcon.password':password,'online-mode':'false','enforce-secure-profile':'false','white-list':'true','enforce-whitelist':'true','level-name':'world','level-type':'minecraft:flat','generator-settings':json.dumps(generator,separators=(',',':')),'gamemode':'survival','difficulty':'normal','pvp':'true','spawn-protection':0,'view-distance':5,'simulation-distance':5,'pause-when-empty-seconds':0,'max-players':4,'max-tick-time':120000,'broadcast-rcon-to-ops':'false','enable-command-block':'false'}
  (srv/'server.properties').write_text(''.join(str(k)+'='+str(v)+'\n'for k,v in props.items()));(srv/'eula.txt').write_text('eula=true\n');(srv/'ops.json').write_text('[]')
  def offline(name):return str(uuid.UUID(bytes=hashlib.md5(('OfflinePlayer:'+name).encode()).digest(),version=3))
  profiles=[{'name':n,'uuid':offline(n)}for n in [OWNER,GUEST]];(srv/'whitelist.json').write_text(json.dumps(profiles));expires=(datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S %z');(srv/'usercache.json').write_text(json.dumps([{**p,'expiresOn':expires}for p in profiles]))
  observer_jar=compile_observer(runtime)
  shutil.copyfile(observer_jar,srv/'mods'/observer_jar.name)
  start_boot('enabled_initial',True)
  owned_binds=[]
  for line in pathlib.Path('/proc/net/tcp').read_text().splitlines()[1:]:
   fields=line.split();addr,port=fields[1].split(':')
   if int(port,16)in ports and fields[3]=='0A':owned_binds.append({'port':int(port,16),'loopback':addr=='0100007F'})
  check(len(owned_binds)==2 and all(x['loopback']for x in owned_binds),'actual game and RCON listeners are loopback only',owned_binds)
  cmd('scoreboard objectives add ncp dummy');cmd('carpet commandPlayer true');cmd('gamerule minecraft:spawn_mobs false');cmd('gamerule minecraft:advance_time false');cmd('time set midnight');cmd('weather clear');cmd('forceload add 16 16 96 96')
  end=min(native_end,time.monotonic()+90)
  while time.monotonic()<end:
   if all(observe('execute if loaded '+str(x)+' 64 '+str(z))for x in [24,40,56,72,88,96]for z in [24,40,56,72,88,96]):break
   time.sleep(.25)
  else:raise RuntimeError('Actual fixture chunks did not load')
  cmd('fill 16 64 16 96 64 96 minecraft:stone');cmd('fill 16 65 16 96 68 96 minecraft:air');check(observe('execute if block 50 64 32 minecraft:stone')==1,'actual continuous return floor sampled',1)
  for name,x,z in [(OWNER,32.5,32.5),(GUEST,30.5,36.5)]:cmd('player '+name+' spawn at '+str(x)+' 65 '+str(z)+' facing 0 0 in minecraft:overworld in survival');ready_actor(name)
  check(observe('execute if entity @a[name=CatProofAbsent]')==0,'actual boolean negative control',0);cmd('tick freeze');ticks(1)
  positive('minecraft:zombie',[]);positive('minecraft:rabbit',['nsp_cat.wild'])
  for role in [('player',OWNER,False),('player',GUEST,False),('minecraft:villager','villager NPC',False),('minecraft:iron_golem','golem NPC',False),('minecraft:wolf','tame wolf',True),('minecraft:cat','tame cat',True),('minecraft:cow','friendly animal',False)]:protection(*role)
  for condition in ['friendship','sitting','healthy recall','low health','leash']:cancel(condition)
  outside_return();play()
  scope_controls();revocation_during_hunt();persistence_and_default_off()
  report['success']=True
 except BaseException:report['errors'].append(traceback.format_exc());print(report['errors'][-1],file=sys.stderr,flush=True)
 finally:
  # Only owned process group, normal save/stop first; forced cleanup can never pass.
  stop_requested=False;stop_errors=[]
  if server is not None and server.poll()is None:
   if rcon:
    try:rcon.cmd('save-all flush');rcon.cmd('stop');stop_requested=True
    except(OSError,RuntimeError)as error:stop_errors.append(type(error).__name__+': '+str(error))
   if not stop_requested and server.stdin:
    try:server.stdin.write(b'save-all flush\nstop\n');server.stdin.flush();stop_requested=True
    except OSError as error:stop_errors.append(str(error))
  if rcon:
   try:rcon.close()
   except OSError:pass
  if server is not None:
   forced=False
   try:
    try:server.wait(timeout=60)
    except subprocess.TimeoutExpired:
     forced=True
     if server.poll()is None and os.getpgid(server.pid)==server.pid:os.killpg(server.pid,signal.SIGTERM)
     try:server.wait(timeout=10)
     except subprocess.TimeoutExpired:
      if server.poll()is None and os.getpgid(server.pid)==server.pid:os.killpg(server.pid,signal.SIGKILL)
      server.wait(timeout=10)
    alive=group_alive(server.pid);report['serverClosure']={'exitCode':server.returncode,'forced':forced,'processGroupAlive':alive,'stopRequested':stop_requested,'stopErrors':stop_errors};need(not forced and server.returncode==0 and not alive,'Normal owned server closure required');ops=json.loads((srv/'ops.json').read_text());report['opsAfterStop']=ops;need(ops==[],'No operators after native proof')
   except BaseException:report['errors'].append('Cleanup: '+traceback.format_exc());report['success']=False
  else:report['serverClosure']={'started':False};report['success']=False
  if log:log.close()
  lp=evidence/'server.actual.log'
  if lp.exists():
   actors_ok=all(report.get('actors',{}).get(n,{}).get('offlineUuidMatched') is True and report['actors'][n]['readiness'][-1]['survivalPresence']==1 and report['actors'][n]['readiness'][-1]['ops']==[] for n in [OWNER,GUEST])
   owner_ok=any(c['pass'] and c['label']=='actual owner relation for '+CAT for c in report['checks'])
   closure=report.get('serverClosure',{});prior_closures=[b.get('closure',{})for b in report.get('boots',[])[:-1]]
   closure_ok=closure.get('exitCode')==0 and closure.get('forced') is False and closure.get('processGroupAlive') is False and all(c.get('exitCode')==0 and c.get('forced') is False and c.get('processGroupAlive') is False for c in prior_closures)
   logs=[{'file':p.name,'boot':p.name.removeprefix('server.').removesuffix('.log'),'text':p.read_text(errors='replace')}for p in sorted(evidence.glob('server*.log'))]
   report['serverLogAudit']=audit_log_records(logs,expected_ids={uuid.UUID(offline(n)).hex for n in [OWNER,GUEST]},actors_ok=actors_ok,owner_ok=owner_ok,closure_ok=closure_ok)
   if report['serverLogAudit']['fatalErrors']:report['success']=False
  report['finishedAt']=utc();save();total=sum(p.stat().st_size for p in evidence.rglob('*')if p.is_file());allowed=total+4096<=16*1024*1024;report['evidenceBudget']={'actualBytesBeforeFinalReceipt':total,'maximumBytes':16*1024*1024,'files':{p.relative_to(evidence).as_posix():p.stat().st_size for p in evidence.rglob('*')if p.is_file()}};report['artifactUploadAllowed']=allowed
  if not allowed:report['success']=False;report['errors'].append('Evidence exceeds16MiB; upload withheld, no truncation')
  save()
  if os.environ.get('GITHUB_OUTPUT'):
   with open(os.environ['GITHUB_OUTPUT'],'a')as out:out.write('upload_allowed='+str(allowed).lower()+'\n')
 print(json.dumps({'success':report['success'],'checks':len(report['checks']),'receipt':str(evidence/'CAT_NATIVE_ACTUAL.json'),'humanClientProven':False,'bedrockProven':False,'liveInstalled':False}));return 0 if report['success']else 1
if __name__=='__main__':raise SystemExit(main())
