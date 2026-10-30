"""Hosted-CI-only generated baseline -> copied world, real Java/Geyser clients. No private world upload."""
from pathlib import Path
import os,sys,subprocess,socket,struct,time,secrets,shutil,json,hashlib,urllib.request,zipfile,traceback
ROOT=Path(__file__).resolve().parents[1];RUN=ROOT/'ci_runtime';RUN.mkdir(exist_ok=False)
if os.environ.get('GITHUB_ACTIONS')!='true':raise RuntimeError('This route is only for hosted CI; local runs use the load governor.')
JAVA='java';children=[];events=[];password=secrets.token_hex(24);report={'scope':'Fresh generated CI baseline copied before mod tests; not a Bloom clone or Xbox visual acceptance'}
def fetch(url,dest,algorithm,expected):
 urllib.request.urlretrieve(url,dest);actual=hashlib.new(algorithm,dest.read_bytes()).hexdigest()
 if actual!=expected:raise RuntimeError('Download hash mismatch: '+url)
 report.setdefault('downloads',[]).append({'url':url,algorithm:actual});return dest
def urljson(url):
 with urllib.request.urlopen(url,timeout=90)as response:return json.load(response)
class RC:
 def __init__(self):
  self.sock=socket.create_connection(('127.0.0.1',26225),timeout=10);self.sock.settimeout(15);self.ident=1;self.send(3,password)
  while True:
   ident,typ,_=self.receive()
   if ident==-1:raise RuntimeError('CI fixture auth failed')
   if typ==2:break
 def exact(self,n):
  data=b''
  while len(data)<n:
   b=self.sock.recv(n-len(data))
   if not b:raise ConnectionError('CI server closed')
   data+=b
  return data
 def send(self,typ,text):
  data=struct.pack('<ii',self.ident,typ)+text.encode()+b'\0\0';self.sock.sendall(struct.pack('<i',len(data))+data)
 def receive(self):
  data=self.exact(struct.unpack('<i',self.exact(4))[0]);return *struct.unpack('<ii',data[:8]),data[8:-2].decode('utf8','replace')
 def command(self,text):
  self.ident+=1;self.send(2,text)
  while True:
   ident,typ,out=self.receive()
   if ident==self.ident:events.append({'command':text,'response':out});return out
 def close(self):self.sock.close()
def spawn(name,args,cwd):
 stream=(RUN/(name+'.log')).open('w',encoding='utf8');p=subprocess.Popen(args,cwd=cwd,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT);children.append(p);return p
def stop(server):
 try:
  r=RC();r.command('save-all flush');r.command('stop');r.close()
 except Exception:pass
 try:server.wait(timeout=40)
 except subprocess.TimeoutExpired:server.terminate();server.wait(timeout=15)
 report.setdefault('owned_server_exits',[]).append(server.returncode)
def start(level,fabric,phase):
 props={'server-ip':'127.0.0.1','server-port':'26224','enable-rcon':'true','rcon.port':'26225','rcon.password':password,'online-mode':'false','enforce-secure-profile':'false','network-compression-threshold':'-1','enable-query':'false','max-players':'3','spawn-protection':'0','view-distance':'2','simulation-distance':'2','difficulty':'peaceful','gamemode':'survival','level-name':level,'level-type':'minecraft:flat','generate-structures':'false','max-tick-time':'120000','require-resource-pack':'false','motd':'NorthStar Gear CI COPY ONLY','generator-settings':json.dumps({'biome':'minecraft:plains','layers':[{'block':'minecraft:bedrock','height':1},{'block':'minecraft:dirt','height':2},{'block':'minecraft:grass_block','height':1}]})}
 (RUN/'server.properties').write_text('\n'.join(k+'='+v for k,v in props.items())+'\n');(RUN/'eula.txt').write_text('eula=true\n')
 p=spawn(phase,[JAVA,'-XX:ActiveProcessorCount=2','-Xms256M','-Xmx1500M','-Djava.awt.headless=true','-jar','fabric-server-launch.jar' if fabric else 'server.jar','nogui'],RUN)
 end=time.monotonic()+180
 while time.monotonic()<end:
  if p.poll()is not None:raise RuntimeError('Owned '+phase+' exited '+str(p.returncode))
  try:r=RC();r.command('tick unfreeze');r.command('gamerule doMobSpawning false');r.close();return p
  except OSError:time.sleep(.5)
 raise TimeoutError('CI fixture server readiness: '+phase)
def test(name):
 p=subprocess.run(['node','--test','protocol_tests/'+name+'_inventory.test.cjs'],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf8',timeout=280)
 (RUN/(name+'_protocol.tap')).write_text(p.stdout);print(p.stdout,flush=True);report[name+'_exit_code']=p.returncode
try:
 meta=urljson('https://piston-meta.mojang.com/mc/game/version_manifest_v2.json');version=next(v for v in meta['versions']if v['id']=='1.21.1');entry=urljson(version['url'])['downloads']['server'];fetch(entry['url'],RUN/'server.jar','sha1',entry['sha1'])
 fetch('https://meta.fabricmc.net/v2/versions/loader/1.21.1/0.16.5/1.0.1/server/jar',RUN/'fabric-server-launch.jar','sha256','243ac92e0ddb12b031218d46d71f211d99d4d61a73fb2538bf73beee1ab37556')
 baseline=start('baseline',False,'baseline');stop(baseline);shutil.copytree(RUN/'baseline',RUN/'world');report['world_copy']={'baseline_level_dat_sha256':hashlib.sha256((RUN/'baseline/level.dat').read_bytes()).hexdigest(),'copy_level_dat_sha256':hashlib.sha256((RUN/'world/level.dat').read_bytes()).hexdigest()}
 if report['world_copy']['baseline_level_dat_sha256']!=report['world_copy']['copy_level_dat_sha256']:raise RuntimeError('World copy hash mismatch')
 mods=RUN/'mods';mods.mkdir();shutil.copy2(ROOT/'build/libs/northstar-server-gear-0.1.0-prototype.jar',mods/'northstar-server-gear-0.1.0-prototype.jar')
 fetch('https://cdn.modrinth.com/data/P7dR8mSH/versions/aUrTRV7H/fabric-api-0.116.14%2B1.21.1.jar',mods/'fabric-api.jar','sha1','1bc9caf399a9eadddaec3215e31594ca40fc9485')
 # common.cjs expects the standard local fixture home; symlink only within this fresh CI checkout.
 (ROOT/'runtime_copy_v01').symlink_to(RUN,target_is_directory=True);(RUN/'local_rcon.secret').write_text(password)
 server=start('world',True,'fabric_server');test('java')
 for folder in ['geyser','viaproxy']:(RUN/folder).mkdir()
 geyser=fetch('https://download.geysermc.org/v2/projects/geyser/versions/2.11.2/builds/1234/downloads/standalone',RUN/'geyser/Geyser-Standalone.jar','sha256','931ab217ee1eb868dac3cdcb79799d8bb3987912e1677d9f7047cfd83e4d1152')
 via=fetch('https://github.com/ViaVersion/ViaProxy/releases/download/v3.4.12/ViaProxy-3.4.12.jar',RUN/'viaproxy/ViaProxy-3.4.12.jar','sha256','32ce9ad871aeb03286823c29da262ebd75992864e7857db283f103525c7fc0cb')
 # New test-only configs, no account or cached-login files are copied.
 (RUN/'viaproxy/ViaProxy.yml').write_text('bind-address: 127.0.0.1:26226\ntarget-address: 127.0.0.1:26224\ntarget-version: 1.21-1.21.1\nproxy-online-mode: false\nauth-method: NONE\nignore-protocol-translation-errors: false\n')
 (RUN/'geyser/config.yml').write_text('bedrock:\n  address: 127.0.0.1\n  port: 19224\njava:\n  address: 127.0.0.1\n  port: 26226\n  auth-type: offline\nenable-metrics: false\nsaved-user-logins: []\nadvanced:\n  bedrock:\n    validate-bedrock-login: false\nconfig-version: 7\n')
 spawn('viaproxy',[JAVA,'-XX:ActiveProcessorCount=2','-Xmx384M','-Djava.awt.headless=true','-jar',via.name,'config','ViaProxy.yml'],via.parent)
 spawn('geyser',[JAVA,'-XX:ActiveProcessorCount=2','-Xmx512M','-Djava.awt.headless=true','-jar',geyser.name,'--nogui'],geyser.parent);time.sleep(12);test('bedrock');stop(server)
 report['passed']=report.get('java_exit_code')==0 and report.get('bedrock_exit_code')==0
except BaseException:report.update(passed=False,error=traceback.format_exc());print(report['error'],file=sys.stderr)
finally:
 for p in reversed(children):
  if p.poll()is None:
   try:p.terminate();p.wait(timeout=15)
   except subprocess.TimeoutExpired:p.kill();p.wait(timeout=10)
 report['owned_children']=[{'pid':p.pid,'exit_code':p.poll()}for p in children];(ROOT/'CI_PROTOCOL_ACTUAL.json').write_text(json.dumps(report,indent=2));(ROOT/'CI_COMMANDS_ACTUAL.json').write_text(json.dumps(events,indent=2));print(json.dumps(report,indent=2),flush=True)
raise SystemExit(0 if report.get('passed')else 1)
