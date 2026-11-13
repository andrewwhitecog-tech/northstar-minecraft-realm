"""Read-only validation of the exact reviewed eight-COMPAT adaptation.
No emit, copy, native, installation, networking, or visual acceptance is performed.
"""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import stat
import sys
from contextlib import contextmanager

IDS=('domestic_bengal','domestic_maine_coon','domestic_sphynx','fantasy_obsidian_rainbow')
TEXTURES='java_resourcepack/assets/nsp_cat_coats/textures/entity/cat/'
TARGETS={TEXTURES+name+('_baby' if role=='baby' else '')+'.png':'compat/originals/'+name+'/'+role+'.png' for name in IDS for role in ('adult','baby')}
PACKET_SCHEMA='northstar.cat-representative-native-adapter-source.v1'

def need(ok,message):
    if not ok: raise ValueError(message)

def digest(raw): return hashlib.sha256(raw).hexdigest()

def unique(pairs):
    result={}
    for key,value in pairs:
        need(key not in result,'Duplicate JSON member refused: '+key)
        result[key]=value
    return result

def parsed(raw):
    return json.loads(raw,object_pairs_hook=unique,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Nonfinite JSON refused')))

def unlinked(path):
    path=Path(path)
    need(path.is_absolute() and '..' not in path.parts,'Absolute unescaped path required')
    for part in (path,*path.parents):
        need(not part.is_symlink() and not getattr(part,'is_junction',lambda:False)(),'Linked path refused')
    return path

def regular(path,cap=512*1024):
    path=unlinked(path);s=path.stat()
    need(stat.S_ISREG(s.st_mode) and s.st_size<=cap,'Bounded regular file required')
    need(s.st_nlink==1,'Hard-linked file refused')
    raw=path.read_bytes();need(len(raw)<=cap,'Bounded file changed while reading')
    return raw

def member(root,relative):
    need(isinstance(relative,str) and re.fullmatch(r'[A-Za-z0-9_./-]+',relative) is not None,'Safe relative member required')
    p=PurePosixPath(relative)
    need(not p.is_absolute() and all(x not in ('','.','..') for x in relative.split('/')),'Unsafe member path')
    out=unlinked(root.joinpath(*p.parts));need(out.is_relative_to(root),'Member escapes source root')
    return out

def strict_equal(actual,expected):
    if type(actual) is not type(expected): return False
    if isinstance(expected,dict): return actual.keys()==expected.keys() and all(strict_equal(actual[k],v) for k,v in expected.items())
    if isinstance(expected,list): return len(actual)==len(expected) and all(strict_equal(a,b) for a,b in zip(actual,expected))
    return actual==expected

@contextmanager
def no_bytecode():
    previous=sys.dont_write_bytecode;sys.dont_write_bytecode=True
    try: yield
    finally: sys.dont_write_bytecode=previous

def reviewed_adapter(adapter_home,reviewed_adapter_sha):
    # Authenticate the code before import, then use its actual guarded source graph.
    home=unlinked(adapter_home)
    need(isinstance(reviewed_adapter_sha,str) and re.fullmatch(r'[0-9a-f]{64}',reviewed_adapter_sha) is not None,'Explicit reviewed adapter SHA256 required')
    raw=regular(home/'PUBLIC_ADAPTER_SOURCE.json')
    need(digest(raw)==reviewed_adapter_sha,'Reviewed adapter packet differs')
    packet=parsed(raw);need(packet.get('schema')==PACKET_SCHEMA,'Adapter source schema differs')
    required={'adapt_representatives.py','test_adapter.py','INPUT_PINS.json','dependencies/compile_cat_coats.py','dependencies/roster_public.json','provenance/ORIGINAL_EXPORT_PUBLIC_SOURCE.json','provenance/REPRESENTATIVES_PUBLIC_SOURCE.json','inputs/representatives/REPRESENTATIVE_ACTUAL.json'}|{'inputs/representatives/'+p for p in TARGETS.values()}
    need(isinstance(packet.get('files'),dict) and set(packet['files'])==required,'Exact reviewed adapter graph required')
    for rel,pin in packet['files'].items():
        data=regular(member(home,rel))
        need(isinstance(pin,dict) and type(pin.get('bytes')) is int and len(data)==pin['bytes'] and digest(data)==pin.get('sha256'),'Adapter source/input drift: '+rel)
    spec=importlib.util.spec_from_file_location('reviewed_cat_representative_adapter_'+reviewed_adapter_sha,home/'adapt_representatives.py')
    adapter=importlib.util.module_from_spec(spec)
    with no_bytecode(): spec.loader.exec_module(adapter)
    need(adapter.source_guard(reviewed_adapter_sha)==reviewed_adapter_sha,'Reviewed source guard failed')
    need(tuple(adapter.IDS)==IDS and adapter.TARGETS==TARGETS,'Exact eight-target adapter mapping required')
    return home,adapter

def validate_adapted_input(base_BUILD_path,candidate_BUILD_path,adapter_home,reviewed_adapter_sha):
    """Return (candidate_root, candidate_receipt) only for the exact approved adaptation.

    Base freshness and same-run RUNNER_TEMP/source-graph binding remain the capture
    controller's responsibility. This function authenticates the adapter first and
    then reads only the two pack trees and its reviewed source/COMPAT inputs.
    """
    home,A=reviewed_adapter(adapter_home,reviewed_adapter_sha)
    base_path=unlinked(base_BUILD_path);candidate_path=unlinked(candidate_BUILD_path)
    need(base_path.name==candidate_path.name=='BUILD_ACTUAL.json','Exact BUILD_ACTUAL.json inputs required')
    base=base_path.parent;candidate=candidate_path.parent
    need(candidate!=home and candidate.is_relative_to(home),'Fresh candidate must be below reviewed adapter home')
    need(not any(part.lower() in A.FORBIDDEN for part in candidate.parts),'Staging candidate only; no world/profile paths')
    need(base!=candidate and not base.is_relative_to(candidate) and not candidate.is_relative_to(base),'Base and candidate must be disjoint')
    pins=parsed(regular(home/'INPUT_PINS.json'))
    need(pins.get('schema')=='northstar.cat-representative-native-inputs.v1','Input pins schema differs')
    with no_bytecode(): compiler=A.compiler(pins)
    old_raw,old,payload=A.checked_original(base,pins,compiler)
    rep_raw,replacements=A.checked_replacements(home/'inputs/representatives',pins,compiler)
    # checked_original uses its pinned compiler; independently reject JSON duplicates.
    need(strict_equal(old,parsed(old_raw)),'Original receipt parse differs')
    roster=parsed(regular(home/'dependencies/roster_public.json'))
    full_ids=[r['id'] for r in roster['entries'] if not r['reuseVanilla']]
    need(len(full_ids)==61 and len(set(full_ids))==61,'Complete unique reviewed61 roster required')
    need(type(old.get('rosterEntries')) is int and old['rosterEntries']==len(roster['entries']),'Actual full roster entry count differs')
    need(len(old['selectedIDs'])==61 and set(old['selectedIDs'])==set(full_ids),'Full61 custom IDs required')
    need(set(replacements)==set(TARGETS) and len(payload)==185 and set(TARGETS)<=set(payload),'Exact185/eight-target packet required')
    merged=dict(payload);merged.update(replacements)
    need({p for p in merged if merged[p]!=payload[p]}==set(TARGETS),'All and only eight approved targets must change')
    files={rel:{'sha256':digest(data),'bytes':len(data)} for rel,data in merged.items()}
    expected={
        'schema':'northstar.cat-representative-native-build.v1','success':True,
        'selectedIDs':old['selectedIDs'],'rosterEntries':old['rosterEntries'],
        'customCoatsCompiled':61,'fullCustomRosterCompiled':True,'bedrockAuthoringIncluded':False,
        'files':files,'payloadFiles':185,'changedFiles':sorted(TARGETS),
        'unchangedPayloadFiles':177,'unchangedCoats':57,
        'provenance':{'originalBuildSchema':old['schema'],'originalBuildSha256':digest(old_raw),
            'originalSourcePacketSha256':pins['originalSourcePacketSha256'],
            'compilerSha256':pins['compilerSha256'],'rosterSha256':pins['rosterSha256'],
            'representativeSourcePacketSha256':pins['representativeSourcePacketSha256'],
            'representativeReceiptSha256':digest(rep_raw),'compatInputs':pins['compatInputs'],
            'adapterSourceSha256':digest(regular(home/'adapt_representatives.py')),
            'originalBuildSourceBinding':'Reviewed unchanged compiler/roster; original build receipt has no source-packet field'},
        'inputChecks':'Unchanged original compiler validates full61 pack; COMPAT exact dimensions/CRC/zlib/hash; exact8 deltas and177 byte-identical payload files; source reread before receipt',
        'nativeVerified':False,'humanVisualAccepted':False,'liveInstalled':False,'existingPetsChanged':False,
        'bedrockClientEntityOrGeyserMappingCreated':False,
        'limitations':['Stock Java cat anatomy unchanged','Only four COMPAT adult/baby looks adopted; no HD','No native closeup, all-species, Bedrock, spawn-assignment or pet conversion acceptance']}
    candidate_raw=regular(candidate_path);receipt=parsed(candidate_raw)
    need(strict_equal(receipt,expected),'Candidate receipt differs from exact approved adaptation')
    need(A.inventory(candidate)==set(merged)|{'BUILD_ACTUAL.json'},'Candidate extra or missing member')
    for rel,wanted in merged.items():
        need(regular(member(candidate,rel))==wanted,'Candidate bytes differ from approved input: '+rel)
        # Re-read every baseline member, including those replaced; reject input drift.
        need(regular(member(base,rel))==payload[rel],'Base changed during validation: '+rel)
    validation=compiler.validate_compiled_coats(candidate)
    need(validation['validatedVariants']==61 and validation['validatedFiles']==185,'Actual candidate registry/PNG validation failed')
    need(regular(base_path)==old_raw and regular(candidate_path)==candidate_raw,'Input receipt changed during validation')
    need(A.inventory(base)==set(payload)|{'BUILD_ACTUAL.json'} and A.inventory(candidate)==set(merged)|{'BUILD_ACTUAL.json'},'Input inventory changed during validation')
    # The final source/producer guard is a CAS read, never a second build or native proof.
    need(A.source_guard(reviewed_adapter_sha)==reviewed_adapter_sha,'Reviewed source changed during validation')
    return candidate,receipt
