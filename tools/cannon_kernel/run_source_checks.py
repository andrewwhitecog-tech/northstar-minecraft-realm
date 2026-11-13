"""Portable, explicit offline source/build checks; never launches Minecraft."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback
import zipfile

HERE=Path(__file__).resolve().parent
MAX_ARTIFACT_BYTES=2*1024*1024

def utc(): return datetime.now(timezone.utc).isoformat()
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def sources():
    metadata=json.loads((HERE/'PUBLIC_SOURCE.json').read_text(encoding='utf-8'))
    result={}
    for name,pin in metadata['files'].items():
        if Path(name).name!=name: raise ValueError('Source manifest paths must be local filenames')
        path=HERE/name
        if path.is_symlink() or not path.is_file() or sha(path)!=pin: raise ValueError('Source pin mismatch: '+name)
        result[name]=pin
    return result

def step(out,name,args,env,timeout):
    row={'argv':args,'startedAt':utc(),'stdout':name+'.stdout.txt','stderr':name+'.stderr.txt'}
    with (out/row['stdout']).open('wb') as stdout,(out/row['stderr']).open('wb') as stderr:
        try:
            child=subprocess.run(args,cwd=HERE,env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,timeout=timeout,check=False)
            row['exitCode']=child.returncode
        except subprocess.TimeoutExpired:
            row['timedOut']=True; row['error']=traceback.format_exc()
    row['finishedAt']=utc()
    (out/(name+'.actual.json')).write_text(json.dumps(row,indent=2),encoding='utf-8')
    # Actual child output is also visible in the hosted job, including failed tests.
    for stream in ['stdout','stderr']:
        content=(out/row[stream]).read_text(encoding='utf-8',errors='replace')
        if content: print(content,end='' if content.endswith('\n') else '\n',file=sys.stderr if stream=='stderr' else sys.stdout,flush=True)
    return row

def good(row): return row.get('exitCode')==0 and not row.get('timedOut')

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--execute',action='store_true')
    ap.add_argument('--output',type=Path)
    args=ap.parse_args()
    if not args.execute:
        print('Source preparation only. Use --execute --output NEW_DIRECTORY for actual offline checks.')
        return 0
    if args.output is None: ap.error('--output is required with --execute')
    pinned=sources()
    out=args.output.resolve()
    if out.exists(): raise ValueError('Preserve earlier evidence: output must be new')
    if out==HERE or HERE in out.parents: raise ValueError('Keep generated output outside tracked source')
    out.mkdir(parents=True,exist_ok=False)
    report={'startedAt':utc(),'sourcePins':pinned,'python':sys.version,'commit':os.environ.get('GITHUB_SHA'),'runId':os.environ.get('GITHUB_RUN_ID'),'repository':os.environ.get('GITHUB_REPOSITORY'),'scope':'offline generated datapack/source tests only','nativeVerified':False,'liveInstalled':False,'worldReadOrWritten':False,'success':False,'steps':{}}
    allowed={'PATH','HOME','LANG','LC_ALL','TMPDIR','SYSTEMROOT','WINDIR'}
    env={key:value for key,value in os.environ.items() if key in allowed}
    env.update(PYTHONUTF8='1',PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1')
    try:
        build=step(out,'generator',[sys.executable,'-B',str(HERE/'build_cannon.py'),'--config',str(HERE/'demo_config.json'),'--output',str(out/'pack'),'--receipt',str(out/'pack-manifest.json')],env,60)
        report['steps']['generator']=build
        if not good(build): raise RuntimeError('Actual generator failed; logs retained')
        manifest=json.loads((out/'pack-manifest.json').read_text(encoding='utf-8'))
        if manifest.get('native_verified') is not False or manifest.get('live_installed') is not False: raise ValueError('Build receipt exceeded offline scope')
        actual={p.relative_to(out/'pack').as_posix():sha(p) for p in (out/'pack').rglob('*') if p.is_file()}
        if not actual or actual!=manifest['files']: raise ValueError('Generated file census/hash mismatch')
        suite=step(out,'unittest',[sys.executable,'-B',str(HERE/'test_cannon_config.py'),'--xml',str(out/'unittest.xml'),'--json',str(out/'unittest.json')],env,180)
        report['steps']['unittest']=suite
        if (out/'unittest.json').is_file(): report['unittest']=json.loads((out/'unittest.json').read_text(encoding='utf-8'))
        if not good(suite) or not report.get('unittest',{}).get('successful') or report['unittest'].get('testsRun',0)<=0: raise RuntimeError('Actual unittest did not pass; exact results retained')
        archive=out/'cannon-pack.zip'
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
            for path in sorted((out/'pack').rglob('*')):
                if path.is_file(): z.write(path,path.relative_to(out/'pack').as_posix())
        report['packArchive']={'name':archive.name,'bytes':archive.stat().st_size,'sha256':sha(archive)}
        report['success']=True
    except BaseException:
        report['error']=traceback.format_exc()
        print(report['error'],file=sys.stderr,flush=True)
    finally:
        report['finishedAt']=utc()
        receipt=out/'SOURCE_CHECK_ACTUAL.json'
        receipt.write_text(json.dumps(report,indent=2),encoding='utf-8')
        total=sum(p.stat().st_size for p in out.rglob('*') if p.is_file())
        report['artifactBytesBeforeFinalReceipt']=total
        report['artifactUploadAllowed']=total+4096<=MAX_ARTIFACT_BYTES
        if not report['artifactUploadAllowed']:
            report['success']=False; report['artifactBudgetError']='Artifact budget exceeded; upload withheld, no logs erased'
        receipt.write_text(json.dumps(report,indent=2),encoding='utf-8')
        action_output=os.environ.get('GITHUB_OUTPUT')
        if action_output:
            with open(action_output,'a',encoding='utf-8') as stream: stream.write('upload_allowed='+str(report['artifactUploadAllowed']).lower()+'\n')
    print(json.dumps({'success':report['success'],'receipt':str(receipt),'nativeVerified':False,'liveInstalled':False}),flush=True)
    return 0 if report['success'] else 1

if __name__=='__main__': raise SystemExit(main())
