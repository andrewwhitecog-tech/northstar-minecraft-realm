#!/usr/bin/env python3
"""Free hosted source/test/export entry point; no native server/client or network call."""
from __future__ import annotations
import argparse
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import time
import traceback
import unittest
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parent


def source_guard():
    packet=json.loads((ROOT/'PUBLIC_EXPORT_SOURCE.json').read_text(encoding='utf-8'))
    paths=set()
    for row in packet['files']:
        rel=Path(row['path'])
        if rel.is_absolute() or '..' in rel.parts or row['path'] in paths: raise ValueError('Unsafe/duplicate allowlist entry')
        paths.add(row['path']); p=ROOT/rel
        if p.is_symlink() or not p.is_file() or not p.resolve().is_relative_to(ROOT): raise ValueError('Source escape')
        b=p.read_bytes()
        if len(b)!=row['bytes'] or hashlib.sha256(b).hexdigest()!=row['sha256']: raise ValueError('Source drift: '+row['path'])
    required={'paint_cat_coats.py','test_paint_cat_coats.py','review_viewer.html','coat_recipes.json','roster_public.json','uv_models.json','run_hosted_export.py'}
    if not required<=paths: raise ValueError('Incomplete public packet')
    return packet

class ActualResult(unittest.TextTestResult):
    def __init__(self,*args,**kwargs): super().__init__(*args,**kwargs); self.rows=[]; self.starts={}
    def startTest(self,test): self.starts[test.id()]=time.monotonic(); super().startTest(test)
    def record(self,test,status,detail=''): self.rows.append({'name':test.id(),'status':status,'seconds':round(time.monotonic()-self.starts.get(test.id(),time.monotonic()),5),'detail':detail})
    def addSuccess(self,test): super().addSuccess(test); self.record(test,'passed')
    def addFailure(self,test,err): super().addFailure(test,err); self.record(test,'failure',self._exc_info_to_string(err,test))
    def addError(self,test,err): super().addError(test,err); self.record(test,'error',self._exc_info_to_string(err,test))
    def addSkip(self,test,reason): super().addSkip(test,reason); self.record(test,'skipped',reason)
    def addSubTest(self,test,subtest,err):
        super().addSubTest(test,subtest,err)
        if err: self.record(subtest,'failure' if issubclass(err[0],test.failureException) else 'error',self._exc_info_to_string(err,test))

def execute(out):
    packet=source_guard(); out=Path(out).resolve()
    if out.exists() or out==ROOT or out.is_relative_to(ROOT): raise ValueError('New output outside source required')
    if any(p.lower() in ('saves','mods','resourcepacks','datapacks','world','v2_master','.minecraft') for p in out.parts): raise ValueError('No profile/world output')
    out.mkdir(parents=True,exist_ok=False)
    receipt={'schema':'northstar.cat-paint-hosted-actual.v1','startedUtc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
             'testsStarted':False,'exportStarted':False,'passed':False,'nativeRun':False,'renderedPersonalQC':False,
             'sourcePacketSha256':hashlib.sha256((ROOT/'PUBLIC_EXPORT_SOURCE.json').read_bytes()).hexdigest(),
             'python':sys.version,'errors':[]}
    try:
        # Imports only AFTER every public source byte has matched the frozen packet.
        sys.path.insert(0,str(ROOT))
        import test_paint_cat_coats
        suite=unittest.defaultTestLoader.loadTestsFromModule(test_paint_cat_coats)
        receipt['testsStarted']=True; stream=io.StringIO()
        result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=ActualResult).run(suite)
        (out/'unittest.actual.txt').write_text(stream.getvalue(),encoding='utf-8')
        test_receipt={'testsRun':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),
                      'successful':result.wasSuccessful(),'rows':result.rows}
        (out/'unittest.actual.json').write_text(json.dumps(test_receipt,indent=2)+'\n',encoding='utf-8')
        xml=ET.Element('testsuite',name='cat-paint-export',tests=str(result.testsRun),failures=str(len(result.failures)),errors=str(len(result.errors)),skipped=str(len(result.skipped)))
        for row in result.rows:
            node=ET.SubElement(xml,'testcase',name=row['name'],time=str(row['seconds']))
            if row['status']!='passed': ET.SubElement(node,row['status']).text=row['detail']
        ET.ElementTree(xml).write(out/'unittest.actual.xml',encoding='utf-8',xml_declaration=True)
        receipt['tests']=test_receipt
        if not result.wasSuccessful() or result.testsRun==0: raise RuntimeError('Actual unittest failed; inspect preserved transcript')
        import paint_cat_coats
        receipt['exportStarted']=True
        export=paint_cat_coats.export(out/'export',include_nyan=True)
        receipt['export']={k:export[k] for k in ('exportedSets','pngCount','reusedReferences','status')}
        source_guard() # read-only check that tests/export changed no source bytes
        receipt['passed']=True
    except BaseException:
        receipt['errors'].append(traceback.format_exc())
    finally:
        receipt['finishedUtc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
        (out/'HOSTED_EXPORT_ACTUAL.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
        total=sum(p.stat().st_size for p in out.rglob('*') if p.is_file())
        print(json.dumps({'passed':receipt['passed'],'testsStarted':receipt['testsStarted'],'exportStarted':receipt['exportStarted'],'bytes':total,'nativeRun':False}))
    if total>12*1024*1024: print('Artifact too large; do not upload',file=sys.stderr); return 2
    # Bounded FAILED transcripts are also retained for diagnosis; success is never assumed.
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8') as f: f.write('upload_allowed=true\n')
    return 0 if receipt['passed'] else 1

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--execute',action='store_true'); p.add_argument('--out',type=Path)
    a=p.parse_args()
    if not a.execute or not a.out: p.error('Explicit --execute --out NEW_FOLDER required; import/default is inert')
    return execute(a.out)
if __name__=='__main__': raise SystemExit(main())
