"""Actual Minecraft 1.21.1 tests on a copied, freshly generated CI world.
No private world, credentials, desktop, or public server is used.
"""
import os,sys,json,zipfile,hashlib,subprocess,time,re,socket,struct,secrets,shutil,unittest,traceback,urllib.request,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parent
RUN=ROOT/'runtime';RUN.mkdir(exist_ok=False)
EVENTS=[];proc=None;rc=None;report={'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Fresh CI-generated baseline world copied before v3 test; not a Bloom clone, Java renderer or Xbox acceptance'}
DP=ROOT/'nsp_mobs_v3_dp_compat_v2.zip';EXPECTED='ff4167bfc3bde696d3425dd539aa8d2509020d9ac8cc5db88060810a20b8483e'
assert hashlib.sha256(DP.read_bytes()).hexdigest()==EXPECTED
class RC:
 def __init__(self,port,password):
  self.s=socket.create_connection(('127.0.0.1',port),timeout=10);self.i=20;self.send(1,3,password);ident,_=self.recv();assert ident==1
 def send(self,i,t,p):
  b=struct.pack('<ii',i,t)+p.encode()+b'\0\0';self.s.sendall(struct.pack('<i',len(b))+b)
 def exact(self,n):
  b=b''
  while len(b)<n:
   chunk=self.s.recv(n-len(b))
   if not chunk:raise ConnectionError('RCON closed')
   b+=chunk
  return b
 def recv(self):
  b=self.exact(struct.unpack('<i',self.exact(4))[0]);return struct.unpack('<i',b[:4])[0],b[8:-2].decode('utf8','replace')
 def __call__(self,cmd):
  self.i+=1;self.send(self.i,2,cmd);ident,out=self.recv();assert ident==self.i;EVENTS.append({'command':cmd,'response':out});return out
 def close(self):self.s.close()
def urljson(url):
 with urllib.request.urlopen(url,timeout=90)as f:return json.load(f)
def start(level,phase):
 global proc,rc
 props={'server-ip':'127.0.0.1','server-port':'26214','enable-rcon':'true','rcon.port':'26215','rcon.password':password,'online-mode':'false','level-name':level,'level-type':'minecraft\:flat','generator-settings':json.dumps({'biome':'minecraft:plains','layers':[{'block':'minecraft:bedrock','height':1},{'block':'minecraft:dirt','height':2},{'block':'minecraft:grass_block','height':1}]}),'generate-structures':'false','view-distance':'2','simulation-distance':'2','max-players':'2','spawn-protection':'0','difficulty':'normal','spawn-monsters':'false','spawn-animals':'false','max-tick-time':'120000'}
 if phase=='test':props['initial-enabled-packs']='vanilla,file/'+DP.name
 (RUN/'server.properties').write_text('\n'.join(k+'='+v for k,v in props.items())+'\n');(RUN/'eula.txt').write_text('eula=true\n')
 logfile=(RUN/(phase+'.log')).open('w',encoding='utf8');kwargs={'cwd':RUN,'stdout':logfile,'stderr':subprocess.STDOUT}
 if os.name=='nt':kwargs['creationflags']=0x08004000
 proc=subprocess.Popen([os.environ.get('JAVA','java'),'-XX:ActiveProcessorCount=1','-Xms128m','-Xmx1024m','-Djava.awt.headless=true','-jar',str(jar),'nogui'],**kwargs)
 end=time.monotonic()+180
 while time.monotonic()<end:
  if proc.poll()is not None:raise RuntimeError('Owned CI server exited during '+phase+'; see '+phase+'.log')
  try:rc=RC(26215,password);return
  except(OSError,ConnectionError,AssertionError):time.sleep(.3)
 raise TimeoutError('Owned CI server readiness: '+phase)
def stop():
 global proc,rc
 if rc:
  try:rc('stop')
  except(OSError,ConnectionError):pass
  rc.close();rc=None
 if proc:
  try:proc.wait(timeout=40)
  except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=15)
  report.setdefault('owned_server_exits',[]).append(proc.returncode);proc=None
try:
 meta=urljson('https://piston-meta.mojang.com/mc/game/version_manifest_v2.json');version=next(v for v in meta['versions']if v['id']=='1.21.1');version_meta=urljson(version['url']);entry=version_meta['downloads']['server'];jar=(ROOT/'server-1.21.1.jar').resolve();urllib.request.urlretrieve(entry['url'],jar)
 assert hashlib.sha1(jar.read_bytes()).hexdigest()==entry['sha1'];report['server_download']={'url':entry['url'],'sha1':entry['sha1']};password=secrets.token_urlsafe(24)
 start('baseline','baseline');rc('save-all flush');stop()
 baseline=RUN/'baseline';copy=RUN/'world_copy';shutil.copytree(baseline,copy);report['world_copy']={'source':'CI generated baseline','source_level_dat_sha256':hashlib.sha256((baseline/'level.dat').read_bytes()).hexdigest(),'copied_level_dat_sha256':hashlib.sha256((copy/'level.dat').read_bytes()).hexdigest()};assert report['world_copy']['source_level_dat_sha256']==report['world_copy']['copied_level_dat_sha256']
 (copy/'datapacks').mkdir(exist_ok=True);shutil.copy2(DP,copy/'datapacks'/DP.name);start('world_copy','test')
 for command in ['tick freeze','gamerule doMobSpawning false','gamerule mobGriefing false','gamerule doDaylightCycle false','gamerule doWeatherCycle false','forceload add 528 16 592 112']:rc(command)
 end=time.monotonic()+30
 while time.monotonic()<end:
  if 'passed'in rc('execute if loaded 528 199 16 if loaded 592 199 112').lower():break
  time.sleep(.2)
 else:raise TimeoutError('CI test arena chunk loading')
 for command in ['fill 528 199 16 592 199 112 minecraft:stone','fill 528 200 16 592 202 112 minecraft:air','fill 528 203 16 592 205 112 minecraft:air']:rc(command)
 import engine_v3_cases as cases
 with zipfile.ZipFile(DP)as z:cases.DP={n:z.read(n)for n in z.namelist()if not n.endswith('/')}
 cases.ROOT=ROOT;cases.rc=rc
 with(ROOT/'unittest_actual.log').open('w',encoding='utf8')as testlog:result=unittest.TextTestRunner(stream=testlog,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(cases.EngineV3))
 report['tests']={'run':result.testsRun,'failed':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'traces':[{'test':str(t),'trace':trace}for t,trace in result.failures+result.errors]}
 rc('save-all flush');stop();logs=(RUN/'test.log').read_text(encoding='utf8',errors='replace');report['parse_errors']=[line for line in logs.splitlines()if any(s in line for s in ['Failed to load function',"Couldn't parse",'Failed to parse'])];report['passed']=result.wasSuccessful()and not report['parse_errors']
except BaseException:report.update(passed=False,error=traceback.format_exc())
finally:
 stop();report['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();(ROOT/'ACTUAL_PACK_ENGINE.json').write_text(json.dumps(report,indent=2),encoding='utf8');(ROOT/'COMMANDS_ACTUAL.json').write_text(json.dumps(EVENTS,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in report.items()if k!='error'},indent=2));
 if report.get('error'):print(report['error'],file=sys.stderr)
raise SystemExit(0 if report.get('passed')else 1)
