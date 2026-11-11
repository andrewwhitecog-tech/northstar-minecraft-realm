"""Real two-case vanilla Minecraft smoke on explicit GitHub-hosted Linux only.
Default validates source payload only. No Windows/native local admission bypass.
The packet tests use synthetic transport bytes; native outcomes are never mocked.
"""
from __future__ import annotations
import argparse, builtins, datetime as dt, hashlib, json, os, re, secrets, shutil, socket, struct, symtable
import subprocess, sys, time, traceback, urllib.parse, urllib.request, zipfile
from pathlib import Path
sys.dont_write_bytecode=True
HOME=Path(__file__).resolve().parent
CONFIG=HOME/'PAYLOAD.json'
PREPARATION=HOME/'ci-prepared'
SMOKE_LABELS=('authentic_trim_0','trim_item_unknown_registry')
NO_WINDOW=0
BELOW_NORMAL=0


def utc(): return dt.datetime.now(dt.timezone.utc).isoformat()

def digest(raw): return hashlib.sha256(raw).hexdigest()

def hash_file(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def require(condition,why):
    if not condition: raise RuntimeError(why)

def save(path,data):path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf8')

def confined(path):
    p=Path(path).resolve()
    require(p.is_relative_to(HOME.resolve()),'Proof output escapes owned native_execution home')
    return p

def function_path(root,identifier):
    ns,name=identifier.split(':',1)
    require(re.fullmatch(r'[a-z0-9_.-]+',ns) and re.fullmatch(r'[a-z0-9_/-]+',name) and '..' not in name.split('/'),'Unsafe function ID')
    return root/'data'/ns/'function'/(name+'.mcfunction')

def parse_literal(s):
    m=re.fullmatch(r'\{x:(-?\d+),y:(-?\d+),z:(-?\d+),item:"([a-z0-9_]+)"\}',s)
    require(m is not None,'Smoke argument is not the retained literal grammar')
    return {'x':int(m[1]),'y':int(m[2]),'z':int(m[3]),'item':m[4]}

def fixture_command(site):
    # Actual native 26.3 item-stack field spelling; server length/effects must confirm it.
    entries=','.join('{Slot:'+str(i)+'b,id:"minecraft:'+site['item']+'",count:64}'for i in range(17))
    return 'setblock {x} {y} {z} minecraft:barrel{{Items:[{items}]}} replace'.format(**site,items=entries)

def wrapper_commands(case):
    require(case['function']=='nsp_crafter_refill:trim' and '\n' not in case['arguments_snbt'] and '\r' not in case['arguments_snbt'],'Unsupported smoke wrapper')
    return [
        'scoreboard players set #after nspmg 0',
        'execute store result score #result nspmg store success score #success nspmg run function '+case['function']+' '+case['arguments_snbt'],
        'scoreboard players add #after nspmg 1',
    ]

def remaining_labels(plan,attempted):
    return [c['label']for c in plan['cases']if c['label']not in attempted]

class Rcon:
    """Bounded Source-RCON protocol; own localhost endpoint only. No library/mock dispatcher."""
    def __init__(self,port,password):
        self.s=socket.create_connection(('127.0.0.1',port),timeout=3);self.s.settimeout(15);self.i=1
        self.send(3,password)
        for _ in range(3):
            i,t,body=self.receive()
            require(i!=-1,'Own RCON authentication failed')
            if i==self.i and t==2:break
        else:raise RuntimeError('No RCON authentication response')
    def exact(self,n):
        b=b''
        while len(b)<n:
            more=self.s.recv(n-len(b))
            if not more:raise ConnectionError('Own RCON closed')
            b+=more
        return b
    def send(self,t,body):
        b=struct.pack('<ii',self.i,t)+body.encode('utf8')+b'\0\0'
        self.s.sendall(struct.pack('<i',len(b))+b)
    def receive(self):
        n=struct.unpack('<i',self.exact(4))[0]
        require(10<=n<=4*1024*1024,'Invalid RCON packet length')
        b=self.exact(n);require(b[-2:]==b'\0\0','Invalid RCON terminator')
        i,t=struct.unpack('<ii',b[:8]);return i,t,b[8:-2].decode('utf8')
    def cmd(self,command):
        self.i+=1;self.send(2,command);parts=[]
        for _ in range(64):
            i,t,body=self.receive();require(i==self.i and t==0,'RCON response identity mismatch');parts.append(body)
            if len(body.encode('utf8'))<4096:return ''.join(parts)
        raise RuntimeError('RCON response exceeds bound')
    def close(self):self.s.close()

def execute(config,loaded,reviewed_hash,benchmark_iterations=0):
    prepared_path=PREPARATION/'PREPARED.json'
    require(hash_file(prepared_path)==reviewed_hash,'Reviewed preparation hash differs')
    prepared=json.loads(prepared_path.read_text(encoding='utf8'))
    require(prepared['config_sha256']==hash_file(CONFIG),'Prepared configuration drift')
    require(prepared['runner_sha256']==hash_file(__file__),'Reviewed native runner source drift')
    for relative,expected in prepared['pack_files'].items():require(hash_file(PREPARATION/relative)==expected,'Prepared pack drift')
    require(0<=benchmark_iterations<=25,'Benchmark iteration bound exceeded')
    ports_free(config)
    govern_parent()
    run=confined(HOME/'runs'/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ'));run.mkdir(parents=True)
    report={'schema':'northstar.native-guard-execution-result.v1','started_utc':utc(),'status':'NOT_RUN','native_execution':False,
            'public_world_actions':False,'isolated_fixture_world_actions':False,'all24_original_holds_retained':True,'hold_clearance':False,
            'prepared_sha256':reviewed_hash,'commands':[],'checks':[],'case_results':[],
            'attempted_case_labels':[],'not_run_cases':remaining_labels(loaded['case_plan'],[]),'benchmark':{'status':'NOT_RUN'},'errors':[]}
    receipt=run/'ACTUAL.json';token=None;proc=None;r=None;log=None;exit_code=1
    def write():save(receipt,report)
    def start_case(label):
        report['attempted_case_labels'].append(label)
        report['not_run_cases']=remaining_labels(loaded['case_plan'],report['attempted_case_labels']);write()
    def check(name,condition,detail=None):
        report['checks'].append({'name':name,'pass':bool(condition),'actual':detail});write()
        require(condition,'Native check failed: '+name)
    def cmd(command):
        start=time.perf_counter();answer=r.cmd(command)
        report['commands'].append({'command':command,'response':answer,'roundtrip_seconds':time.perf_counter()-start});write();return answer
    def score(name):
        raw=cmd('scoreboard players get '+name+' nspmg');m=re.search(r'has (-?\d+)',raw)
        require(m is not None,'Native scoreboard response is not an integer: '+raw)
        return int(m.group(1))
    def condition(clause):
        cmd('scoreboard players set #probe nspmg -1')
        cmd('execute store success score #probe nspmg run execute '+clause)
        return score('#probe')==1
    def reset(site):
        cmd('setblock {x} {y} {z} minecraft:air replace'.format(**site))
        cmd(fixture_command(site));cmd('data modify storage nsp_crafter_refill:t first set value {proof_sentinel:1b}')
        check('fixture actually has17stacks',condition('if data block {x} {y} {z} Items[16]'.format(**site)))
        check('fixture first native item matches',condition('if data block {x} {y} {z} Items[0]{{id:"minecraft:{item}"}}'.format(**site)))
    try:
        require_hosted_ci()
        report['admission']={'route':'EXPLICIT_GITHUB_HOSTED_LINUX_CI','repository':os.environ['GITHUB_REPOSITORY'],'run_id':os.environ['GITHUB_RUN_ID'],'job':os.environ.get('GITHUB_JOB'),'local_governor_bypass':False};write()
        # Bind installed libraries after admission; no downloads or shared-file mutation.
        deps=[loaded['classpath']['server_jar'],*loaded['classpath']['libraries']]
        for row in deps:require(hash_file(row['path'])==row['sha256'],'Installed native dependency drift: '+row['path'])
        report['dependencies_verified']=len(deps)
        server=run/'server';server.mkdir();world=server/'world';(world/'datapacks').mkdir(parents=True)
        import shutil
        shutil.copytree(PREPARATION/'pack',world/'datapacks/nsp_mg_proof')
        password=secrets.token_hex(24)
        props={'server-ip':'127.0.0.1','server-port':config['game_port'],'enable-rcon':'true','rcon.port':config['rcon_port'],'rcon.password':password,
               'online-mode':'false','max-players':1,'level-name':'world','level-seed':1,'level-type':'minecraft:flat',
               'generator-settings':json.dumps({'layers':[{'height':1,'block':'minecraft:bedrock'},{'height':2,'block':'minecraft:dirt'},{'height':1,'block':'minecraft:grass_block'}],'biome':'minecraft:plains'}),
               'generate-structures':'false','difficulty':'peaceful','spawn-protection':0,'view-distance':2,'simulation-distance':2,'pause-when-empty-seconds':0,
               'function-permission-level':2,'enable-query':'false','broadcast-rcon-to-ops':'false','max-tick-time':60000,'motd':'PRIVATE MACRO PROOF'}
        (server/'server.properties').write_text('\n'.join(k+'='+str(v).replace(':','\\:')for k,v in props.items())+'\n',encoding='utf8')
        (server/'eula.txt').write_text('eula=true\n',encoding='utf8')
        env={k:v for k,v in os.environ.items()if k not in ('JAVA_TOOL_OPTIONS','_JAVA_OPTIONS','JDK_JAVA_OPTIONS','CLASSPATH')};env.update(PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
        args=[config['java'],'-Xms256M','-Xmx1G','-XX:ActiveProcessorCount=1','-Djava.awt.headless=true','-Dfile.encoding=UTF-8','-cp',loaded['classpath']['classpath'],'net.minecraft.server.Main','--nogui']
        log=(server/'console.actual.log').open('xb')
        proc=subprocess.Popen(args,cwd=server,stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,env=env,creationflags=NO_WINDOW|BELOW_NORMAL)
        report.update(server_pid=proc.pid,native_execution=True,isolated_fixture_world_actions=True,status='RUNNING');write()
        deadline=time.monotonic()+180
        while time.monotonic()<deadline:
            require(proc.poll() is None,'Owned native server exited before readiness')
            try:r=Rcon(config['rcon_port'],password);break
            except (OSError,RuntimeError):time.sleep(1)
        require(r is not None,'Owned native server readiness timed out')
        cmd('scoreboard objectives add nspmg dummy')
        cmd('datapack list enabled')
        sites=prepared['benchmark_sites']
        for s in sites:cmd('forceload add {x} {z}'.format(**s))
        site=sites[0]
        # Wait for native chunk loading by placing/reading the actual fixture.
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            cmd(fixture_command(site))
            if condition('if block {x} {y} {z} minecraft:barrel'.format(**site)):break
            time.sleep(0.5)
        check('owned fixture chunk loaded',condition('if block {x} {y} {z} minecraft:barrel'.format(**site)))
        cases={c['label']:c for c in loaded['case_plan']['cases']}
        accepted=cases['authentic_trim_0'];args_snbt=accepted['arguments_snbt']
        start_case('authentic_trim_0')
        reset(site);baseline_before=cmd('data get block {x} {y} {z} Items'.format(**site))
        cmd('execute store result score #original_result nspmg store success score #original_success nspmg run function nsp_mg_proof:original_trim '+args_snbt)
        baseline_after=cmd('data get block {x} {y} {z} Items'.format(**site))
        check('original operative body removes exactly one list item',condition('if data block {x} {y} {z} Items[15]'.format(**site))and not condition('if data block {x} {y} {z} Items[16]'.format(**site)))
        baseline_result=score('#original_result');baseline_success=score('#original_success')
        reset(site);cmd('function nsp_mg_proof:authentic_trim_0')
        guarded_after=cmd('data get block {x} {y} {z} Items'.format(**site))
        check('guarded public body side effects equal exact original',guarded_after==baseline_after,{'original':baseline_after,'guarded':guarded_after})
        check('accepted guard valid flag',condition('if data storage nsp_legacy_macro_guard:trim flags{valid:1b}'))
        check('caller continuation after accepted child',score('#after')==1)
        report['case_results'].append({'label':'authentic_trim_0','status':'PASS','original_result':baseline_result,'original_success':baseline_success,'guarded_result':score('#result'),'guarded_success':score('#success'),'before':baseline_before,'after':guarded_after});write()
        start_case('trim_item_unknown_registry')
        reset(site);rejected_before=cmd('data get block {x} {y} {z} Items'.format(**site))
        cmd('function nsp_mg_proof:trim_item_unknown_registry')
        rejected_after=cmd('data get block {x} {y} {z} Items'.format(**site))
        check('rejected guard leaves barrel unchanged',rejected_before==rejected_after)
        check('rejected guard leaves operative storage sentinel untouched',condition('if data storage nsp_crafter_refill:t first{proof_sentinel:1b}'))
        check('rejected guard resets valid flag',condition('if data storage nsp_legacy_macro_guard:trim flags{valid:0b}'))
        check('early return value is zero',score('#result')==0)
        check('early return discards child frame only; caller continues',score('#after')==1)
        report['case_results'].append({'label':'trim_item_unknown_registry','status':'PASS','result':score('#result'),'success':score('#success'),'caller_after':score('#after')});write()
        if benchmark_iterations:
            profiler_start=cmd('debug start')
            rows=[]
            for s in sites:
                for variant,identifier in [('original','nsp_mg_proof:original_trim'),('guarded','nsp_crafter_refill:trim')]:
                    reset(s);cmd('function '+identifier+' '+s['arguments_snbt']) # One recorded warmup per site/variant.
                    times=[]
                    for _ in range(benchmark_iterations):
                        reset(s);cmd('function '+identifier+' '+s['arguments_snbt']);times.append(report['commands'][-1]['roundtrip_seconds'])
                    rows.append({'site':s,'variant':variant,'iterations':len(times),'rcon_end_to_end_seconds':times})
            profiler_stop=cmd('debug stop')
            report['benchmark']={'status':'MEASURED_RCON_LATENCY_ONLY','rows':rows,'warmup_per_site_variant':1,'profiler_start_response':profiler_start,'profiler_stop_response':profiler_stop,'acceptance':'NOT_DECIDED','native_cpu_or_TPS_overhead_proven':False}
        report['status']='PARTIAL_NATIVE_SMOKE_PASS_REMAINING_CASES_NOT_RUN';exit_code=0
    except BaseException:
        report['errors'].append(traceback.format_exc());report['status']='FAILED_OR_NOT_ADMITTED';traceback.print_exc()
        passed_labels={x['label']for x in report['case_results']if x['status']=='PASS'}
        report['failed_or_interrupted_case_labels']=[x for x in report['attempted_case_labels']if x not in passed_labels]
    finally:
        if r is not None:
            try:cmd('stop')
            except BaseException:report['stop_response_error']=traceback.format_exc()
            finally:r.close()
        if proc is not None:
            if proc.poll() is None:
                try:
                    if proc.stdin:proc.stdin.write(b'stop\n');proc.stdin.flush()
                except OSError:pass
                try:proc.wait(timeout=45)
                except subprocess.TimeoutExpired:
                    proc.terminate() # Exact Popen handle owned by this runner, never PID search/taskkill.
                    try:proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=10)
            report['server_exit_code']=proc.poll();report['server_close_observed']=proc.poll()is not None
            if proc.returncode!=0:exit_code=1
        if log:log.close()
        report['release']={'route':'HOSTED_CI_OWN_PROCESS_CLOSED','no_local_lease_acquired':True}
        if exit_code and report['status']=='PARTIAL_NATIVE_SMOKE_PASS_REMAINING_CASES_NOT_RUN':report['status']='CHECKS_PASSED_CLEANUP_FAILED'
        report['finished_utc']=utc();report['exit_code']=exit_code;write()
    return exit_code,receipt

def require_hosted_ci():
    require(os.name=='posix' and sys.platform=='linux','Native CI route is Linux-only; no Windows governor bypass')
    need={'GITHUB_ACTIONS':'true','CI':'true','RUNNER_ENVIRONMENT':'github-hosted','RUNNER_OS':'Linux','GITHUB_REPOSITORY':'andrewwhitecog-tech/northstar-minecraft-realm'}
    require(all(os.environ.get(k)==v for k,v in need.items()),'Explicit approved GitHub-hosted context absent')
    require(os.environ.get('GITHUB_RUN_ID','').isdigit() and bool(os.environ.get('GITHUB_JOB')),'Hosted run identity absent')
    require(Path(os.environ.get('GITHUB_WORKSPACE','/')).resolve().is_relative_to(Path('/home/runner/work')),'Hosted workspace identity differs')

def govern_parent():
    require_hosted_ci()
    os.setpriority(os.PRIO_PROCESS,0,19)
    allowed=os.sched_getaffinity(0)
    require(bool(allowed),'Hosted CPU affinity empty')
    os.sched_setaffinity(0,{min(allowed)})

def ports_free(config):
    for key in ('game_port','rcon_port'):
        with socket.socket() as s:s.bind(('127.0.0.1',config[key]))

def assert_global_bindings():
    """Audit real source symbols, including native-only branches, without executing them."""
    root=symtable.symtable(Path(__file__).read_text(encoding='utf8'),__file__,'exec')
    allowed=set(globals())|set(vars(builtins))
    missing=set()
    def inspect_table(table):
        for symbol in table.get_symbols():
            if symbol.is_referenced() and symbol.is_global() and symbol.get_name() not in allowed:missing.add(symbol.get_name())
        for child in table.get_children():inspect_table(child)
    inspect_table(root)
    require(not missing,'Unbound native source globals: '+','.join(sorted(missing)))

def validate_file_bindings(root,rows):
    root=Path(root).resolve()
    def no_alias(path):
        require(not path.is_symlink() and not getattr(path,'is_junction',lambda:False)(),'Public source alias/symlink refused')
    for relative,expected_hash in rows.items():
        require(not Path(relative).is_absolute() and '..' not in Path(relative).parts,'Payload path escapes allowlist root')
        cursor=root/relative
        while cursor!=root:
            no_alias(cursor);cursor=cursor.parent
        path=(root/relative).resolve();require(path.is_relative_to(root),'Payload path escapes allowlist root')
        require(hash_file(path)==expected_hash,'Public source drift: '+relative)
    actual=set()
    for folder,dirs,files in os.walk(root):
        for name in dirs:no_alias(Path(folder)/name)
        if Path(folder)==root:dirs[:]=[d for d in dirs if d not in ('__pycache__','ci-prepared','ci-dependencies','runs')]
        for name in files:
            no_alias(Path(folder)/name)
            if Path(folder)==root and name=='PAYLOAD.json':continue
            actual.add((Path(folder)/name).relative_to(root).as_posix())
            require(len(actual)<=200,'Payload file bound exceeded')
    require(actual==set(rows),'Public directory differs from exact source allowlist')

def validate_payload(expected=None):
    assert_global_bindings()
    if expected is not None:require(hash_file(CONFIG)==expected,'Reviewed public payload differs')
    p=json.loads(CONFIG.read_text(encoding='utf8'))
    require(p['schema']=='northstar.public-vanilla-trim-smoke-payload.v1' and p['hold_clearance'] is False,'Payload schema/clearance differs')
    require(len(p['files'])<100,'Public payload file bound')
    validate_file_bindings(HOME,p['files'])
    original=HOME/'proof_pack/data/nsp_mg_proof/function/original_trim.mcfunction'
    require(hash_file(original)==p['original_trim_sha256'],'Original trim body drift')
    for identifier,expected_hash in p['full_overlay_logical_hashes'].items():
        file=function_path(HOME/'proof_pack',identifier)
        if file.is_file():require(hash_file(file)==expected_hash,'Original guarded trim dependency drift')
    plan=json.loads((HOME/'cases.json').read_text())
    require(len(plan['cases'])==p['case_count_total']==56,'Full coverage accounting differs')
    require(set(p['implemented_cases'])==set(SMOKE_LABELS),'Implemented smoke scope differs')
    require(plan['all24_original_holds_retained'] is True and plan['hold_clearance'] is False,'Plan clearance differs')
    return p,plan

def acquire_official_dependencies(transport,destination):
    outer=transport['outer'];url=urllib.parse.urlparse(outer['url'])
    require(url.scheme=='https' and url.hostname=='piston-data.mojang.com' and url.path=='/v1/objects/'+outer['sha1']+'/server.jar','Official download origin differs')
    require(outer['size']<=80*1024*1024 and len(transport['classpath_members'])==40,'Native dependency bound differs')
    destination.mkdir()
    bundle=destination/'server-bundle.jar'
    request=urllib.request.Request(outer['url'],headers={'User-Agent':'NorthStar-public-vanilla-smoke'})
    h1=hashlib.sha1();h256=hashlib.sha256();total=0
    with urllib.request.urlopen(request,timeout=30) as remote,bundle.open('xb') as out:
        final=urllib.parse.urlparse(remote.geturl());require(final.scheme=='https' and final.hostname=='piston-data.mojang.com','Unexpected native download redirect')
        while True:
            chunk=remote.read(1024*1024)
            if not chunk:break
            total+=len(chunk);require(total<=outer['size'],'Native download size overflow')
            h1.update(chunk);h256.update(chunk);out.write(chunk)
    require(total==outer['size'] and h1.hexdigest()==outer['sha1'] and h256.hexdigest()==outer['sha256'],'Official outer bundle verification failed')
    deps=[]
    with zipfile.ZipFile(bundle) as z:
        require(len(z.namelist())==len(set(z.namelist())),'Duplicate official ZIP members')
        for row in transport['classpath_members']:
            target=(destination/row['relative']).resolve()
            require(target.is_relative_to(destination.resolve()),'Native member path escapes dependency root')
            info=z.getinfo(row['member']);require(info.file_size==row['bytes'] and info.file_size<80*1024*1024,'Native member bound differs')
            target.parent.mkdir(parents=True,exist_ok=True)
            with z.open(row['member']) as src,target.open('xb') as dst:shutil.copyfileobj(src,dst,1024*1024)
            require(hash_file(target)==row['sha256'],'Native member hash differs')
            deps.append({'path':str(target),'sha256':row['sha256']})
    return {'server_jar':deps[0],'libraries':deps[1:],'classpath':os.pathsep.join(d['path']for d in deps)}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--ci',action='store_true');ap.add_argument('--execute',action='store_true')
    ap.add_argument('--reviewed-payload-sha256');ap.add_argument('--benchmark-iterations',type=int,default=0)
    args=ap.parse_args()
    payload,plan=validate_payload(args.reviewed_payload_sha256)
    if not args.execute:
        print(json.dumps({'status':'SOURCE_PAYLOAD_VALIDATED_NATIVE_NOT_RUN','files':len(payload['files']),'implemented_cases':list(SMOKE_LABELS),'remaining_cases':54,'hold_clearance':False}));return 0
    require(args.ci and args.reviewed_payload_sha256 is not None,'Explicit --ci --execute and reviewed payload hash required')
    require_hosted_ci()
    require(not PREPARATION.exists(),'Existing CI preparation must be preserved; use a fresh hosted checkout')
    java=shutil.which('java');require(java is not None,'Java25 executable absent')
    v=subprocess.run([java,'-version'],capture_output=True,text=True,timeout=10)
    require(v.returncode==0 and re.search(r'version "25(?:\.|\")',v.stdout+v.stderr),'Actual Java major must be25')
    transport=json.loads((HOME/'transport.json').read_text())
    cp=acquire_official_dependencies(transport,HOME/'ci-dependencies')
    PREPARATION.mkdir();shutil.copytree(HOME/'proof_pack',PREPARATION/'pack')
    prepared={'schema':'northstar.native-guard-execution-prepared.v1','status':'PREPARED_NOT_RUN','config_sha256':hash_file(CONFIG),'runner_sha256':hash_file(__file__),
              'pack_files':{'pack/'+p.relative_to(HOME/'proof_pack').as_posix():hash_file(p)for p in (HOME/'proof_pack').rglob('*')if p.is_file()},
              'remaining_case_labels':remaining_labels(plan,SMOKE_LABELS),'benchmark_sites':json.loads((HOME/'benchmark_sites.json').read_text())}
    save(PREPARATION/'PREPARED.json',prepared)
    config={'java':java,'game_port':27081,'rcon_port':27082}
    code,receipt=execute(config,{'case_plan':plan,'classpath':cp},hash_file(PREPARATION/'PREPARED.json'),args.benchmark_iterations)
    result=json.loads(receipt.read_text())
    summary={'status':result['status'],'exit_code':code,'case_results':result['case_results'],'not_run_cases':result['not_run_cases'],'checks':result['checks'],
             'errors':result['errors'],'server_exit_code':result.get('server_exit_code'),'server_close_observed':result.get('server_close_observed'),'admission':result.get('admission'),
             'benchmark':result['benchmark'],'native_execution':result['native_execution'],'isolated_fixture_world_actions':result['isolated_fixture_world_actions'],
             'hold_clearance':False,'full56_acceptance':False,'native_server_sha256':transport['classpath_members'][0]['sha256']}
    print(json.dumps(summary,indent=2))
    if code:
        console=receipt.parent/'server/console.actual.log'
        if console.is_file():print('ACTUAL OWNED SERVER CONSOLE TAIL\n'+'\n'.join(console.read_text(encoding='utf8',errors='replace').splitlines()[-100:]))
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a',encoding='utf8') as out:
            out.write('## Actual vanilla trim smoke\n\n```json\n'+json.dumps(summary,indent=2)+'\n```\n')
    return code

if __name__=='__main__':raise SystemExit(main())
