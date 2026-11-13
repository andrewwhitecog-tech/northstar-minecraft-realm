"""New-only adapter: four approved COMPAT adult/baby coats, stock Java anatomy.
No painter, renderer, native process, world installation, network or dependency install.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path, PurePosixPath
import stat
import traceback

HOME=Path(__file__).resolve().parent
IDS=('domestic_bengal','domestic_maine_coon','domestic_sphynx','fantasy_obsidian_rainbow')
TEXTURES='java_resourcepack/assets/nsp_cat_coats/textures/entity/cat/'
TARGETS={TEXTURES+name+('_baby' if role=='baby' else '')+'.png':'compat/originals/'+name+'/'+role+'.png' for name in IDS for role in ('adult','baby')}
FORBIDDEN={'saves','world','v2_master','.minecraft','srv','mods','datapacks','resourcepacks'}


def need(ok,message):
    if not ok:raise ValueError(message)


def digest(raw):return hashlib.sha256(raw).hexdigest()


def unlinked(path):
    path=Path(path)
    need(path.is_absolute() and '..' not in path.parts,'Absolute unescaped path required')
    for part in (path,*path.parents):
        need(not part.is_symlink() and not getattr(part,'is_junction',lambda:False)(),'Linked path refused: '+str(part))
    return path


def member(root,rel):
    need(isinstance(rel,str) and re.fullmatch(r'[A-Za-z0-9_./-]+',rel) is not None,'Safe member spelling required')
    p=PurePosixPath(rel)
    need(rel and not p.is_absolute() and '\\' not in rel and all(v not in ('','.','..') for v in rel.split('/')),'Unsafe member path')
    root=unlinked(Path(root));out=unlinked(root.joinpath(*p.parts))
    need(out.is_relative_to(root),'Member escapes root')
    return out


def read(root,rel,cap=512*1024):
    p=member(root,rel)
    need(p.is_file() and stat.S_ISREG(p.stat().st_mode) and p.stat().st_size<=cap,'Bounded regular source required: '+rel)
    with p.open('rb') as f:raw=f.read(cap+1)
    need(len(raw)<=cap,'Input exceeds cap: '+rel)
    return raw


def inventory(root):
    root=unlinked(Path(root));need(root.is_dir(),'Existing source directory required')
    result=set();visited=0
    for folder,dirs,files in os.walk(root,followlinks=False):
        visited+=1;need(visited<=512,'Directory count cap')
        for name in dirs:unlinked(Path(folder)/name)
        for name in files:
            p=unlinked(Path(folder)/name);need(stat.S_ISREG(p.stat().st_mode),'Nonregular member refused')
            result.add(p.relative_to(root).as_posix());need(len(result)<=512,'File count cap')
    return result


def source_guard(expected=None):
    raw=read(HOME,'PUBLIC_ADAPTER_SOURCE.json')
    if expected is not None:need(digest(raw)==expected,'Reviewed adapter packet differs')
    packet=json.loads(raw)
    for rel,pin in packet['files'].items():
        data=read(HOME,rel)
        need(len(data)==pin['bytes'] and digest(data)==pin['sha256'],'Adapter source/input drift: '+rel)
    return digest(raw)


def compiler(pins):
    raw=read(HOME,'dependencies/compile_cat_coats.py')
    roster=read(HOME,'dependencies/roster_public.json')
    need(digest(raw)==pins['compilerSha256'] and digest(roster)==pins['rosterSha256'],'Pinned unchanged compiler/roster required')
    packet_raw=read(HOME,'provenance/ORIGINAL_EXPORT_PUBLIC_SOURCE.json')
    need(digest(packet_raw)==pins['originalSourcePacketSha256'],'Original source packet mismatch')
    files={r['path']:r for r in json.loads(packet_raw)['files']}
    for rel,data in [('compile_cat_coats.py',raw),('roster_public.json',roster)]:
        need(files[rel]['sha256']==digest(data) and files[rel]['bytes']==len(data),'Compiler not bound to reviewed original source packet')
    spec=importlib.util.spec_from_file_location('exact_coat_compiler',HOME/'dependencies/compile_cat_coats.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def checked_original(root,pins,c):
    raw=read(root,'BUILD_ACTUAL.json')
    need(digest(raw)==pins['originalBuildSha256'],'Reviewed original build receipt mismatch')
    receipt=json.loads(raw)
    need(receipt['schema']=='northstar.cat-coat-build.v1' and receipt['customCoatsCompiled']==61 and receipt['fullCustomRosterCompiled'] is True and receipt['bedrockAuthoringIncluded'] is False,'Complete original61 Java-only pack required')
    need(len(receipt['files'])==185,'Original185 payload files required')
    validated=c.validate_compiled_coats(root)
    need(validated['validatedVariants']==61 and validated['validatedFiles']==185,'Actual original compiler validation failed')
    payload={rel:read(root,rel) for rel in receipt['files']}
    need(inventory(root)==set(payload)|{'BUILD_ACTUAL.json'},'Exact original file allowlist required')
    need(all(len(b)==receipt['files'][p]['bytes'] and digest(b)==receipt['files'][p]['sha256'] for p,b in payload.items()),'Original payload drift during validation')
    return raw,receipt,payload


def checked_replacements(root,pins,c):
    packet_raw=read(HOME,'provenance/REPRESENTATIVES_PUBLIC_SOURCE.json')
    need(digest(packet_raw)==pins['representativeSourcePacketSha256'],'Representative source packet mismatch')
    packet=json.loads(packet_raw)
    need(set(packet['representatives'])==set(IDS) and len(packet['representatives'])==4,'Exact reviewed four representatives required')
    raw=read(root,'REPRESENTATIVE_ACTUAL.json')
    need(digest(raw)==pins['representativeReceiptSha256'],'Representative producer receipt mismatch')
    receipt=json.loads(raw)
    need(receipt['schema']=='northstar.cat-representative-actual.v3' and receipt['passed'] is True and receipt['errors']==[] and receipt['representativeCount']==4 and receipt['sourcePacketSha256']==pins['representativeSourcePacketSha256'],'Actual successful representative producer receipt required')
    tests=receipt['tests'];need(tests['testsRun']>0 and all(tests[k]==0 for k in ('failures','errors','skipped')),'Clean actual representative producer tests required')
    rows=receipt['files'];need(len(rows)==len({r['path'] for r in rows}),'Duplicate producer members refused')
    records={r['path']:r for r in rows}
    expected={r['path']:r for r in pins['compatInputs']}
    need(len(expected)==8 and set(expected)==set(TARGETS.values()),'Exactly eight COMPAT input pins required')
    replacements={}
    for target,rel in TARGETS.items():
        need(rel in records and records[rel]==expected[rel],'Exact approved COMPAT producer pin required')
        p=member(root,rel);data=c.png(p,32 if rel.endswith('/baby.png') else 64,32)
        pin=expected[rel];need(len(data)==pin['bytes'] and digest(data)==pin['sha256'],'COMPAT byte/hash mismatch')
        replacements[target]=data
    return raw,replacements


def emit(original,representatives,out,pins):
    original,representatives,out=map(lambda p:unlinked(Path(p)),(original,representatives,out))
    need(out.is_relative_to(HOME) and out!=HOME and out.parent.is_dir() and not out.exists(),'New output below owned adapter home only')
    need(not any(p.lower() in FORBIDDEN for p in out.parts),'Staging only; no world/profile output')
    need(not any(out==src or out.is_relative_to(src) or src.is_relative_to(out) for src in (original,representatives)),'Input/output trees must be disjoint')
    c=compiler(pins)
    old_raw,old,payload=checked_original(original,pins,c)
    rep_raw,replacements=checked_replacements(representatives,pins,c)
    need(set(replacements)==set(TARGETS) and set(TARGETS)<=set(payload),'Exact eight existing target textures required')
    changed={p for p in payload if p in replacements and payload[p]!=replacements[p]}
    need(changed==set(TARGETS),'Every approved target must change; no hidden/no-op adoption')
    merged=dict(payload);merged.update(replacements)
    need(len(merged)==185 and {p for p in merged if merged[p]!=payload[p]}==set(TARGETS),'Only exact eight changes permitted')
    # Claim fresh tree only after all input/type/CRC/hash validations succeed.
    out.mkdir(exist_ok=False)
    try:
        for rel,data in merged.items():
            p=member(out,rel);p.parent.mkdir(parents=True,exist_ok=True)
            with p.open('xb') as f:f.write(data)
        need(inventory(out)==set(merged),'Unexpected output member')
        for rel,data in merged.items():need(read(out,rel)==data,'Actual output byte mismatch: '+rel)
        # CAS-style input immutability check before final honest receipt.
        need(read(original,'BUILD_ACTUAL.json')==old_raw and read(representatives,'REPRESENTATIVE_ACTUAL.json')==rep_raw,'Input receipt changed during adaptation')
        need(inventory(original)==set(payload)|{'BUILD_ACTUAL.json'},'Original inventory changed during adaptation')
        for rel,data in payload.items():need(read(original,rel)==data,'Original pack changed during adaptation: '+rel)
        for target,rel in TARGETS.items():need(read(representatives,rel)==replacements[target],'Representative changed during adaptation: '+rel)
        files={p:{'sha256':digest(b),'bytes':len(b)} for p,b in merged.items()}
        receipt={'schema':'northstar.cat-representative-native-build.v1','success':True,
                 'selectedIDs':old['selectedIDs'],'rosterEntries':old['rosterEntries'],
                 'customCoatsCompiled':61,'fullCustomRosterCompiled':True,'bedrockAuthoringIncluded':False,
                 'files':files,'payloadFiles':len(files),'changedFiles':sorted(changed),
                 'unchangedPayloadFiles':len(files)-len(changed),'unchangedCoats':61-len(IDS),
                 'provenance':{'originalBuildSchema':old['schema'],'originalBuildSha256':digest(old_raw),
                    'originalSourcePacketSha256':pins['originalSourcePacketSha256'],
                    'compilerSha256':pins['compilerSha256'],'rosterSha256':pins['rosterSha256'],
                    'representativeSourcePacketSha256':pins['representativeSourcePacketSha256'],
                    'representativeReceiptSha256':digest(rep_raw),'compatInputs':pins['compatInputs'],
                    'adapterSourceSha256':digest(Path(__file__).read_bytes()),
                    'originalBuildSourceBinding':'Reviewed unchanged compiler/roster; original build receipt has no source-packet field'},
                 'inputChecks':'Unchanged original compiler validates full61 pack; COMPAT exact dimensions/CRC/zlib/hash; exact8 deltas and177 byte-identical payload files; source reread before receipt',
                 'nativeVerified':False,'humanVisualAccepted':False,'liveInstalled':False,'existingPetsChanged':False,
                 'bedrockClientEntityOrGeyserMappingCreated':False,
                 'limitations':['Stock Java cat anatomy unchanged','Only four COMPAT adult/baby looks adopted; no HD','No native closeup, all-species, Bedrock, spawn-assignment or pet conversion acceptance']}
        with (out/'BUILD_ACTUAL.json').open('x',encoding='utf8') as f:json.dump(receipt,f,indent=2);f.write('\n')
        return receipt
    except BaseException:
        with (out/'BUILD_FAILURE.json').open('x',encoding='utf8') as f:json.dump({'success':False,'error':traceback.format_exc(),'nativeVerified':False},f,indent=2)
        raise


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute',action='store_true');p.add_argument('--reviewed-adapter-sha256')
    p.add_argument('--original-pack',type=Path);p.add_argument('--representatives',type=Path,default=HOME/'inputs/representatives')
    p.add_argument('--out-name',default='native_representative_pack_v01')
    a=p.parse_args();packet=source_guard(a.reviewed_adapter_sha256)
    if not a.execute:print(json.dumps({'sourceVerified':True,'executed':False,'nativeVerified':False,'sourcePacketSha256':packet}));return 0
    need(a.reviewed_adapter_sha256 is not None and a.original_pack is not None,'Explicit reviewed packet and original pack required')
    need(a.out_name and a.out_name.replace('_','').replace('-','').isalnum() and len(a.out_name)<=60,'Safe new output name required')
    result=emit(a.original_pack,a.representatives,HOME/a.out_name,json.loads(read(HOME,'INPUT_PINS.json')))
    print(json.dumps({'success':result['success'],'payloadFiles':result['payloadFiles'],'changedFiles':len(result['changedFiles']),'nativeVerified':False,'output':str(HOME/a.out_name)}));return 0


if __name__=='__main__':raise SystemExit(main())
