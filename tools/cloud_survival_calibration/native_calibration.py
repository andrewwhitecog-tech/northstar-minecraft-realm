"""Real 26.3 Fabric/Flan held-dig calibration. Default SOURCE ONLY.
Execution is restricted to an explicitly reviewed standard PUBLIC GitHub Linux runner.
No private world, player, account, config, launcher or workstation native process is used.
"""
from __future__ import annotations
import argparse, base64, datetime, hashlib, json, math, os, platform, re, secrets, shutil, socket, struct, subprocess, sys, time, traceback, uuid
from pathlib import Path
from download_runtime import prepare, arguments, file_hash, require
from nbt_region import block_state, read_dat, fresh_servers_dat
HOME=Path(__file__).resolve().parent
TARGETS=[('permitted_a',(4,65,24),False),('protected_b',(24,65,24),True),('permitted_c',(44,65,24),False)]
DEFAULT_PERMS=['flan:can_stay','flan:drop','flan:portal','flan:flight','flan:enderchest','flan:enchantment','flan:lock_items','flan:snow_golem','flan:enderman']
EXPECTED_BONE={'Name':'minecraft:bone_block','Properties':{'axis':'y'}}

def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(path,value):Path(path).write_text(json.dumps(value,indent=2)+'\n',encoding='utf8')
def hosted_gate():
    require(not any(k in os.environ for k in ('WSL_DISTRO_NAME','WSL_INTEROP')) and 'microsoft' not in platform.release().lower(),'No WSL/Microsoft-kernel native admission')
    require(os.name=='posix' and sys.platform=='linux','No local/Windows native admission')
    want={'GITHUB_ACTIONS':'true','CI':'true','RUNNER_ENVIRONMENT':'github-hosted','RUNNER_OS':'Linux','NSP_PUBLIC_REPOSITORY':'true','NSP_ALLOW_CLOUD_SURVIVAL_CALIBRATION':'1','GITHUB_REPOSITORY':'andrewwhitecog-tech/northstar-minecraft-realm'}
    require(all(os.environ.get(k)==v for k,v in want.items()),'Explicit approved public hosted context absent')
    require(Path(os.environ.get('GITHUB_WORKSPACE','/')).resolve().is_relative_to('/home/runner/work'),'Not a hosted workspace')
    require(os.environ.get('GITHUB_RUN_ID','').isdigit(),'Hosted run ID absent')

def offline_uuid(name):
    b=bytearray(hashlib.md5(('OfflinePlayer:'+name).encode()).digest());b[6]=(b[6]&15)|48;b[8]=(b[8]&63)|128
    return uuid.UUID(bytes=bytes(b))

def route(run_id,label,target,protected,limits):
    prefix=run_id+'_'+label
    steps=[{'slot':0},{'wait':40},{'mark':prefix+'_ready'},{'await':prefix+'_ready','ticks':limits['awaitTicks']},
           {'dighold':list(target),'face':'SOUTH','ticks':limits['holdTicks']},{'wait':120},
           {'mark':prefix+'_after'},{'await':prefix+'_after','ticks':limits['awaitTicks']}]
    if protected:steps += [{'dighold':list(target),'face':'SOUTH','ticks':3},{'mark':prefix+'_resync'},{'await':prefix+'_resync','ticks':limits['awaitTicks']}]
    steps += [{'shot':prefix}]
    return steps

def parse_score(raw,name):
    m=re.fullmatch(re.escape(name)+r' has (-?\d+) \[nspcal\]',raw)
    require(m is not None,'Unknown authoritative score response: '+raw)
    return int(m.group(1))

def parse_pos(raw):
    m=re.search(r'(?:contents|entity data): \[([^\[\]]+)\]$',raw)
    require(m is not None,'Unknown authoritative position response: '+raw)
    pieces=m.group(1).split(',');require(len(pieces)==3,'Position vector shape')
    vals=[]
    for p in pieces:
        p=p.strip();require(re.fullmatch(r'[-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?[dDfF]?',p) is not None,'Position numeric shape')
        v=float(p.rstrip('dDfF'));require(math.isfinite(v),'Non-finite player position');vals.append(v)
    return vals

class Rcon:
    def __init__(self,port,password):
        self.s=socket.create_connection(('127.0.0.1',port),timeout=2);self.s.settimeout(10);self.i=1;self.send(3,password)
        for _ in range(3):
            i,t,b=self.receive();require(i!=-1,'Owned RCON authentication refused')
            if i==1 and t==2:break
        else:raise RuntimeError('Owned RCON auth response absent')
    def exact(self,n):
        out=b''
        while len(out)<n:
            b=self.s.recv(n-len(out))
            if not b:raise ConnectionError('Owned RCON closed')
            out+=b
        return out
    def send(self,t,body):
        b=struct.pack('<ii',self.i,t)+body.encode()+b'\0\0';self.s.sendall(struct.pack('<i',len(b))+b)
    def receive(self):
        n=struct.unpack('<i',self.exact(4))[0];require(10<=n<=4194304,'RCON packet length');b=self.exact(n)
        require(b[-2:]==b'\0\0','RCON terminator');i,t=struct.unpack('<ii',b[:8]);return i,t,b[8:-2].decode()
    def cmd(self,text):
        self.i+=1;self.send(2,text);parts=[]
        for _ in range(64):
            i,t,b=self.receive();require(i==self.i and t==0,'RCON response identity');parts.append(b)
            if len(b.encode())<4096:return ''.join(parts)
        raise RuntimeError('RCON response bound')
    def close(self):self.s.close()

def payload_path(relative):
    require(isinstance(relative,str),'Payload path must be text')
    part=Path(relative)
    require(bool(part.parts) and not part.is_absolute() and not part.drive and '..' not in part.parts,'Payload alias/escape')
    raw=HOME/part
    # Check the unresolved entry AND every parent before resolve() erases aliases.
    for candidate in (raw,*raw.parents):
        require(not candidate.is_symlink() and not getattr(candidate,'is_junction',lambda:False)(),'Payload alias/escape')
    resolved=raw.resolve()
    require(resolved.is_relative_to(HOME.resolve()),'Payload alias/escape')
    return resolved

def validate_payload(reviewed=None):
    p=payload_path('PAYLOAD.json')
    if reviewed:require(file_hash(p)==reviewed,'Reviewed source payload drift')
    manifest=json.loads(p.read_text());require(manifest['nativeExecution']=='NOT_RUN','Prepared payload must not claim native execution')
    for relative,expected in manifest['files'].items():
        path=payload_path(relative)
        require(file_hash(path)==expected,'Source payload drift: '+relative)
    lock=json.loads(payload_path('LOCK.json').read_text());h=lock['harness'];require(file_hash(payload_path(h['path']))==h['sha256'],'Own compiled harness drift')
    require(h['sha256']=='b19fefcfee9980099dbf3ebd8426fe8da1f13346c37c347723b6ebc4cc99b532','Unreviewed mining harness')
    return lock

def execute(lock):
    hosted_gate();os.nice(19)
    for port in (27091,27092):
        with socket.socket() as s:s.bind(('127.0.0.1',port))
    require(shutil.which('java') and shutil.which('Xvfb'),'Hosted Java25 or Xvfb absent; no silent fake client')
    v=subprocess.run(['java','-version'],capture_output=True,text=True,timeout=10)
    require(v.returncode==0 and '25.0.5' in v.stderr+v.stdout,'Pinned Java patch differs')
    run_id='cal'+secrets.token_hex(4);name='Cal'+secrets.token_hex(4);player_uuid=offline_uuid(name)
    root=HOME/'runs'/run_id;root.mkdir(parents=True,exist_ok=False)
    result={'schema':'northstar.real-survival-calibration.v1','startedUtc':utc(),'status':'NOT_RUN','nativeExecution':False,'holdClearance':False,
            'runId':run_id,'player':{'name':name,'uuid':str(player_uuid),'freshOfflineIdentity':True},'legs':[],'checks':[],'commands':[],'errors':[]}
    report=root/'ACTUAL.json';procs=[];logs=[];r=None;server=None;client=None
    def write():save(report,result)
    def check(label,ok,detail=None):
        result['checks'].append({'utc':utc(),'label':label,'pass':bool(ok),'actual':detail});write();require(ok,'Native calibration check failed: '+label)
    def cmd(text):
        answer=r.cmd(text);result['commands'].append({'utc':utc(),'command':text,'response':answer});write();return answer
    def score(name):return parse_score(cmd('scoreboard players get '+name+' nspcal'),name)
    def test(condition):
        cmd('scoreboard players reset #probe nspcal');cmd('execute store success score #probe nspcal run execute '+condition);return score('#probe')==1
    def game_tick():
        cmd('scoreboard players reset #tick nspcal');cmd('execute store result score #tick nspcal run time query gametime');return score('#tick')
    def wait_for(predicate,seconds,why):
        deadline=min(end,time.monotonic()+seconds)
        while time.monotonic()<deadline:
            if server is not None:require(server.poll() is None,'Owned server exited')
            if client is not None:require(client.poll() is None,'Real client exited before proof: inspect client.actual.log')
            if predicate():return
            time.sleep(.25)
        raise RuntimeError(why)
    def rows():
        p=route_dir/'walk_log.json'
        if not p.exists():return []
        for attempt in range(5):
            try:out=json.loads(p.read_text());break
            except json.JSONDecodeError:
                if attempt==4:raise RuntimeError('Real client log remained truncated across bounded retries')
                time.sleep(.02)
        require(isinstance(out,list),'Client log schema')
        require(not any(x.get('what') in ('ERROR','STUCK','AWAIT_TIMEOUT') for x in out),'Fatal real harness row; no later leg allowed')
        return out
    def marker(mark):return next((x for x in rows() if x.get('what')=='MARK' and x.get('value')==mark),None)
    def ack(mark):
        p=route_dir/('ack_'+mark);require(not p.exists(),'Stale ACK refused');tmp=p.with_suffix('.tmp');tmp.write_text(utc());tmp.replace(p)
    def tool(expected_damage):
        item=cmd('data get entity '+name+' SelectedItem')
        check('same owned wooden pickaxe selected',test('if items entity '+name+' weapon.mainhand minecraft:wooden_pickaxe[minecraft:custom_data~{calibration_tool:"'+run_id+'"}]'),item)
        exists=test('if data entity '+name+' SelectedItem.components."minecraft:damage"')
        damage=0
        if exists:
            cmd('scoreboard players reset #damage nspcal');cmd('execute store result score #damage nspcal run data get entity '+name+' SelectedItem.components."minecraft:damage"');damage=score('#damage')
        check('authoritative tool damage matches prior leg',damage==expected_damage,{'damage':damage,'expected':expected_damage,'item':item})
        return {'damage':damage,'item':item}
    def identity(expected_damage):
        check('same non-op survival living player',test('if entity @a[name='+name+',gamemode=survival]') and not json.loads((srv/'ops.json').read_text()),{'ops':json.loads((srv/'ops.json').read_text())})
        check('alive',not test('if entity @a[name='+name+',nbt={Health:0.0f}]'))
        uuid_ints=[int.from_bytes(player_uuid.bytes[i:i+4],'big',signed=True) for i in range(0,16,4)]
        check('offline player UUID unchanged',test('if data entity '+name+' {UUID:[I;'+','.join(map(str,uuid_ints))+']}'))
        return tool(expected_damage)
    def eyes():
        tag=run_id+'_eye';cmd('execute as '+name+' at @s anchored eyes run summon minecraft:marker ^ ^ ^ {Tags:["'+tag+'"]}')
        try:return parse_pos(cmd('data get entity @e[type=minecraft:marker,tag='+tag+',limit=1] Pos'))
        finally:cmd('kill @e[type=minecraft:marker,tag='+tag+']')
    def convergence(row,target,stand,expected_damage):
        server_pos=parse_pos(cmd('data get entity '+name+' Pos'));client_pos=row.get('pos')
        check('real client/server stand converged',isinstance(client_pos,list) and len(client_pos)==3 and math.dist(server_pos,client_pos)<=.25 and math.dist(server_pos,stand)<=.15 and row.get('onGround') is True,{'server':server_pos,'client':client_pos,'stand':stand})
        check('server feet/head clear and floor solid',test('if block '+f'{target[0]} 65 26 minecraft:air') and test('if block '+f'{target[0]} 66 26 minecraft:air') and test('if block '+f'{target[0]} 64 26 minecraft:stone'))
        eye=eyes();cmd('scoreboard players reset #range nspcal');cmd('execute store result score #range nspcal run attribute '+name+' minecraft:block_interaction_range get 1000');reach=score('#range')/1000
        center=[x+.5 for x in target];distance=math.dist(eye,center);check('measured server eye within actual block reach',0<reach<=10 and distance<=reach-.1,{'eye':eye,'distance':distance,'range':reach})
        cells={tuple(math.floor(a+(b-a)*k/40) for a,b in zip(eye,center)) for k in range(40)};cells.discard(tuple(target))
        check('line of sight to exposed target',all(test('if block '+' '.join(map(str,p))+' minecraft:air') for p in sorted(cells)),{'rayCells':sorted(cells)})
        identity(expected_damage)
        return {'server':server_pos,'client':client_pos,'eye':eye,'reach':reach,'target':target}
    def persisted(target,want):
        cmd('save-all flush');state=block_state(world,*target);check('saved region has exact fixture state',state==want,{'target':target,'saved':state,'expected':want});return state
    def settle(target,protected):
        first=game_tick();start=time.monotonic()
        def ready():
            check('server target remains expected during settle',test('if block '+' '.join(map(str,target))+(' minecraft:bone_block[axis=y]' if protected else ' minecraft:air')))
            return time.monotonic()-start>=lock['limits']['settleSeconds'] and game_tick()-first>=lock['limits']['settleServerTicks']
        wait_for(ready,30,'Authoritative server did not advance enough settled ticks')
    end=time.monotonic()+lock['limits']['nativeSeconds']
    try:
        runtime=prepare(root/'runtime',lock);end=time.monotonic()+lock['limits']['nativeSeconds'];result['runtime']={'downloadedBytes':runtime['downloaded_bytes'],'assets':runtime['asset_objects']};write()
        srv=root/'server';world=srv/'world';profile=root/'client';route_dir=root/'route'
        for p in (srv,profile/'mods',route_dir):p.mkdir(parents=True,exist_ok=True)
        claim={'ID':str(uuid.uuid4()),'Name':'Owned calibration protected bay','PosxXzZY':[16,31,16,31,-64],'Home':[24,65,26],'Potions':{},'AllowedEntries':{},'GlobalPerms':DEFAULT_PERMS,'PermGroup':{}}
        claims=world/'dimensions/minecraft/overworld/data/claims/!AdminClaims.json';claims.parent.mkdir(parents=True);save(claims,[claim]);result['claims']=[claim]
        (srv/'ops.json').write_text('[]\n');password=secrets.token_hex(24)
        props={'server-ip':'127.0.0.1','server-port':27091,'enable-rcon':'true','rcon.port':27092,'rcon.password':password,'online-mode':'false','enforce-secure-profile':'false','max-players':1,'level-name':'world','level-seed':1,'level-type':'minecraft:flat','generator-settings':json.dumps({'layers':[{'height':1,'block':'minecraft:bedrock'},{'height':2,'block':'minecraft:dirt'},{'height':1,'block':'minecraft:grass_block'}],'biome':'minecraft:plains'}),'generate-structures':'false','difficulty':'peaceful','spawn-protection':0,'view-distance':2,'simulation-distance':2,'pause-when-empty-seconds':0,'max-tick-time':60000,'broadcast-rcon-to-ops':'false','motd':'Owned calibration only'}
        (srv/'server.properties').write_text('\n'.join(k+'='+str(v).replace(':','\\:') for k,v in props.items())+'\n');(srv/'eula.txt').write_text('eula=true\n')
        (srv/'mods').mkdir();api=runtime['mods']['0.165.0+26.3'];flan=runtime['mods']['26.3-1.12.8.b-fabric']
        shutil.copyfile(api,srv/'mods/fabric-api.jar');shutil.copyfile(flan,srv/'mods/flan.jar');shutil.copyfile(api,profile/'mods/fabric-api.jar');shutil.copyfile(HOME/lock['harness']['path'],profile/'mods/nsp-route-walk.jar')
        env={k:v for k,v in os.environ.items() if k not in ('JAVA_TOOL_OPTIONS','_JAVA_OPTIONS','JDK_JAVA_OPTIONS','CLASSPATH')}
        def launch(args,cwd,logname,extra=None):
            f=(root/logname).open('xb');logs.append(f);p=subprocess.Popen(args,cwd=cwd,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,env=dict(env,**(extra or {})));procs.append(p);return p
        server=launch(['java','-Xms256M','-Xmx1G','-XX:ActiveProcessorCount=1','-Djava.awt.headless=true','-cp',runtime['server_classpath'],runtime['server_profile']['mainClass'],'--nogui'],srv,'server.actual.log')
        result.update(nativeExecution=True,status='RUNNING',serverPid=server.pid);write()
        deadline=time.monotonic()+120
        while time.monotonic()<deadline:
            require(server.poll() is None,'Fabric server exited before readiness')
            try:r=Rcon(27092,password);break
            except (OSError,RuntimeError):time.sleep(.5)
        require(r is not None,'Fabric server RCON readiness timeout')
        cmd('scoreboard objectives add nspcal dummy');cmd('forceload add 0 16 63 31')
        wait_for(lambda:all(test('if loaded '+str(target[0])+' 65 24') for _,target,_ in TARGETS),30,'Fixture chunks never actually loaded')
        cmd('fill 0 64 16 63 64 31 minecraft:stone');cmd('fill 0 65 16 63 69 31 minecraft:air')
        for label,target,protected in TARGETS:cmd('setblock '+' '.join(map(str,target))+' minecraft:bone_block[axis=y] replace')
        display=':'+str(90+secrets.randbelow(100));check('own X display number unused',not Path('/tmp/.X11-unix/X'+display[1:]).exists())
        x=launch(['Xvfb',display,'-screen','0','800x450x24','-nolisten','tcp','+extension','GLX','+render','-noreset'],root,'xvfb.actual.log');time.sleep(1);check('Xvfb is alive',x.poll() is None)
        extra={'DISPLAY':display,'LIBGL_ALWAYS_SOFTWARE':'1','GALLIUM_DRIVER':'llvmpipe','ALSOFT_DRIVERS':'null'}
        if shutil.which('glxinfo'):
            g=subprocess.run(['glxinfo','-B'],env=dict(env,**extra),capture_output=True,text=True,timeout=20);result['glxinfo']={'exit':g.returncode,'output':g.stdout+g.stderr};write();check('Mesa OpenGL preflight succeeds',g.returncode==0)
        (profile/'options.txt').write_text('renderDistance:2\nsimulationDistance:2\nmaxFps:20\nenableVsync:false\npauseOnLostFocus:false\nskipMultiplayerWarning:true\nonboardAccessibility:false\nsoundCategory_master:0.0\nguiScale:2\n')
        fresh_servers_dat(profile/'servers.dat','127.0.0.1:27091')
        values={'auth_player_name':name,'version_name':'26.3','game_directory':profile,'assets_root':runtime['assets'],'assets_index_name':'34','auth_uuid':player_uuid.hex,'auth_access_token':'0','clientid':'0','auth_xuid':'0','version_type':'release','resolution_width':800,'resolution_height':450,'quickPlayPath':str(profile/'quickplay.json'),'quickPlayMultiplayer':'127.0.0.1:27091','natives_directory':runtime['natives'],'launcher_name':'northstar-calibration','launcher_version':'1','classpath':runtime['client_classpath']}
        features={'has_custom_resolution':True,'has_quick_plays_support':True,'is_quick_play_multiplayer':True}
        jvm=arguments(runtime['meta']['arguments']['jvm'],values,features)+arguments(runtime['client_profile'].get('arguments',{}).get('jvm',[]),values,features)
        game=arguments(runtime['meta']['arguments']['game'],values,features)
        args=['java','-Xms256M','-Xmx2G','-XX:ActiveProcessorCount=2','-Djava.awt.headless=false','-Dfabric.noGui=true','-Dnsp.walk.dir='+str(route_dir),*jvm,runtime['client_profile']['mainClass'],*game]
        client=launch(args,profile,'client.actual.log',extra);result['clientPid']=client.pid;write()
        wait_for(lambda:test('if entity @a[name='+name+']'),180,'Real Fabric client did not join; inspect OpenGL/onboarding/auth logs')
        cmd('deop '+name);cmd('gamemode survival '+name);cmd('effect clear '+name)
        cmd('item replace entity '+name+' hotbar.0 with minecraft:wooden_pickaxe[minecraft:custom_data={calibration_tool:"'+run_id+'"}]')
        prior_damage=0
        for label,target,protected in TARGETS:
            if protected:require(result['legs'] and result['legs'][-1]['status']=='PASS','No protected leg before permitted positive control')
            stand=[target[0]+.5,65,26.5];cmd('tp '+name+' '+' '.join(map(str,stand))+' 180 25')
            prefix=run_id+'_'+label;old_len=len(rows());save(route_dir/'steps.tmp',route(run_id,label,target,protected,lock['limits']));(route_dir/'steps.tmp').replace(route_dir/'steps.json')
            wait_for(lambda:marker(prefix+'_ready') is not None,60,'Client ready mark missing')
            converged=convergence(marker(prefix+'_ready'),target,stand,prior_damage)
            check('initial target is same bone block',test('if block '+' '.join(map(str,target))+' minecraft:bone_block[axis=y]'))
            ack(prefix+'_ready')
            wait_for(lambda:marker(prefix+'_after') is not None,90,'Held dig completion mark missing')
            leg_rows=rows()[old_len:];dig=[row for row in leg_rows if row.get('what')=='DIGHOLD'];start_rows=[row for row in leg_rows if row.get('what')=='DIGSTART']
            expected_target=', '.join(map(str,target))
            check('actual client held exact target then predicted air',bool(start_rows) and len(dig)==1 and str(dig[0]['value']).startswith(expected_target+' ticks ') and 'client_sees Block{minecraft:air}' in str(dig[0]['value']),{'DIGSTART':start_rows,'DIGHOLD':dig})
            convergence(marker(prefix+'_after'),target,stand,prior_damage+(0 if protected else 1))
            settle(target,protected);state=persisted(target,EXPECTED_BONE if protected else {'Name':'minecraft:air'})
            ack(prefix+'_after')
            if protected:
                wait_for(lambda:marker(prefix+'_resync') is not None,30,'Protected resync mark missing')
                resync=[x for x in rows()[old_len:] if x.get('what')=='DIGHOLD']
                check('real client resynced to protected bone after saved server state',len(resync)==2 and 'client_sees Block{minecraft:bone_block}' in str(resync[-1]['value']),resync)
                persisted(target,EXPECTED_BONE);identity(prior_damage);ack(prefix+'_resync')
            else:prior_damage+=1
            wait_for(lambda:any(x.get('what')=='DONE' for x in rows()[old_len:]),30,'Client did not finish phase')
            result['legs'].append({'label':label,'status':'PASS','protected':protected,'target':target,'stand':converged,'toolDamage':prior_damage,'saved':state,'clientRows':rows()[old_len:]});write()
        check('three authoritative legs completed in order',len(result['legs'])==3 and [x['label'] for x in result['legs']]==[x[0] for x in TARGETS])
        result['status']='NATIVE_LEGS_PASSED_PENDING_CLEAN_SHUTDOWN'
    except BaseException:
        result['errors'].append(traceback.format_exc());result['status']='FAILED_OR_INCONCLUSIVE';traceback.print_exc()
    finally:
        # Only exact owned process handles. No taskkill/pkill/search, no foreign lease.
        if client is not None and client.poll() is None:
            client.terminate()
            try:client.wait(timeout=15)
            except subprocess.TimeoutExpired:client.kill();client.wait(timeout=10)
        if r is not None:
            try:cmd('save-all flush');cmd('stop')
            except Exception:result['cleanupError']=traceback.format_exc()
            finally:r.close()
        if server is not None:
            try:server.wait(timeout=45)
            except subprocess.TimeoutExpired:
                server.terminate()
                try:server.wait(timeout=10)
                except subprocess.TimeoutExpired:server.kill();server.wait(timeout=10)
            result['serverExit']=server.poll()
        for p in reversed(procs):
            if p.poll() is None:
                p.terminate()
                try:p.wait(timeout=10)
                except subprocess.TimeoutExpired:p.kill();p.wait(timeout=10)
        for log in logs:log.close()
        if result['status']=='NATIVE_LEGS_PASSED_PENDING_CLEAN_SHUTDOWN':
            try:
                require(result.get('serverExit')==0 and 'cleanupError' not in result,'Clean server shutdown missing')
                final={label:block_state(world,*target) for label,target,_ in TARGETS}
                require(final=={'permitted_a':{'Name':'minecraft:air'},'protected_b':EXPECTED_BONE,'permitted_c':{'Name':'minecraft:air'}},'Final persisted targets differ')
                player_files=[p for p in (world/'players'/f'{player_uuid}.dat',world/'playerdata'/f'{player_uuid}.dat') if p.is_file()];require(len(player_files)==1,'Ambiguous/missing saved player')
                player=read_dat(player_files[0]);stack=next((x for x in player['Inventory'] if x['Slot']==0),None)
                require(stack and stack['id']=='minecraft:wooden_pickaxe' and stack.get('count',1)==1,'Final saved tool missing')
                require(stack.get('components',{}).get('minecraft:damage',0)==2,'Final saved wooden pickaxe damage not2')
                require(stack.get('components',{}).get('minecraft:custom_data',{}).get('calibration_tool')==run_id,'Final saved tool identity differs')
                require(player['playerGameType']==0 and not json.loads((srv/'ops.json').read_text()),'Final saved survival/non-op lost')
                result.update(status='PASS_THREE_LEG_REAL_CLIENT_CALIBRATION',persistedFinal=final,persistedTool=stack)
            except Exception:result['status']='FAILED_PERSISTENCE_OR_SHUTDOWN';result['errors'].append(traceback.format_exc())
        result['finishedUtc']=utc();result['exitCode']=0 if result['status']=='PASS_THREE_LEG_REAL_CLIENT_CALIBRATION' else 1;write()
        print(json.dumps(result,indent=2))
        for filename in ('server.actual.log','client.actual.log','xvfb.actual.log'):
            p=root/filename
            if p.exists():print('OWN LOG '+filename+'\n'+'\n'.join(p.read_text(errors='replace').splitlines()[-60:]))
        # Public fixture screenshot only. No artifact-upload/cache service or private world upload.
        for p in sorted((root/'client/screenshots').glob('*.png'))[:3]:
            raw=p.read_bytes()
            if len(raw)>1500000:continue
            print('OWN_FIXTURE_PNG '+p.name+' '+hashlib.sha256(raw).hexdigest()+' '+str(len(raw)))
            encoded=base64.b64encode(raw).decode()
            for i in range(0,len(encoded),2000):print('PNG64 '+encoded[i:i+2000])
            print('END_OWN_FIXTURE_PNG')
    return result['exitCode']

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execute',action='store_true');ap.add_argument('--reviewed-payload-sha256');a=ap.parse_args()
    lock=validate_payload(a.reviewed_payload_sha256)
    if not a.execute:
        print(json.dumps({'status':'SOURCE_VALIDATED_NATIVE_NOT_RUN','harnessSha256':lock['harness']['sha256'],'privateWorldUploads':False,'holdsCleared':False}));return 0
    require(a.reviewed_payload_sha256 is not None,'Explicit reviewed source hash required before hosted native execution')
    return execute(lock)
if __name__=='__main__':raise SystemExit(main())
