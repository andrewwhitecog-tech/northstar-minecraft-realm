"""Actual hosted Linux Fabric/Carpet cannon COMPONENT probe. Import is inert.
No real human client, Bedrock, moving ship, full crafting chain or live-world claim.
"""
from __future__ import annotations
import argparse,copy,datetime,hashlib,importlib.util,json,os,pathlib,re,secrets,shutil,signal,socket,struct,subprocess,sys,time,traceback,uuid
HOME=pathlib.Path(__file__).resolve().parent
REPO=HOME.parents[1]
RUNTIME_HOME=REPO/'tools/cloud_survival_calibration'
REPOSITORY='andrewwhitecog-tech/northstar-minecraft-realm'
PACKET=HOME/'NATIVE_SOURCE.json'
POWDER='*[custom_data~{nsp_chain:"black_powder"}]'

def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def need(ok,message):
    if not ok:raise RuntimeError(message)
def sha(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()

def source_guard(reviewed):
    need(isinstance(reviewed,str) and re.fullmatch('[0-9a-f]{64}',reviewed),'Full reviewed native-source packet SHA256 required')
    need(sha(PACKET)==reviewed,'Reviewed native-source packet drift')
    packet=json.loads(PACKET.read_text(encoding='utf-8'))
    for relative,pin in packet['files'].items():
        path=(REPO/relative).resolve()
        need(not pathlib.Path(relative).is_absolute() and '..' not in pathlib.Path(relative).parts and path.is_relative_to(REPO.resolve()),'Unsafe source packet path')
        need(path.is_file() and not path.is_symlink() and sha(path)==pin,'Pinned native source drift: '+relative)
    return packet

def hosted_guard(expected_commit):
    need(sys.platform=='linux' and os.uname().machine=='x86_64' and os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted' and os.environ.get('RUNNER_OS')=='Linux','Actual hosted Linux runner required; no local/native fallback')
    need(os.environ.get('GITHUB_REPOSITORY')==REPOSITORY and os.environ.get('GITHUB_REF')=='refs/heads/main' and os.environ.get('GITHUB_ACTOR')=='andrewwhitecog-tech' and os.environ.get('GITHUB_EVENT_NAME')=='workflow_dispatch','Only owner manual dispatch on this public main is allowed')
    need(isinstance(expected_commit,str) and re.fullmatch('[0-9a-f]{40}',expected_commit) and os.environ.get('GITHUB_SHA')==expected_commit,'Exact reviewed workflow commit required')
    event=json.loads(pathlib.Path(os.environ['GITHUB_EVENT_PATH']).read_text(encoding='utf-8'))
    need(event.get('repository',{}).get('full_name')==REPOSITORY and event['repository'].get('private') is False,'Actual event must identify the public repository')
    head=subprocess.run(['git','rev-parse','HEAD'],cwd=REPO,check=True,capture_output=True,text=True,timeout=10).stdout.strip()
    need(head==expected_commit,'Actual checked-out source differs from reviewed commit')
    return head

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

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execute',action='store_true');ap.add_argument('--reviewed-source-sha256',required=True);ap.add_argument('--expected-commit');ap.add_argument('--pack',type=pathlib.Path);ap.add_argument('--manifest',type=pathlib.Path);ap.add_argument('--output',type=pathlib.Path)
    args=ap.parse_args();packet=source_guard(args.reviewed_source_sha256)
    if not args.execute:
        print(json.dumps({'executed':False,'sourcePacketVerified':True,'nativeVerified':False,'scope':'server/Carpet component only'}));return 0
    # Guard precedes runtime import/download/world creation/Java.
    commit=hosted_guard(args.expected_commit)
    need(args.output is not None and args.pack is not None and args.manifest is not None,'Fresh output plus exact source-built pack/manifest required')
    temp=pathlib.Path(os.environ['RUNNER_TEMP']).resolve();root=args.output.resolve()
    need(root.is_relative_to(temp) and root!=temp and not root.exists(),'Native output must be fresh below actual RUNNER_TEMP')
    pack=args.pack.resolve();manifest_path=args.manifest.resolve()
    need(pack.is_relative_to(temp) and manifest_path.is_relative_to(temp) and pack.is_dir(),'Only this hosted run source-built pack is allowed')
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    need(manifest['config']==json.loads((HOME/'demo_config.json').read_text(encoding='utf-8')) and manifest.get('native_verified') is False and manifest.get('live_installed') is False,'Exact generic source-built demo required')
    actual={p.relative_to(pack).as_posix():sha(p) for p in pack.rglob('*') if p.is_file()}
    need(actual and actual==manifest['files'] and not any(p.is_symlink() for p in pack.rglob('*')),'Source-built pack census/hash drift')
    root.mkdir();artifacts=root/'evidence';artifacts.mkdir()
    report={'schema':1,'startedAt':utc(),'commit':commit,'sourcePacketSha256':args.reviewed_source_sha256,'scope':'actual fresh loopback Fabric/Carpet server component only','checks':[],'commands':[],'errors':[],'success':False,'humanClientProven':False,'bedrockProven':False,'movingShipProven':False,'fullCraftingChainProven':False,'liveInstalled':False,'masterWrites':False,'publicWorldWrites':False}
    server=rcon=None;logs=[];password=secrets.token_hex(24);native_end=None
    def save():
        tmp=artifacts/'NATIVE_ACTUAL.json.tmp';tmp.write_text(json.dumps(report,indent=2),encoding='utf-8');tmp.replace(artifacts/'NATIVE_ACTUAL.json')
    def cmd(text):
        if native_end is not None:need(time.monotonic()<native_end,'Actual native probe deadline expired')
        reply=rcon.cmd(text);report['commands'].append({'command':text,'reply':reply,'at':utc()})
        need(re.search(r'Unknown (?:or incomplete command|function|block|item|entity)|Incorrect argument|Expected (?:integer|double|float|literal)|Invalid (?:command|argument)',reply,re.I) is None,'Actual command/function parse failure: '+reply)
        return reply
    def check(ok,label,evidence):
        report['checks'].append({'pass':bool(ok),'label':label,'actual':evidence});save();need(ok,'Actual native check failed: '+label+'; actual='+str(evidence))
    def score(holder,obj):
        reply=cmd('scoreboard players get '+holder+' '+obj);match=re.search(r'\bhas (-?\d+)\b',reply);need(match is not None,'Actual score unreadable: '+reply);return int(match.group(1))
    def observe(condition):
        # RCON does not return /say chat. Read the server command's stored success instead.
        need(condition.startswith('execute ') and 'run say' not in condition,'Internal boolean condition required')
        cmd('scoreboard players set #native_probe ck_tmp -1')
        cmd('execute store success score #native_probe ck_tmp run '+condition)
        actual=score('#native_probe','ck_tmp')
        report.setdefault('booleanObservations',[]).append({'condition':condition,'successScore':actual,'at':utc()})
        need(actual in (0,1),'Actual boolean success score must be 0 or 1: '+str(actual))
        return actual
    def value(query):
        reply=cmd('data get '+query);match=re.search(r':\s*(-?\d+(?:\.\d+)?)[bdfLs]?\s*$',reply);need(match is not None,'Actual NBT scalar unreadable: '+reply);return float(match.group(1))
    def items(predicate):
        cmd('execute store result score #proof_count ck_tmp if items block 30 65 24 container.* '+predicate);return score('#proof_count','ck_tmp')
    def steps(n):
        need(type(n) is int and 1<=n<=200,'Bounded actual tick step required')
        before_reply=cmd('time query gametime');parts=re.findall(r'-?\d+',before_reply);need(bool(parts),'Game clock unreadable: '+before_reply);before=int(parts[-1])
        cmd('tick step '+str(n));deadline=time.monotonic()+max(10,n*.25)
        while time.monotonic()<deadline:
            reply=cmd('time query gametime');values=re.findall(r'-?\d+',reply);need(bool(values),'Actual game clock unreadable: '+reply)
            after=int(values[-1])
            if after-before>=n:
                report.setdefault('actualTickSteps',[]).append({'requested':n,'before':before,'after':after});return
            time.sleep(.1)
        raise RuntimeError('Actual world clock did not advance requested ticks: '+reply)
    def await_actor(name):
        # Carpet's profile resolution/join is asynchronous, including while world ticks are frozen.
        deadline=min(native_end,time.monotonic()+30)
        observations=[]
        while time.monotonic()<deadline:
            identity=observe('execute if entity @a[name='+name+',gamemode=survival]')
            ops=json.loads((srv/'ops.json').read_text(encoding='utf-8'))
            need(ops==[],'Fresh fixture unexpectedly contains operators during '+name+' readiness')
            ready=identity==1 and ops==[]
            row={'at':utc(),'identitySuccessScore':identity,'ops':ops}
            observations.append(row)
            report.setdefault('actorReadiness',{})[name]={'timeoutSeconds':30,'observations':observations}
            if ready:
                row['actualPosition']=cmd('data get entity '+name+' Pos')
                check(ready,'Carpet survival player with no ops '+name,report['actorReadiness'][name])
                return
            time.sleep(.1)
        check(False,'bounded actual Carpet actor readiness '+name,{'timeoutSeconds':30,'observations':observations})

    def press(action):
        x,y,z=manifest['config']['guns'][0]['controls'][action]
        cmd(f'player CannonProof look at {x+.5} {y+.06} {z+.5}');cmd('player CannonProof use once');steps(3)
        actual=observe(f'execute if block {x} {y} {z} minecraft:stone_button[powered=true]')
        check(actual==1,'Carpet real button use '+action,actual)
    def release_button():steps(21)
    def spawn_target(registered=True):
        cmd('kill @e[type=minecraft:marker,tag=ck.proof.target]')
        cmd('summon minecraft:marker 32.5 67.7 48.5 {Tags:["nsp_ck.ship_anchor","ck.proof.target"]}')
        if registered:cmd('execute as @e[type=minecraft:marker,tag=ck.proof.target,limit=1] at @s run function nsp_ck:api/register_target')
    def load_ammo():
        cmd('data modify block 30 65 24 Items set value []');cmd('loot insert 30 65 24 loot nsp_chain:black_powder');cmd('item replace block 30 65 24 container.1 with minecraft:iron_ingot 3')
    try:
        lock=json.loads((RUNTIME_HOME/'LOCK.json').read_text(encoding='utf-8'))
        java=subprocess.run(['java','-version'],capture_output=True,text=True,timeout=10)
        report['java']={'exitCode':java.returncode,'stdout':java.stdout,'stderr':java.stderr}
        need(java.returncode==0 and lock['java'] in java.stdout+java.stderr,'Exact existing pinned Java version required')
        spec=importlib.util.spec_from_file_location('cannon_trusted_public_download_runtime',RUNTIME_HOME/'download_runtime.py');runtime_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime_module)
        carpet=json.loads((HOME/'fixtures/CARPET_RUNTIME.json').read_text(encoding='utf-8'))
        need(carpet['game_versions']==['26.3'] and carpet['loaders']==['fabric'] and len(carpet['files'])==1,'Exact compatible Carpet metadata required')
        proof_lock=copy.deepcopy(lock);proof_lock['mods']=[row for row in lock['mods'] if row['filename'].startswith('fabric-api-')]
        need(len(proof_lock['mods'])==1,'One exact Fabric API runtime row required')
        proof_lock['mods'].append(dict(carpet['files'][0],version=carpet['version_number']))
        runtime=runtime_module.prepare(root/'runtime',proof_lock)
        report['runtime']={'downloadedBytes':runtime['downloaded_bytes'],'assetObjects':runtime['asset_objects'],'minecraft':lock['minecraft'],'fabricLoader':lock['fabricLoader'],'javaPin':lock['java'],'mods':[{'filename':row['filename'],'hashes':row['hashes']} for row in proof_lock['mods']],'excludedFlan':True}
        native_end=time.monotonic()+600
        srv=root/'server';srv.mkdir();datapacks=srv/'world/datapacks';datapacks.mkdir(parents=True);shutil.copytree(pack,datapacks/'nsp_cannon_kernel')
        ammo=datapacks/'nsp_cannon_authentic_ammo';(ammo/'data/nsp_chain/loot_table').mkdir(parents=True)
        provenance=json.loads((HOME/'fixtures/AMMO_PROVENANCE.json').read_text(encoding='utf-8'))
        loot=HOME/'fixtures/black_powder.json';need(sha(loot)==provenance['sha256'] and loot.stat().st_size==provenance['bytes'],'Authentic ammo fixture drift')
        shutil.copyfile(loot,ammo/'data/nsp_chain/loot_table/black_powder.json')
        (ammo/'pack.mcmeta').write_text(json.dumps({'pack':{'description':'Unchanged Black Powder loot fixture only; no complete crafting-chain proof','min_format':[121,0],'max_format':[121,0]}}),encoding='utf-8');report['ammoProvenance']=provenance
        (srv/'mods').mkdir()
        for row in proof_lock['mods']:shutil.copyfile(runtime['mods'][row['version']],srv/'mods'/row['filename'])
        ports=[]
        for _ in range(2):
            with socket.socket() as probe:probe.bind(('127.0.0.1',0));ports.append(probe.getsockname()[1])
        need(ports[0]!=ports[1],'Loopback port collision');gameport,rconport=ports;report['ports']={'game':gameport,'rcon':rconport,'bind':'127.0.0.1'}
        generator={'biome':'minecraft:plains','layers':[{'block':'minecraft:bedrock','height':1},{'block':'minecraft:stone','height':62},{'block':'minecraft:grass_block','height':1}],'features':False,'lakes':False}
        props={'server-ip':'127.0.0.1','server-port':gameport,'enable-rcon':'true','rcon.port':rconport,'rcon.password':password,'online-mode':'false','enforce-secure-profile':'false','white-list':'true','enforce-whitelist':'true','level-name':'world','level-type':'minecraft:flat','generator-settings':json.dumps(generator,separators=(',',':')),'gamemode':'survival','difficulty':'normal','pvp':'true','spawn-protection':0,'view-distance':5,'simulation-distance':5,'pause-when-empty-seconds':0,'max-players':4,'max-tick-time':120000,'broadcast-rcon-to-ops':'false','enable-command-block':'false','function-permission-level':2}
        (srv/'server.properties').write_text(''.join(str(k)+'='+str(v)+'\n' for k,v in props.items()),encoding='utf-8');(srv/'eula.txt').write_text('eula=true\n',encoding='utf-8')
        def offline_uuid(name):return str(uuid.UUID(bytes=hashlib.md5(('OfflinePlayer:'+name).encode()).digest(),version=3))
        (srv/'ops.json').write_text('[]',encoding='utf-8');(srv/'whitelist.json').write_text(json.dumps([{'name':name,'uuid':offline_uuid(name)} for name in ['CannonProof','CannonBystander']]),encoding='utf-8')
        # Only the same two generic offline fixture identities; no existing cache/account is read.
        expires=(datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S %z')
        cache=[{'name':name,'uuid':offline_uuid(name),'expiresOn':expires} for name in ['CannonProof','CannonBystander']]
        (srv/'usercache.json').write_text(json.dumps(cache),encoding='utf-8')
        cache_actual=json.loads((srv/'usercache.json').read_text(encoding='utf-8'));whitelist_actual=json.loads((srv/'whitelist.json').read_text(encoding='utf-8'))
        same_profiles={(row['name'],row['uuid']) for row in cache_actual}=={(row['name'],row['uuid']) for row in whitelist_actual}
        need(same_profiles and len(cache_actual)==2,'Fresh generic cache/whitelist identity mismatch')
        report['offlineFixtureProfileCache']={'names':[row['name'] for row in cache_actual],'count':len(cache_actual),'expiresOn':expires,'usesSameOfflineUUIDsAsWhitelist':same_profiles}

        env={key:os.environ[key] for key in ['PATH','JAVA_HOME','LANG','LC_ALL','HOME','TMPDIR'] if key in os.environ};env.update(PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
        log=(artifacts/'server.actual.log').open('xb');logs.append(log)
        argv=['java','-Xms256M','-Xmx2G','-XX:ActiveProcessorCount=2','-Dmax.bg.threads=1','-Dfile.encoding=UTF-8','-Djava.awt.headless=true','-cp',runtime['server_classpath'],runtime['server_profile']['mainClass'],'--nogui']
        server=subprocess.Popen(argv,cwd=srv,env=env,stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);report['serverPid']=server.pid;report['serverLaunchArgv']=argv;save()
        deadline=min(native_end,time.monotonic()+360)
        while time.monotonic()<deadline:
            need(server.poll() is None,'Actual private server exited during startup')
            try:rcon=Rcon(rconport,password);rcon.cmd('list');break
            except(OSError,RuntimeError):
                if rcon:rcon.close();rcon=None
                time.sleep(.5)
        need(rcon is not None,'Actual hosted Fabric server startup deadline');report['readyObservedAt']=utc();save()
        check('nsp_cannon_kernel' in cmd('datapack list enabled'),'kernel actually enabled',report['commands'][-1]['reply'])
        cmd('carpet commandPlayer true');cmd('time set midnight');cmd('weather clear')
        cmd('function nsp_ck:demo/build')
        cmd('player CannonProof spawn at 32.5 65 20.5 facing 0 0 in minecraft:overworld in survival')
        await_actor('CannonProof')
        observation_positive=observe('execute if entity @a[name=CannonProof,gamemode=survival]')
        observation_negative=observe('execute if entity @a[name=CannonAbsentFixture]')
        check(observation_positive==1 and observation_negative==0,'actual boolean observation positive and negative controls',{'existingSurvivalActor':observation_positive,'nonexistentFixtureActor':observation_negative})
        check(score('@e[type=minecraft:marker,tag=nsp_ck.g.battery,limit=1]','ck_ld')==0,'actual controller starts unloaded','ck_ld queried')
        cmd('tick freeze');steps(1)
        load_ammo();check(items(POWDER)==4,'authentic source powder recognized',items(POWDER))
        check(items('minecraft:iron_ingot')==3,'iron inventory prepared',items('minecraft:iron_ingot'))
        press('load');check(score('@e[type=minecraft:marker,tag=nsp_ck.g.battery,limit=1]','ck_ld')==1,'button loaded gun',items(POWDER))
        check(items(POWDER)==3 and items('minecraft:iron_ingot')==2,'one genuine powder and iron consumed exactly once',{'powder':items(POWDER),'iron':items('minecraft:iron_ingot')})
        steps(5);check(items(POWDER)==3 and items('minecraft:iron_ingot')==2,'held button does not consume twice',{'powder':items(POWDER),'iron':items('minecraft:iron_ingot')});release_button()
        cmd('clone 22 64 23 42 71 43 72 64 23 replace force')
        spawn_target(True);check(score('@e[type=minecraft:marker,tag=ck.proof.target,limit=1]','ck_hp')==40,'owned ship anchor registered',40)
        press('fire');steps(16);check(score('@e[type=minecraft:marker,tag=ck.proof.target,limit=1]','ck_hp')==32,'actual marker trajectory hit owned anchor',score('@e[type=minecraft:marker,tag=ck.proof.target,limit=1]','ck_hp'))
        same=observe('execute if blocks 22 64 23 42 71 43 72 64 23 all');check(same==1,'cannon shot leaves actual fixture blocks and inventory unchanged',same)
        check(score('#shots','ck_stat')==1 and score('#hits','ck_stat')==1,'real shot and hit counters',{'shots':score('#shots','ck_stat'),'hits':score('#hits','ck_stat')})
        release_button();before={'powder':items(POWDER),'iron':items('minecraft:iron_ingot')};press('load');check(before=={'powder':items(POWDER),'iron':items('minecraft:iron_ingot')},'load during cooldown consumes nothing',before);release_button()
        steps(125);press('load');release_button();press('fire');steps(20)
        check(score('#shots','ck_stat')==2,'second firing after real cooldown',score('#shots','ck_stat'))
        # Raised deck puts a vulnerable bystander inside the actual shot/collision envelope.
        cmd('fill 29 65 36 35 65 46 minecraft:stone')
        cmd('player CannonBystander spawn at 32.5 66 41.5 facing 0 0 in minecraft:overworld in survival')
        await_actor('CannonBystander')
        cmd('execute as CannonBystander at @s run function nsp_ck:api/register_target')
        tags=cmd('data get entity CannonBystander Tags');check('nsp_ck.target' not in tags,'player cannot register as cannon target',tags)
        hp=value('entity CannonBystander Health');steps(125);release_button();press('load');release_button();press('fire')
        observed=[];path_contact=[]
        for _ in range(20):
            steps(1);observed.append(value('entity CannonBystander Health'))
            contact=observe('execute as CannonBystander at @s positioned ~ ~0.9 ~ if entity @e[type=minecraft:marker,tag=nsp_ck.shell,distance=..0.95]')
            path_contact.append(contact)
        check(any(path_contact),'actual shot occupied bystander collision envelope',{'contactSamples':path_contact,'playerPosition':cmd('data get entity CannonBystander Pos')})
        check(all(v==hp for v in observed),'bystander stays unharmed across actual shot ticks',{'before':hp,'observed':observed})
        cmd('damage CannonBystander 1 minecraft:generic');after=value('entity CannonBystander Health');check(after<hp,'negative control proves health/damage observation is live',{'before':hp,'after':after})
        # No broad projectile or explosive entities can be hidden behind cosmetic smoke.
        forbidden=observe('execute if entity @e[type=minecraft:tnt]')
        check(forbidden==0,'no TNT entities after shots',forbidden)
        release_button();steps(125)
        before={'powder':items(POWDER),'iron':items('minecraft:iron_ingot')};press('load')
        check(before=={'powder':items(POWDER),'iron':items('minecraft:iron_ingot')} and score('@e[type=minecraft:marker,tag=nsp_ck.g.battery,limit=1]','ck_ld')==0,'missing iron refuses without consuming genuine powder',before)
        release_button();cmd('item replace block 30 65 24 container.1 with minecraft:iron_ingot 1');press('load')
        check(items(POWDER)==0 and items('minecraft:iron_ingot')==0 and score('@e[type=minecraft:marker,tag=nsp_ck.g.battery,limit=1]','ck_ld')==1,'last genuine powder and iron units load correctly',{'powder':items(POWDER),'iron':items('minecraft:iron_ingot')})
        release_button();spawn_target(True);cmd('fill 31 65 40 33 70 40 minecraft:stone')
        shots_before=score('#shots','ck_stat');hits_before=score('#hits','ck_stat');press('fire')
        check(score('#shots','ck_stat')==shots_before+1,'wall case really fired one shot',{'before':shots_before,'after':score('#shots','ck_stat')})
        wall_trace=[];wall_witness=None
        shell_selector='@e[type=minecraft:marker,tag=nsp_ck.shell,limit=1]'
        for _ in range(24):
            exists=observe('execute if entity '+shell_selector)
            if exists==0:break
            state={key:score(shell_selector,'ck_'+key) for key in ['x','y','z','vx','vy','vz','age']}
            next_pos=[(state[k]+state['v'+k])/1000 for k in ['x','y','z']]
            point=' '.join(f'{v:.6f}' for v in next_pos)
            solid=observe('execute positioned '+point+' if block ~ ~ ~ minecraft:stone')
            loaded=observe('execute positioned '+point+' if loaded ~ ~ ~')
            other=observe('execute positioned '+point+' if entity @e[tag=nsp_ck.target,distance=..1.1]')
            row={'actualScores':state,'nextFirstSubstep':next_pos,'solidStone':solid==1,'loaded':loaded==1,'nearRegisteredTarget':other==1,'observationScores':{'solidStone':solid,'loaded':loaded,'nearRegisteredTarget':other}}
            wall_trace.append(row)
            if row['solidStone'] and row['loaded'] and not row['nearRegisteredTarget'] and state['age']<80 and 31<=next_pos[0]<34 and 65<=next_pos[1]<71 and 40<=next_pos[2]<41:
                wall_witness=row;steps(1);break
            steps(1)
        report['wallProductionTrace']=wall_trace
        check(wall_witness is not None,'actual moving shell reached loaded solid wall before lifetime/boundary guards',wall_trace)
        stopped=observe('execute if entity '+shell_selector)
        check(stopped==0 and score('#hits','ck_stat')==hits_before and score('@e[type=minecraft:marker,tag=ck.proof.target,limit=1]','ck_hp')==40,'production solid-block step removed fired shell without target damage',{'witness':wall_witness,'shellQuery':stopped,'hitsBefore':hits_before,'hitsAfter':score('#hits','ck_stat'),'targetHP':score('@e[type=minecraft:marker,tag=ck.proof.target,limit=1]','ck_hp')})
        # Genuine living-entity API component checks, independently of marker trajectory evidence.
        for typ,register,want_damage in [('skeleton',True,True),('drowned',True,True),('skeleton',False,False),('cow',True,False)]:
            cmd('kill @e[tag=ck.proof.mob]')
            cmd('summon minecraft:'+typ+' 39.5 65 20.5 {Tags:["ck.proof.mob"],NoAI:1b,Silent:1b,PersistenceRequired:1b}')
            selector='@e[type=minecraft:'+typ+',tag=ck.proof.mob,limit=1]'
            if register:cmd('execute as '+selector+' at @s run function nsp_ck:api/register_target')
            tags=cmd('data get entity '+selector+' Tags')
            check(('nsp_ck.target' in tags)==want_damage,'actual living target registration '+typ+' registered='+str(register),tags)
            health=value('entity '+selector+' Health');before_hits=score('#hits','ck_stat')
            cmd('execute as '+selector+' at @s run function nsp_ck:target/damage')
            after_health=value('entity '+selector+' Health');after_hits=score('#hits','ck_stat')
            check((after_health<health and after_hits==before_hits+1) if want_damage else (after_health==health and after_hits==before_hits),'living entry damage positive/negative '+typ+' registered='+str(register),{'beforeHealth':health,'afterHealth':after_health,'beforeHits':before_hits,'afterHits':after_hits,'method':'actual target/damage entry; not a fired mob-trajectory claim'})
        cmd('kill @e[tag=ck.proof.mob]')
        cmd('summon minecraft:oak_boat 38.5 65 19.5 {Tags:["ck.proof.boat"]}')
        boat='@e[type=minecraft:oak_boat,tag=ck.proof.boat,limit=1]'
        before_hits=score('#hits','ck_stat')
        cmd('execute as '+boat+' at @s run function nsp_ck:api/register_target')
        boat_tags=cmd('data get entity '+boat+' Tags')
        cmd('execute as '+boat+' at @s run function nsp_ck:target/damage');cmd('execute as '+boat+' at @s run function nsp_ck:target/anchor_hit')
        boat_exists=observe('execute if entity '+boat)
        check('nsp_ck.target' not in boat_tags and boat_exists==1 and score('#hits','ck_stat')==before_hits,'neutral boat remains untargeted and present',{'tags':boat_tags,'exists':boat_exists,'hitsBefore':before_hits,'hitsAfter':score('#hits','ck_stat')})
        # Boundary regression: a registered target moves out, while the real hit path starts inside.
        spawn_target(True);target='@e[type=minecraft:marker,tag=ck.proof.target,limit=1]'
        maximum=manifest['config']['site']['max'][0];inside_x=maximum+.5;outside_x=maximum+1.3
        cmd(f'forceload add {int(inside_x)} 48');cmd(f'forceload add {int(outside_x)} 48')
        cmd(f'tp {target} {outside_x:.6f} 67.7 48.5')
        before_hp=score(target,'ck_hp');before_hits=score('#hits','ck_stat')
        boundary_pos=cmd('data get entity '+target+' Pos')
        lo=manifest['config']['site']['min'];hi=manifest['config']['site']['max']
        box=','.join([f'x={lo[0]}',f'y={lo[1]}',f'z={lo[2]}',f'dx={hi[0]-lo[0]}',f'dy={hi[1]-lo[1]}',f'dz={hi[2]-lo[2]}'])
        actual_target_inside=observe('execute as '+target+' if entity @s['+box+']')
        check(actual_target_inside==0,'registered marker really moved outside actual site selector',{'position':boundary_pos,'query':actual_target_inside})
        cmd(f'summon minecraft:marker {inside_x:.6f} 67.7 48.5 {{Tags:["nsp_ck.shell","ck.proof.boundary_shell"]}}')
        boundary_shell='@e[type=minecraft:marker,tag=ck.proof.boundary_shell,limit=1]'
        actual_shell_inside=observe('execute as '+boundary_shell+' if entity @s['+box+']')
        check(actual_shell_inside==1,'boundary collision context really starts inside actual site selector',actual_shell_inside)
        near=observe('execute at '+boundary_shell+' if entity '+target[:-1]+',distance=..1.1]')
        check(near==1,'moved-out registered target is in actual boundary hit envelope',{'targetPosition':boundary_pos,'shellPosition':cmd('data get entity '+boundary_shell+' Pos'),'nativeNearQuery':near})
        cmd('execute as '+boundary_shell+' at @s run function nsp_ck:hit/anchor')
        check(score(target,'ck_hp')==before_hp and score('#hits','ck_stat')==before_hits,'moved-out anchor cannot be damaged by boundary hit path',{'targetPosition':boundary_pos,'hpBefore':before_hp,'hpAfter':score(target,'ck_hp'),'hitsBefore':before_hits,'hitsAfter':score('#hits','ck_stat')})
        cmd('summon minecraft:skeleton 39.5 65 20.5 {Tags:["ck.proof.boundary_mob"],NoAI:1b,Silent:1b,PersistenceRequired:1b}')
        mob='@e[type=minecraft:skeleton,tag=ck.proof.boundary_mob,limit=1]'
        cmd('execute as '+mob+' at @s run function nsp_ck:api/register_target')
        mob_tags=cmd('data get entity '+mob+' Tags');check('nsp_ck.target' in mob_tags,'living boundary fixture truly registered before move',mob_tags)
        mob_x=maximum+2.5;cmd(f'forceload add {int(mob_x)} 20');cmd(f'setblock {int(mob_x)} 64 20 minecraft:stone');cmd(f'tp {mob} {mob_x:.6f} 65 20.5')
        health=value('entity '+mob+' Health');before_hits=score('#hits','ck_stat');position=cmd('data get entity '+mob+' Pos')
        actual_mob_inside=observe('execute as '+mob+' if entity @s['+box+']')
        check(actual_mob_inside==0 and 'nsp_ck.target' in cmd('data get entity '+mob+' Tags'),'living target remains registered but actually outside site after move',{'position':position,'query':actual_mob_inside})
        cmd('execute as '+mob+' at @s run function nsp_ck:target/damage')
        check(value('entity '+mob+' Health')==health and score('#hits','ck_stat')==before_hits,'moved-out registered living target cannot take entry damage',{'position':position,'healthBefore':health,'healthAfter':value('entity '+mob+' Health'),'hitsBefore':before_hits,'hitsAfter':score('#hits','ck_stat')})

        report['success']=True
    except BaseException:
        report['errors'].append(traceback.format_exc())
        print(report['errors'][-1],file=sys.stderr,flush=True)
    finally:
        # Cleanup bypasses the gameplay clock deadline, never the process ownership boundary.
        stop_requested=False;stop_errors=[]
        if server is not None and server.poll() is None:
            if rcon:
                try:rcon.cmd('save-all flush');rcon.cmd('stop');stop_requested=True
                except (OSError,RuntimeError) as error:stop_errors.append(type(error).__name__+': '+str(error))
            if not stop_requested and server.stdin:
                try:server.stdin.write(b'save-all flush\nstop\n');server.stdin.flush();stop_requested=True
                except OSError as error:stop_errors.append(type(error).__name__+': '+str(error))
        if rcon:
            try:rcon.close()
            except OSError:pass
        forced=False
        if server is not None:
            try:
                try:server.wait(timeout=60)
                except subprocess.TimeoutExpired:
                    forced=True
                    try:
                        if server.poll() is None and os.getpgid(server.pid)==server.pid:os.killpg(server.pid,signal.SIGTERM)
                    except ProcessLookupError:pass
                    try:server.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        try:
                            if server.poll() is None and os.getpgid(server.pid)==server.pid:os.killpg(server.pid,signal.SIGKILL)
                        except ProcessLookupError:pass
                        server.wait(timeout=10)
                alive=group_alive(server.pid)
                report['serverClosure']={'exitCode':server.returncode,'forced':forced,'processGroupAlive':alive,'stopRequested':stop_requested,'stopErrors':stop_errors}
                if forced or server.returncode!=0 or alive:report['success']=False
                if (root/'server/ops.json').is_file():report['opsAfterStop']=json.loads((root/'server/ops.json').read_text())
                if report.get('opsAfterStop')!=[]:report['success']=False
            except BaseException:
                report['errors'].append('Cleanup failure: '+traceback.format_exc());report['success']=False
        else:report['serverClosure']={'started':False}
        for log in logs:log.close()
        if server is not None:
            actual_log=artifacts/'server.actual.log'
            if actual_log.is_file():
                lines=actual_log.read_text(encoding='utf-8',errors='replace').splitlines()
                patterns=[r'/(?:ERROR|FATAL)\]',r'Failed to (?:load|parse) (?:function|tag|registry|data)',r"Couldn.t (?:load|parse) (?:function|tag|registry|data)",r'Unknown function',r'Exception in (?:thread|server tick)',r'Encountered an unexpected exception',r'Errors in currently selected datapacks']
                failures=[line for line in lines if any(re.search(pattern,line,re.I) for pattern in patterns)]
                report['serverLogAudit']={'linesRead':len(lines),'parseOrGlobalErrors':failures}
                report['checks'].append({'pass':not failures,'label':'no actual function parse or global server errors','actual':report['serverLogAudit']})
                if failures:report['success']=False
            else:
                report['errors'].append('Actual launched-server log is missing');report['success']=False
        report['finishedAt']=utc();save()
        total=sum(p.stat().st_size for p in artifacts.rglob('*') if p.is_file())
        allowed=total+4096<=2*1024*1024
        report['artifactBytesBeforeFinalReceipt']=total;report['artifactUploadAllowed']=allowed
        if not allowed:report['success']=False;report['errors'].append('Evidence exceeds 2MiB; upload withheld, logs retained on runner')
        save()
        if os.environ.get('GITHUB_OUTPUT'):
            with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8') as stream:stream.write('upload_allowed='+str(allowed).lower()+'\n')
    print(json.dumps({'success':report['success'],'actualChecks':len(report['checks']),'receipt':str(artifacts/'NATIVE_ACTUAL.json'),'humanClientProven':False,'bedrockProven':False,'liveInstalled':False}),flush=True)
    return 0 if report['success'] else 1
if __name__=='__main__':raise SystemExit(main())
