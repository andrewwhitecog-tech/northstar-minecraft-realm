"""Source-only by default; fresh public-hosted real Minecraft client capture, never live install."""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,math,os,pathlib,re,secrets,select,shutil,signal,socket,subprocess,sys,time,traceback,uuid,zipfile
HOME=pathlib.Path(__file__).resolve().parent;REPO=HOME.parents[1];RUNTIME=REPO/'tools/cloud_survival_calibration'
CAM='CatCaptureCam';OWNER='CatProofOwner';CAT='@e[type=minecraft:cat,tag=nsp_capture.main,limit=1]'
IDS=['domestic_bengal','domestic_maine_coon','domestic_sphynx','fantasy_obsidian_rainbow']
def need(v,m):
 if not v:raise RuntimeError(m)
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def js(p,v):
 p=pathlib.Path(p);t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(v,indent=2)+'\n');t.replace(p)
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def source_guard(capture,cat,native):
 need(re.fullmatch('[0-9a-f]{64}',capture or '')and sha(HOME/'CAPTURE_SOURCE.json')==capture,'Exact reviewed capture packet required')
 for rel,pin in json.loads((HOME/'CAPTURE_SOURCE.json').read_text())['files'].items():
  p=(REPO/rel).resolve();need(not pathlib.Path(rel).is_absolute()and '..'not in pathlib.Path(rel).parts and p.is_relative_to(REPO)and p.is_file()and not p.is_symlink()and sha(p)==pin,'Capture source drift: '+rel)
 n=load('nsp_capture_native',REPO/'tools/cat_instincts/native_component_probe.py');n.source_guard(native,cat);return n

def main():
 a=argparse.ArgumentParser(description=__doc__)
 for name in ['capture','cat','native','coat-source']:a.add_argument('--reviewed-'+name+'-sha256',required=True)
 a.add_argument('--execute',action='store_true');a.add_argument('--expected-commit');a.add_argument('--cat-build-receipt',type=pathlib.Path);a.add_argument('--coat-build-receipt',type=pathlib.Path);a.add_argument('--representative-build-receipt',type=pathlib.Path);a.add_argument('--reviewed-representative-adapter-sha256');a.add_argument('--output',type=pathlib.Path);args=a.parse_args()
 n=source_guard(args.reviewed_capture_sha256,args.reviewed_cat_sha256,args.reviewed_native_sha256)
 if not args.execute:print(json.dumps({'sourceVerified':True,'executed':False,'clientVerified':False}));return 0
 need(sha(REPO/'tools/cat_menagerie/PUBLIC_EXPORT_SOURCE.json')==args.reviewed_coat_source_sha256,'Reviewed coat source packet drift');sys.path.insert(0,str(REPO/'tools/cat_menagerie'));ex=load('nsp_capture_export',REPO/'tools/cat_menagerie/run_hosted_export.py');ex.source_guard()
 commit=n.hosted_guard(args.expected_commit);workspace=pathlib.Path(os.environ['GITHUB_WORKSPACE']).resolve();root=args.output.resolve();temp=pathlib.Path(os.environ['RUNNER_TEMP']).resolve()
 need(root.is_relative_to(workspace)and root!=workspace and root.name.startswith('cat-client-')and not root.exists(),'Fresh isolated workspace output required for existing graphics helpers')
 for p in [args.cat_build_receipt,args.coat_build_receipt]:need(p is not None and p.resolve().is_relative_to(temp)and p.is_file()and not p.is_symlink(),'Actual same-run hosted input receipt required')
 build=json.loads(args.cat_build_receipt.read_text());need(build['success']is True and build['commit']==commit and build['sourcePacketSha256']==args.reviewed_cat_sha256,'Current same-run source build required');counts=build['junitActual'];need(counts['tests']>0 and all(counts[k]==0 for k in ['failures','errors','skipped']),'Clean actual JUnit suite required')
 jar=(args.cat_build_receipt.parent/build['jar']['name']).resolve();need(jar.is_relative_to(args.cat_build_receipt.parent.resolve())and sha(jar)==build['jar']['sha256'],'Actual source JAR mismatch')
 coat=json.loads(args.coat_build_receipt.read_text());coatroot=args.coat_build_receipt.parent.resolve();exported=json.loads((coatroot.parent/'HOSTED_EXPORT_ACTUAL.json').read_text());need(exported['passed']is True and exported['sourcePacketSha256']==args.reviewed_coat_source_sha256,'Actual same-run original coat export required');need(coat['schema']=='northstar.cat-coat-build.v1'and coat['customCoatsCompiled']==61 and len(coat['files'])==185 and not coat['bedrockAuthoringIncluded'],'Exact compiled61 Java-coat packet required')
 actual={p.relative_to(coatroot).as_posix()for p in coatroot.rglob('*')if p.is_file()};need(actual==set(coat['files'])|{'BUILD_ACTUAL.json'},'Unexpected coat payload files')
 for rel,pin in coat['files'].items():
  p=(coatroot/rel).resolve();need(p.is_relative_to(coatroot)and not p.is_symlink()and p.stat().st_size==pin['bytes']and sha(p)==pin['sha256'],'Compiled coat drift: '+rel)
 representative_input=None
 if args.representative_build_receipt is not None:
  ah=REPO/'tools/cat_native_representatives';need(args.reviewed_representative_adapter_sha256==sha(ah/'PUBLIC_ADAPTER_SOURCE.json'),'Exact reviewed representative adapter required')
  base_coat_sha=sha(args.coat_build_receipt);helper=load('nsp_capture_representative_input',HOME/'representative_input.py');coatroot,coat=helper.validate_adapted_input(args.coat_build_receipt,args.representative_build_receipt,ah,args.reviewed_representative_adapter_sha256)
  representative_input={'baseBuildReceiptSha256':base_coat_sha,'adaptedBuildReceiptSha256':sha(args.representative_build_receipt),'reviewedAdapterSourceSha256':args.reviewed_representative_adapter_sha256,'changedFiles':coat['changedFiles'],'unchangedPayloadFiles':coat['unchangedPayloadFiles'],'provenance':coat['provenance']}
 root.mkdir();e=root/'evidence';e.mkdir();route=root/'route';route.mkdir();report={'commit':commit,'success':False,'errors':[],'commands':[],'phases':[],'catJar':build['jar'],'coatInputReceiptSha256':sha(args.coat_build_receipt),'representativeCoatInput':representative_input,'coatFiles':coat['files'],'scope':'fresh Java client visual component evidence only','silent':True,'humanClientProven':False,'bedrockProven':False,'defaultOffProven':False,'saveReloadProven':False,'allSpeciesProven':False,'naturalSpawnProven':False,'existingPetsChanged':False,'liveInstalled':False,'humanVisualAccepted':False,'anatomy':'Stock Java cat geometry with original custom coat CatVariants'}
 server=client=xvfb=r=None;handles=[];procs=[];end=time.monotonic()+1200
 def save():js(e/'CLIENT_CAPTURE_ACTUAL.json',report)
 def cmd(t):
  need(time.monotonic()<end,'Owned capture deadline');v=r.cmd(t);report['commands'].append({'command':t,'reply':v});need(not re.search(r'Unknown (?:or incomplete command|function|block|item|entity)|Incorrect argument|Expected (?:integer|double|float|literal)|Invalid (?:command|argument)',v,re.I),'Actual command parse failure: '+v);return v
 def observe(c):
  cmd('scoreboard players set #obs ncp 0');cmd('execute store success score #obs ncp run execute '+c);v=cmd('scoreboard players get #obs ncp');m=re.search(r'\bhas (-?\d+)\b',v);need(m is not None and int(m[1])in(0,1),'Actual boolean unreadable');return int(m[1])
 def scalar(q):
  v=cmd('data get entity '+q);m=re.search(r':\s*(-?\d+(?:\.\d+)?)[bdfLs]?\s*$',v);need(m is not None,'Actual scalar unreadable: '+v);return float(m[1])
 def pos(w):return [scalar(w+' Pos['+str(i)+']')for i in range(3)]
 def clock():
  cmd('execute store result score #capture_clock ncp run time query gametime');v=cmd('scoreboard players get #capture_clock ncp');m=re.search(r'\bhas (-?\d+)\b',v);need(m is not None,'Actual frozen tick clock unreadable');return int(m[1])
 def settle_frozen(ticks):
  start=clock();cmd('tick step '+str(ticks));wait(lambda:clock()>=start+ticks,15,'Actual frozen cleanup ticks did not advance')
 def alive():
  need(server is None or server.poll()is None,'Server exited prematurely');need(client is None or client.poll()is None,'Client exited prematurely; inspect actual logs')
  need(not (route/'CLIENT_ERROR.txt').exists(),'Actual client observer error')
 def wait(pred,secs,why):
  until=min(end,time.monotonic()+secs)
  while time.monotonic()<until:
   alive()
   if pred():return
   time.sleep(.1)
  raise RuntimeError(why)
 def rows():
  p=route/'walk_log.json'
  if not p.exists():return []
  for _ in range(5):
   try:v=json.loads(p.read_text());break
   except json.JSONDecodeError:time.sleep(.02)
  else:raise RuntimeError('Client route log stayed partial')
  need(not any(x.get('what')in('ERROR','STUCK','AWAIT_TIMEOUT')for x in v),'Actual route failed');return v
 def mark(s):return next((x for x in rows()if x.get('what')=='MARK'and x.get('value')==s),None)
 def ack(s):
  p=route/('ack_'+s);need(not p.exists(),'Stale route ACK refused');p.write_text('actual authoritative setup complete\n')
 def launch(argv,cwd,label,extra=None):
  f=(e/(label+'.log')).open('xb');handles.append(f);p=subprocess.Popen([str(v)for v in argv],cwd=cwd,env=dict(childenv,**(extra or {})),stdin=subprocess.PIPE if label=='server.actual'else subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True);procs.append((label,p));return p
 def check(label,ok,actual):report.setdefault('checks',[]).append({'label':label,'pass':bool(ok),'actual':actual});save();need(ok,'Actual check failed: '+label)
 def camera_state():
  p=route/'CLIENT_ACTUAL.json';return json.loads(p.read_text())if p.exists()else {}
 def fixture(variant,x=34.5,baby=False,tag='main',sit=False):
  t='@e[type=minecraft:cat,tag=nsp_capture.'+tag+',limit=1]';cmd('summon minecraft:cat '+str(x)+' 65 32.5 '+json.dumps({'Tags':['nsp_capture.fixture','nsp_capture.'+tag],'Age':-24000 if baby else 0,'Sitting':sit,'PersistenceRequired':True,'variant':'nsp_cat_coats:'+variant},separators=(',',':')));cmd('data modify entity '+t+' Owner set from entity '+OWNER+' UUID');v=cmd('data get entity '+t+' variant');check('actual CatVariant '+variant,'nsp_cat_coats:'+variant in v,v);age=scalar(t+' Age');check('actual baby age'if baby else'actual adult age',age<0 if baby else age>=0,age);return t
 try:
  sys.path.insert(0,str(RUNTIME));from download_runtime import prepare,arguments;from nbt_region import fresh_servers_dat;from egl_runtime import prepare_egl;from real_sdl_probe import observation_ok
  lock=json.loads((RUNTIME/'LOCK.json').read_text());need(sha(RUNTIME/lock['harness']['path'])==lock['harness']['sha256'],'Exact original recorder harness required');report['hostTools']={x:shutil.which(x) for x in ['java','javac','ffmpeg','ffprobe','Xvfb']};save();need(all(report['hostTools'].values()),'Actual hosted Java/FFmpeg/Xvfb tools required; missing='+','.join(x for x,p in report['hostTools'].items() if not p))
  childenv={k:v for k,v in os.environ.items()if k in ['PATH','JAVA_HOME','HOME','TMPDIR','LANG','LC_ALL']};os.nice(19)
  jv=subprocess.run(['java','-version'],capture_output=True,text=True,timeout=10);need(jv.returncode==0 and lock['java']in jv.stdout+jv.stderr,'Exact Java runtime required')
  runtime=prepare(root/'runtime',lock);report['runtime']={'downloadedBytes':runtime['downloaded_bytes'],'assetObjects':runtime['asset_objects'],'unusedFlanDownloaded':True,'flanInstalled':False};end=time.monotonic()+900
  classes=root/'observer-classes';classes.mkdir();javac=subprocess.run(['javac','-J-XX:ActiveProcessorCount=2','-J-Xmx512M','--release','25','-encoding','UTF-8','-proc:none','-cp',runtime['client_classpath'],'-d',str(classes),str(HOME/'src/net/northstar/capture/CaptureObserverMixin.java')],capture_output=True,text=True,timeout=120);(e/'observer_javac.stdout.log').write_text(javac.stdout);(e/'observer_javac.stderr.log').write_text(javac.stderr);report['observerJavacExit']=javac.returncode;need(javac.returncode==0,'Actual observer compilation failed')
  observer=root/'cat-capture-observer.jar'
  with zipfile.ZipFile(observer,'w',zipfile.ZIP_DEFLATED)as z:
   for p in classes.rglob('*.class'):z.write(p,p.relative_to(classes).as_posix())
   for name in ['fabric.mod.json','northstar_capture.mixins.json']:z.write(HOME/'resources'/name,name)
  srv=root/'server';profile=root/'client';(srv/'mods').mkdir(parents=True);(profile/'mods').mkdir(parents=True);(srv/'world/datapacks').mkdir(parents=True);shutil.copytree(coatroot/'java_datapack',srv/'world/datapacks/nsp_cat_coats');(profile/'resourcepacks').mkdir()
  rp=profile/'resourcepacks/nsp-cat-coats.zip'
  with zipfile.ZipFile(rp,'w',zipfile.ZIP_DEFLATED)as z:
   for p in sorted((coatroot/'java_resourcepack').rglob('*')):
    if p.is_file():z.write(p,p.relative_to(coatroot/'java_resourcepack').as_posix())
  report['selectedClientResourcePack']={'entry':'file/nsp-cat-coats.zip','sha256':sha(rp),'texturePins':{k:v for k,v in coat['files'].items()if k.endswith('.png')and any('/'+name+'.png' in k or '/'+name+'_baby.png'in k for name in IDS)}}
  for place in [srv/'mods',profile/'mods']:shutil.copyfile(jar,place/jar.name);shutil.copyfile(runtime['mods']['0.165.0+26.3'],place/'fabric-api.jar')
  carpet=json.loads((REPO/'tools/cat_instincts/fixtures/CARPET_RUNTIME.json').read_text())['files'][0];from download_runtime import Downloader;d=Downloader(root/'runtime',lock['limits']);carpetjar=d.get(carpet['url'],root/'runtime/mods'/carpet['filename'],carpet['hashes'],carpet['size']);shutil.copyfile(carpetjar,srv/'mods/carpet.jar');shutil.copyfile(RUNTIME/lock['harness']['path'],profile/'mods/route-recorder.jar');shutil.copyfile(observer,profile/'mods/observer.jar')
  def offline(name):return str(uuid.UUID(bytes=hashlib.md5(('OfflinePlayer:'+name).encode()).digest(),version=3))
  profiles=[{'name':name,'uuid':offline(name)}for name in[CAM,OWNER]];(srv/'ops.json').write_text('[]');js(srv/'whitelist.json',profiles);js(srv/'usercache.json',[{**p,'expiresOn':'2099-01-01 00:00:00 +0000'}for p in profiles]);ports=[]
  for _ in range(2):
   with socket.socket()as s:s.bind(('127.0.0.1',0));ports.append(s.getsockname()[1])
  need(ports[0]!=ports[1],'Port collision');gp,rpport=ports;password=secrets.token_hex(24);generator={'biome':'minecraft:plains','layers':[{'block':'minecraft:bedrock','height':1},{'block':'minecraft:stone','height':63}],'features':False,'lakes':False};props={'server-ip':'127.0.0.1','server-port':gp,'enable-rcon':'true','rcon.port':rpport,'rcon.password':password,'online-mode':'false','enforce-secure-profile':'false','white-list':'true','enforce-whitelist':'true','level-name':'world','level-type':'minecraft:flat','generator-settings':json.dumps(generator,separators=(',',':')),'difficulty':'normal','spawn-protection':0,'view-distance':4,'simulation-distance':4,'pause-when-empty-seconds':0,'max-players':2,'broadcast-rcon-to-ops':'false'};(srv/'server.properties').write_text(''.join(str(k)+'='+str(v)+'\n'for k,v in props.items()));(srv/'eula.txt').write_text('eula=true\n')
  server=launch(['java','-Xms256M','-Xmx2G','-XX:ActiveProcessorCount=2','-Djava.awt.headless=true','-Djava.net.preferIPv4Stack=true','-Dnsp.cat.instincts.enabled=true','-cp',runtime['server_classpath'],runtime['server_profile']['mainClass'],'--nogui'],srv,'server.actual')
  until=time.monotonic()+180
  while time.monotonic()<until:
   alive()
   try:r=n.Rcon(rpport,password);break
   except(OSError,RuntimeError):time.sleep(.5)
  need(r is not None,'Real server startup timeout');cmd('scoreboard objectives add ncp dummy');cmd('carpet commandPlayer true');cmd('gamerule minecraft:spawn_mobs false');cmd('gamerule minecraft:advance_time false');cmd('time set midnight');cmd('weather clear');cmd('forceload add 16 16 96 64');wait(lambda:all(observe('if loaded '+str(x)+' 64 '+str(z))for x in[24,40,56,72,88,96]for z in[24,40,56,64]),90,'Actual fixture chunks unavailable');cmd('fill 20 64 24 60 64 52 minecraft:polished_blackstone');cmd('fill 20 65 24 60 69 52 minecraft:air');cmd('fill 20 64 30 60 64 30 minecraft:cyan_glazed_terracotta');cmd('fill 20 64 34 60 64 34 minecraft:gold_block');cmd('fill 20 65 24 60 66 24 minecraft:amethyst_block');[cmd('setblock '+str(x)+' 64 '+str(z)+' minecraft:sea_lantern') for x in range(24,61,4) for z in [28,36,44,52]];cmd('player '+OWNER+' spawn at 32.5 65 32.5 facing 0 0 in minecraft:overworld in survival');wait(lambda:observe('if entity @a[name='+OWNER+',gamemode=survival]')==1,30,'Actual synthetic owner missing');check('owner has actual expected offline UUID',observe('if data entity '+OWNER+' {UUID:[I;'+','.join(str(int.from_bytes(uuid.UUID(offline(OWNER)).bytes[i:i+4],'big',signed=True))for i in[0,4,8,12])+']}')==1,cmd('data get entity '+OWNER+' UUID'))
  rdf,wdf=os.pipe()
  # Explicit pass_fds is required; do not leak the display pipe to Java or encoders.
  xf=(e/'xvfb.actual.log').open('xb');handles.append(xf);xvfb=subprocess.Popen(['Xvfb','-displayfd',str(wdf),'-screen','0','800x450x24','-nolisten','tcp','+extension','GLX','+render','-noreset'],pass_fds=(wdf,),cwd=root,env=childenv,stdout=xf,stderr=subprocess.STDOUT,start_new_session=True);procs.append(('xvfb',xvfb));os.close(wdf)
  try:need(select.select([rdf],[],[],10)[0],'Owned display timeout');display=':'+os.read(rdf,16).decode().strip();need(re.fullmatch(':[0-9]{1,3}',display),'Owned display malformed')
  finally:os.close(rdf)
  extra={'DISPLAY':display,'LIBGL_ALWAYS_SOFTWARE':'1','GALLIUM_DRIVER':'llvmpipe','LP_NUM_THREADS':'2','SDL_VIDEO_DRIVER':'x11','ALSOFT_DRIVERS':'null'};prep=prepare_egl(root);extra.update(prep['env']);report['egl']=prep['provenance'];selected=None;report['sdlProbes']=[]
  # Keep only reviewed nonsecret host attestations; SDL still validates their real values.
  probeenv=dict(childenv,**{k:os.environ[k]for k in ['CI','GITHUB_ACTIONS','RUNNER_ENVIRONMENT','RUNNER_OS','ImageOS','GITHUB_EVENT_NAME','GITHUB_REF','GITHUB_REPOSITORY','GITHUB_ACTOR','GITHUB_TRIGGERING_ACTOR','GITHUB_WORKSPACE','GITHUB_RUN_ID','NSP_PUBLIC_REPOSITORY','NSP_ALLOW_CLOUD_SURVIVAL_CALIBRATION']if k in os.environ})
  for mode in ['glx','egl']:
   attempt=dict(extra,SDL_VIDEO_FORCE_EGL='1'if mode=='egl'else'0');p=subprocess.run([sys.executable,'-B',str(RUNTIME/'real_sdl_probe.py'),'--execute','--native-home',runtime['natives'],'--mode',mode],env=dict(probeenv,**attempt),capture_output=True,text=True,timeout=30)
   try:o=json.loads(p.stdout)
   except ValueError:o={}
   report['sdlProbes'].append({'mode':mode,'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr});save()
   if p.returncode==0 and observation_ok(o):selected=attempt;break
  need(selected is not None,'Real SDL3 context failed; no client substitute');(profile/'options.txt').write_text('renderDistance:4\nsimulationDistance:5\nmaxFps:20\nenableVsync:false\npauseOnLostFocus:false\nskipMultiplayerWarning:true\nonboardAccessibility:false\nsoundCategory_master:0.0\nguiScale:2\nresourcePacks:["vanilla","file/nsp-cat-coats.zip"]\nincompatibleResourcePacks:[]\n');fresh_servers_dat(profile/'servers.dat','127.0.0.1:'+str(gp));values={'auth_player_name':CAM,'version_name':'26.3','game_directory':profile,'assets_root':runtime['assets'],'assets_index_name':'34','auth_uuid':uuid.UUID(offline(CAM)).hex,'auth_access_token':'0','clientid':'0','auth_xuid':'0','version_type':'release','resolution_width':800,'resolution_height':450,'quickPlayPath':str(profile/'quickplay.json'),'quickPlayMultiplayer':'127.0.0.1:'+str(gp),'natives_directory':runtime['natives'],'launcher_name':'northstar-cat-capture','launcher_version':'1','classpath':runtime['client_classpath']};features={'has_custom_resolution':True,'has_quick_plays_support':True,'is_quick_play_multiplayer':True};jvm=arguments(runtime['meta']['arguments']['jvm'],values,features)+arguments(runtime['client_profile'].get('arguments',{}).get('jvm',[]),values,features);game=arguments(runtime['meta']['arguments']['game'],values,features);report['syntheticOfflineFixture']=props.get('online-mode')=='false'and values.get('auth_access_token')=='0'and values.get('auth_player_name')==CAM;client=launch(['java','-Xms256M','-Xmx2G','-XX:ActiveProcessorCount=2','-Djava.awt.headless=false','-Dfabric.noGui=true','-Dnsp.cat.instincts.enabled=true','-Dnsp.walk.dir='+str(route),'-Dnsp.cat.capture.dir='+str(route),*jvm,runtime['client_profile']['mainClass'],*game],profile,'client.actual',selected)
  wait(lambda:observe('if entity @a[name='+CAM+']')==1 and camera_state().get('joined')is True,300,'Actual real client join failed');need('nsp-cat-coats.zip' in (e/'client.actual.log').read_text(errors='replace'),'Actual client log does not show selected custom resource pack');cmd('gamemode spectator '+CAM);check('actual no operators',json.loads((srv/'ops.json').read_text())==[],[])
  ffargs=['ffmpeg','-hide_banner','-nostdin','-loglevel','error','-f','rawvideo','-pixel_format','rgba','-video_size','{W}x{H}','-framerate','{FPS}','-i','pipe:0','-an','-vf','vflip','-c:v','libx264','-preset','ultrafast','-crf','18','-threads','2','-pix_fmt','yuv420p','-movflags','+faststart',str(e/'{NAME}.mp4')];(route/'ffmpeg_args.txt').write_text('\n'.join(ffargs)+'\n')
  for label,variant in [('return',IDS[0]),('hunt',IDS[1]),('protected',IDS[2]),('coats',IDS[3])]:
   cmd('tick freeze');cmd('kill @e[type=!minecraft:player,tag=nsp_capture.fixture]');settle_frozen(25)
   camera=[42,68,47,180,18]if label=='return'else[38.5,66.5,41,180,8]if label=='hunt'else[35,66.4,38.5,180,8]if label=='protected'else[39.5,66.6,42,180,8]
   camera_end=[40,67,45,180,18]if label=='return'else[camera[0],camera[1]-.2,camera[2]-1,180,8]
   cmd('tp '+OWNER+' 32.5 65 32.5');cmd('tp '+CAM+' '+' '.join(map(str,camera)));fixture(variant,x=50.5 if label=='return'else 34.5,sit=label=='coats')
   if label=='coats':
    for i,v in enumerate(IDS[:3]):fixture(v,36.5+i*2,tag='coat'+str(i),sit=True)
    fixture(variant,44.5,baby=True,tag='baby',sit=True)
   if label in['hunt','protected']:
    kind='minecraft:zombie'if label=='hunt'else'minecraft:villager';vx=42.5 if label=='hunt'else 35.5;tags=['nsp_capture.fixture','nsp_capture.victim']+(['nsp_cat.hostile','nsp_cat.wild']if label=='protected'else[]);cmd('summon '+kind+' '+str(vx)+' 65 32.5 '+json.dumps({'Tags':tags,'NoAI':True,'Health':100.0},separators=(',',':')));cmd('attribute @e[tag=nsp_capture.victim,limit=1] minecraft:max_health base set 100');cmd('data merge entity @e[tag=nsp_capture.victim,limit=1] {Health:100f}')
    if label=='protected':
     cmd('damage @e[tag=nsp_capture.victim,limit=1] 1 minecraft:generic');check('protected footage fixture damageable positive control',scalar('@e[tag=nsp_capture.victim,limit=1] Health')<100,scalar('@e[tag=nsp_capture.victim,limit=1] Health'));cmd('data merge entity @e[tag=nsp_capture.victim,limit=1] {Health:100f}');settle_frozen(20);check('protected fixture stays healthy during setup settling',scalar('@e[tag=nsp_capture.victim,limit=1] Health')==100,scalar('@e[tag=nsp_capture.victim,limit=1] Health'))
   # Actual pre-record render settling, then handshake holds the world frozen until recorder is live.
   prefix='capture_'+label;old=len(rows());steps=[{'hud':False},{'clouds':False},{'wait':80},{'rec':label,'fps':10},{'mark':prefix+'_recording'},{'await':prefix+'_recording','ticks':1200},{'cam':camera+camera_end,'seconds':6},{'shot':label},{'recstop':True},{'mark':prefix+'_done'},{'await':prefix+'_done','ticks':1200}];js(route/'steps.json',steps);wait(lambda:mark(prefix+'_recording')is not None,90,'Real recorder start marker missing');wait(lambda:camera_state().get('hudHidden')is True and len(camera_state().get('clientCats',[]))>=1,20,'Client has not observed actual cats/HUD state');phase={'label':label,'variant':variant,'cameraStart':camera,'cameraEnd':camera_end,'start':pos(CAT),'samples':[],'clientBefore':camera_state()};cmd('tick unfreeze');ack(prefix+'_recording');until=min(end,time.monotonic()+60)
   while mark(prefix+'_done')is None and time.monotonic()<until:
    alive();phase['samples'].append({'wallMonotonic':time.monotonic(),'cat':pos(CAT),'health':scalar('@e[tag=nsp_capture.victim,limit=1] Health')if label in['hunt','protected']else None,'targetedProtectedVictim':observe('as '+CAT+' on target if entity @s[tag=nsp_capture.victim]')if label=='protected'else None});time.sleep(.1)
   need(mark(prefix+'_done')is not None,'Real recorder did not finish');cmd('tick freeze');phase['clientAfter']=camera_state();phase['routeRows']=rows()[old:];stats=[x['value']for x in phase['routeRows']if x.get('what')=='RECSTOP'];need(len(stats)==1 and isinstance(stats[0],dict),'Actual recorder stats missing');phase['recorder']=stats[0];need(stats[0].get('ffmpegExit')==0 and not stats[0].get('error')and stats[0].get('framesWritten',0)>10 and stats[0].get('framesRepeated')==0,'Actual recorder closure/unique-frame guard failed');report['phases'].append(phase);save()
   if label=='return':check('actual return footage endpoint approached owner',math.dist(phase['samples'][-1]['cat'],[32.5,65,32.5])<4.5,phase['samples'][-1])
   if label=='hunt':check('actual captured cat health drop',any(x['health']<100 for x in phase['samples']),phase['samples'][-1])
   if label=='protected':check('actual captured NPC retains health',all(x['health']==100 and x['targetedProtectedVictim']==0 for x in phase['samples']),phase['samples'][-1])
   movie=e/(label+'.mp4');probe=subprocess.run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(movie)],capture_output=True,text=True,timeout=20);need(probe.returncode==0,'Actual ffprobe failed');media=json.loads(probe.stdout);duration=float(media['format']['duration']);need(4<duration<20 and any(s['codec_type']=='video'and s['width']==800 and s['height']==450 for s in media['streams'])and not any(s['codec_type']=='audio'for s in media['streams']),'Actual silent video format invalid');phase['ffprobe']=media;decode=subprocess.run(['ffmpeg','-v','error','-threads','2','-i',str(movie),'-f','null','-'],capture_output=True,text=True,timeout=60);need(decode.returncode==0 and not decode.stderr.strip(),'Actual full movie decode failed');phase['movie']={'sha256':sha(movie),'bytes':movie.stat().st_size}
   for i,fraction in enumerate([0,.25,.5,.75,1]):
    frame=e/(label+'_qc_'+str(i)+'.png');t=min(duration-.12,duration*fraction);q=subprocess.run(['ffmpeg','-v','error','-threads','2','-ss',str(max(0,t)),'-i',str(movie),'-frames:v','1',str(frame)],capture_output=True,text=True,timeout=20);need(q.returncode==0 and frame.is_file(),'Actual timeline frame extraction failed')
   for pic in (profile/'screenshots').glob(label+'*.png'):shutil.copyfile(pic,e/('client_'+pic.name))
   ack(prefix+'_done');wait(lambda:any(x.get('what')=='DONE'for x in rows()[old:]),10,'Route completion absent');save()
  (route/'STOP_CLIENT').write_text('normal owned shutdown\n');client.wait(timeout=45);check('actual client normal exit',client.returncode==0,{'exit':client.returncode,'observer':camera_state()});check('actual observer acknowledged owned stop',not (route/'CLIENT_ERROR.txt').exists() and camera_state().get('stopRequested') is True,camera_state());report['technicalCaptureCompleted']=True
 except BaseException:report['errors'].append(traceback.format_exc());print(report['errors'][-1],file=sys.stderr)
 finally:
  closures=[]
  if client is not None and client.poll()is None:
   try:(route/'STOP_CLIENT').write_text('normal owned cleanup\n');client.wait(timeout=30)
   except Exception:report['errors'].append('Client normal cleanup: '+traceback.format_exc())
  if server is not None and server.poll()is None:
   try:
    if r:r.cmd('save-all flush');r.cmd('stop')
    elif server.stdin:server.stdin.write(b'save-all flush\nstop\n');server.stdin.flush()
    server.wait(timeout=60)
   except Exception:report['errors'].append('Server normal cleanup: '+traceback.format_exc())
  if r:
   try:r.close()
   except OSError:pass
  for label,process in reversed(procs):
   forced=False
   if process.poll()is None:
    forced=label!='xvfb';process.terminate()
    try:process.wait(timeout=10)
    except subprocess.TimeoutExpired:forced=True;os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=10)
   gone=not n.group_alive(process.pid);closures.append({'label':label,'exit':process.returncode,'forced':forced,'groupGone':gone})
   if forced or not gone or label in['server.actual','client.actual']and process.returncode!=0:report['errors'].append('Owned process closure failed: '+str(closures[-1]))
  for handle in handles:handle.close()
  if (route/'CLIENT_ERROR.txt').exists():
   shutil.copyfile(route/'CLIENT_ERROR.txt',e/'CLIENT_OBSERVER_ERROR_ACTUAL.txt');report['errors'].append('Actual client observer error: '+(route/'CLIENT_ERROR.txt').read_text(errors='replace'))
  report['closures']=closures;report['opsAfter']=json.loads((root/'server/ops.json').read_text())if(root/'server/ops.json').exists()else None
  for name in ['server.actual','client.actual']:
   path=e/(name+'.log');raw=path.read_text(errors='replace')if path.exists()else'';lines=raw.splitlines();bad=[l for l in lines if re.search(r'/(?:ERROR|FATAL)\]|Missing (?:texture|model)|Failed to load (?:texture|model|resource)|Unable to load (?:texture|model)|Using missing texture',l,re.I)];report[name+'LogErrors']=bad;blocking=bad
   if name=='client.actual':
    try:
     policy=load('nsp_capture_offline_service_records',HOME/'offline_service_records.py');assessment=policy.audit_error_lines(raw,offline_fixture=report.get('syntheticOfflineFixture')is True);report['offlineServiceDiagnostics']=assessment['offlineServiceDiagnostics'];report['blockingClientErrorRecords']=assessment['blockingErrorRecords'];blocking=assessment['blockingLines']
    except Exception:report['errors'].append('Offline-service classification failed closed: '+traceback.format_exc())
   report[name+'BlockingErrors']=blocking
   if blocking:report['errors'].append(name+' contains actual blocking renderer/runtime errors; inspect preserved full log')
  if report['opsAfter']!=[]:report['errors'].append('Missing/changed ops state')
  report['success']=bool(report.get('technicalCaptureCompleted'))and not report['errors'];save();total=sum(p.stat().st_size for p in e.rglob('*')if p.is_file());allowed=total<=40*1024*1024;report['artifactUploadAllowed']=allowed
  if not allowed:report['errors'].append('Evidence exceeds40MiB; upload withheld without truncation');report['success']=False
  save()
  if os.environ.get('GITHUB_OUTPUT'):
   with open(os.environ['GITHUB_OUTPUT'],'a')as out:out.write('upload_allowed='+str(allowed).lower()+'\n')
 print(json.dumps({'success':report['success'],'humanVisualAccepted':False,'liveInstalled':False,'evidence':str(e)}));return 0 if report['success']else 1
if __name__=='__main__':raise SystemExit(main())
