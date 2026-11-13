#!/usr/bin/env python3
"""Explicit free-hosted four-cat paint+CPU-render batch. Never exports all61 or launches Minecraft."""
import argparse
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


def guard():
    packet=json.loads((ROOT/'PUBLIC_SOURCE.json').read_text(encoding='utf-8'))
    for r in packet['files']:
        path=Path(r['path'])
        if path.is_absolute() or '..' in path.parts: raise ValueError('Unsafe allowlist')
        p=ROOT/path
        if p.is_symlink() or not p.resolve().is_relative_to(ROOT): raise ValueError('Source escape')
        b=p.read_bytes()
        if len(b)!=r['bytes'] or hashlib.sha256(b).hexdigest()!=r['sha256']: raise ValueError('Source drift: '+r['path'])
    return packet

class Results(unittest.TextTestResult):
    def __init__(self,*a,**k): super().__init__(*a,**k); self.rows=[]
    def addSuccess(self,t): super().addSuccess(t);self.rows.append({'name':t.id(),'status':'passed'})
    def addFailure(self,t,e): super().addFailure(t,e);self.rows.append({'name':t.id(),'status':'failure','detail':self._exc_info_to_string(e,t)})
    def addError(self,t,e): super().addError(t,e);self.rows.append({'name':t.id(),'status':'error','detail':self._exc_info_to_string(e,t)})
    def addSkip(self,t,r): super().addSkip(t,r);self.rows.append({'name':t.id(),'status':'skipped','detail':r})

def execute(out,scale,size,modes):
    guard(); out=Path(out).resolve()
    if out.exists() or out==ROOT or out.is_relative_to(ROOT): raise ValueError('Fresh output outside source required')
    if any(p.lower() in ('saves','mods','resourcepacks','datapacks','world','srv','v2_master','.minecraft') for p in out.parts): raise ValueError('No world/profile output')
    if scale not in (1,4) or not 64<=size<=512: raise ValueError('Scale1/4 and viewSize64..512 only')
    if not modes or len(modes)!=len(set(modes)) or not set(modes)<={'adult','baby','bedrock'}: raise ValueError('Only actual known model modes')
    out.mkdir(parents=True,exist_ok=False)
    receipt={'schema':'northstar.cat-representative-actual.v3','startedUtc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
             'sourcePacketSha256':hashlib.sha256((ROOT/'PUBLIC_SOURCE.json').read_bytes()).hexdigest(),
             'testsStarted':False,'paintStarted':False,'renderStarted':False,'passed':False,'errors':[],
             'nativeRun':False,'visualPersonalQC':False,'gameInstalled':False,'mappingIDsAssigned':False,
             'full61Repainted':False,'sheets':[],'files':[]}
    try:
        sys.path.insert(0,str(ROOT))
        import test_representatives as T
        import baseline_paint as B
        import representative_painter as P
        import render_four_views as R
        receipt['testsStarted']=True; stream=io.StringIO()
        result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Results).run(unittest.defaultTestLoader.loadTestsFromModule(T))
        (out/'unittest.actual.txt').write_text(stream.getvalue(),encoding='utf-8')
        receipt['tests']={'testsRun':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'rows':result.rows}
        (out/'unittest.actual.json').write_text(json.dumps(receipt['tests'],indent=2)+'\n',encoding='utf-8')
        xml=ET.Element('testsuite',tests=str(result.testsRun),failures=str(len(result.failures)),errors=str(len(result.errors)),skipped=str(len(result.skipped)))
        for row in result.rows:
            node=ET.SubElement(xml,'testcase',name=row['name'])
            if row['status']!='passed': ET.SubElement(node,row['status']).text=row.get('detail','')
        ET.ElementTree(xml).write(out/'unittest.actual.xml',encoding='utf-8',xml_declaration=True)
        if result.testsRun==0 or not result.wasSuccessful(): raise RuntimeError('Actual tests failed; preserved transcripts')
        cfg,models=P.model_sources()
        def write(rel,data):
            p=out/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
            receipt['files'].append({'path':rel,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
        receipt['paintStarted']=True
        for name,group in models.items():
            for atlas_scale in sorted({1,scale}):
                for mode,m in group.items():
                    w,h,pixels,count=P.paint(name,m,atlas_scale)
                    write(('compat' if atlas_scale==1 else 'detail')+'/originals/'+name+'/'+mode+'.png',B.png_bytes(w,h,pixels))
            write('geometry_source/'+name+'.geo.json',(json.dumps(group['bedrock']['geometry'],indent=2)+'\n').encode())
        receipt['renderStarted']=True
        for name,group in models.items():
            for mode in modes:
                rel='sheets/'+name+'_'+mode+'_4view.png'; path=out/rel; path.parent.mkdir(parents=True,exist_ok=True)
                texture=out/('compat' if scale==1 else 'detail')/'originals'/name/(mode+'.png')
                stats=R.sheet(group[mode],texture,path,size,'obsidian' if name.startswith('fantasy_') else 'fur')
                actual=R.decode_png(path)
                if actual[0]!=size*2 or actual[1]!=size*2: raise ValueError('Rendered sheet decode dimensions')
                receipt['sheets'].append({'path':rel,'coat':name,'mode':mode,**stats})
                data=path.read_bytes();receipt['files'].append({'path':rel,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
        receipt['pngCount']=sum(r['path'].endswith('.png') for r in receipt['files'])
        receipt['representativeCount']=len(models);guard();receipt['passed']=True
    except BaseException:
        receipt['errors'].append(traceback.format_exc())
    finally:
        receipt['finishedUtc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
        receipt['scope']='Original four-look assets and real CPU textured-geometry review sheets only; no native/live/Bedrock acceptance.'
        (out/'REPRESENTATIVE_ACTUAL.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    total=sum(p.stat().st_size for p in out.rglob('*') if p.is_file())
    print(json.dumps({'passed':receipt['passed'],'tests':receipt.get('tests',{}).get('testsRun',0),'sheets':len(receipt['sheets']),'bytes':total,'nativeRun':False}))
    if total>32*1024*1024: print('Artifact exceeds32MiB; not uploaded',file=sys.stderr);return 2
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8') as f:f.write('upload_allowed=true\n')
    return 0 if receipt['passed'] else 1

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true');p.add_argument('--out',type=Path)
    p.add_argument('--atlas-scale',type=int,choices=(1,4),default=4);p.add_argument('--view-size',type=int,default=384)
    p.add_argument('--models',default='adult,baby,bedrock')
    a=p.parse_args()
    if not a.execute or not a.out:p.error('Explicit --execute --out NEW_FOLDER required')
    return execute(a.out,a.atlas_scale,a.view_size,a.models.split(','))
if __name__=='__main__':raise SystemExit(main())
