#!/usr/bin/env python3
"""Compile selected original cat coats only after exact original PNG inputs exist. No world/runtime operations."""
import argparse,hashlib,json,pathlib,re,shutil,struct,tempfile,zlib
HOME=pathlib.Path(__file__).resolve().parent

def need(ok,msg):
 if not ok:raise ValueError(msg)
def sha(data):return hashlib.sha256(data).hexdigest()
def png(path,w,h):
 raw=path.read_bytes();need(len(raw)<=512*1024 and raw[:8]==b'\x89PNG\r\n\x1a\n','Bounded PNG required: '+str(path))
 at=8;payload=[];header=False;ended=False
 while at<len(raw):
  need(at+12<=len(raw),'Truncated PNG');n=struct.unpack('>I',raw[at:at+4])[0];kind=raw[at+4:at+8];end=at+8+n
  need(end+4<=len(raw),'Truncated PNG chunk');body=raw[at+8:end]
  need(zlib.crc32(kind+body)&0xffffffff==struct.unpack('>I',raw[end:end+4])[0],'PNG CRC mismatch')
  if kind==b'IHDR':
   need(not header and n==13,'Duplicate/invalid IHDR');pw,ph,depth,color,compression,filtering,interlace=struct.unpack('>IIBBBBB',body)
   need((pw,ph,depth,color,compression,filtering,interlace)==(w,h,8,6,0,0,0),'Exact RGBA8 un-interlaced UV atlas dimensions required');header=True
  elif kind==b'IDAT':payload.append(body)
  elif kind==b'IEND':need(n==0 and end+4==len(raw),'Invalid terminal PNG');ended=True
  at=end+4
 need(header and ended and payload,'PNG required chunks absent')
 expected=h*(1+w*4);decoder=zlib.decompressobj();decoded=decoder.decompress(b''.join(payload),expected+1)
 need(decoder.eof and not decoder.unconsumed_tail and not decoder.unused_data and len(decoded)==expected,'Invalid/bomb/truncated PNG image data')
 need(all(decoded[y*(1+w*4)]<=4 for y in range(h)),'Invalid PNG scanline filter')
 return raw

def compile_coats(asset_root,ids,out,include_bedrock=False):
 roster=json.loads((HOME/'roster_public.json').read_text(encoding='utf-8'));rows={e['id']:e for e in roster['entries']}
 selected=list(dict.fromkeys(ids));need(selected and len(selected)==len(ids),'Unique explicit IDs required')
 need(all(x in rows and not rows[x]['reuseVanilla'] for x in selected),'Only existing new custom roster IDs may be compiled; vanilla entries are reused, never overwritten')
 asset_root=pathlib.Path(asset_root).resolve(strict=True);out=pathlib.Path(out).resolve()
 need(not out.exists() and not out.is_symlink(),'Fresh output only')
 need(not any(p.lower() in {'saves','v2_master','world','datapacks','resourcepacks'} for p in out.parts),'Staging only, never world/profile installation')
 # Check every source before creating staging: missing assets must not produce a broken pack.
 originals={}
 for rid in selected:
  name=rid.split(':')[1];need(re.fullmatch('[a-z0-9_]+',name) is not None,'Unsafe ID')
  texture_roles=[('adult',64,32),('baby',32,32)]+([('bedrock',128,64)] if include_bedrock else [])
  for role,w,h in texture_roles:
   path=(asset_root/name/(role+'.png')).resolve(strict=True)
   need(path.is_relative_to(asset_root) and not path.is_symlink(),'Unsafe input')
   originals[(rid,role)]=png(path,w,h)
 out.parent.mkdir(parents=True,exist_ok=True);stage=pathlib.Path(tempfile.mkdtemp(prefix=out.name+'.partial.',dir=out.parent))
 try:
  files={}
  def write(rel,data):
   p=stage/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);files[rel]={'sha256':sha(data),'bytes':len(data)}
  def js(rel,value):write(rel,(json.dumps(value,indent=2)+'\n').encode())
  js('java_datapack/pack.mcmeta',{'pack':{'description':'Original NorthStar custom cat coats; no automatic spawn weighting','min_format':[121,0],'max_format':[121,0]}})
  js('java_resourcepack/pack.mcmeta',{'pack':{'description':'Original cat textures; client acceptance pending','min_format':[97,1],'max_format':[97,1]}})
  for rid in selected:
   row=rows[rid];name=rid.split(':')[1]
   js('java_datapack/data/nsp_cat_coats/cat_variant/'+name+'.json',{'asset_id':'nsp_cat_coats:entity/cat/'+name,'baby_asset_id':'nsp_cat_coats:entity/cat/'+name+'_baby','spawn_conditions':[]})
   write('java_resourcepack/assets/nsp_cat_coats/textures/entity/cat/'+name+'.png',originals[(rid,'adult')])
   write('java_resourcepack/assets/nsp_cat_coats/textures/entity/cat/'+name+'_baby.png',originals[(rid,'baby')])
   if include_bedrock:
    write('bedrock_authoring/textures/'+name+'.png',originals[(rid,'bedrock')])
    profile=row['geometryProfile'];geometry=json.loads((HOME/'geometry_source'/(profile+'.geo.json')).read_text(encoding='utf-8'))
    js('bedrock_authoring/models/'+profile+'.geo.json',geometry)
  manifest={'schema':'northstar.cat-coat-build.v1','selectedIDs':selected,'rosterEntries':len(rows),'customCoatsCompiled':len(selected),'fullCustomRosterCompiled':len(selected)==sum(not r['reuseVanilla'] for r in rows.values()),'inputTextureChecks':'actual dimension/CRC/zlib decode only; NOT visual acceptance','files':files,'nativeVerified':False,'humanVisualAccepted':False,'liveInstalled':False,'existingPetsChanged':False,'bedrockAuthoringIncluded':bool(include_bedrock),'bedrockClientEntityOrGeyserMappingCreated':False,'limitations':['Java texture-only CatVariants retain stock anatomy','Bedrock authoring outputs are NOT an installed Bedrock pack or registered entity','No rarity/server assignment hook activated','No existing pet conversion or paid reroll']}
  js('BUILD_ACTUAL.json',manifest);stage.rename(out);return manifest
 except BaseException:
  if stage.exists():shutil.rmtree(stage)
  raise


def validate_compiled_coats(out):
 out=pathlib.Path(out).resolve(strict=True);manifest=json.loads((out/'BUILD_ACTUAL.json').read_text(encoding='utf-8'));ids=manifest['selectedIDs']
 roster={r['id']:r for r in json.loads((HOME/'roster_public.json').read_text(encoding='utf-8'))['entries']}
 need(ids and len(ids)==len(set(ids)) and all(i in roster and not roster[i]['reuseVanilla'] for i in ids),'Compiled IDs must be explicit original variants')
 expected={'java_datapack/pack.mcmeta','java_resourcepack/pack.mcmeta'}
 for rid in ids:
  name=rid.split(':')[1];expected.add('java_datapack/data/nsp_cat_coats/cat_variant/'+name+'.json')
  for suffix in ['', '_baby']:expected.add('java_resourcepack/assets/nsp_cat_coats/textures/entity/cat/'+name+suffix+'.png')
 need(set(manifest['files'])==expected,'Unexpected or missing native pack member')
 actual={p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file()}
 need(actual==expected|{'BUILD_ACTUAL.json'},'Unlisted native pack member')
 for rel,pin in manifest['files'].items():
  p=(out/rel).resolve();need(p.is_relative_to(out) and p.is_file() and not p.is_symlink(),'Unsafe compiled member');data=p.read_bytes()
  need(len(data)==pin['bytes'] and sha(data)==pin['sha256'],'Compiled member byte/hash drift: '+rel)
 for folder,version in [('java_datapack',[121,0]),('java_resourcepack',[97,1])]:
  p=json.loads((out/folder/'pack.mcmeta').read_text())['pack'];need(p['min_format']==version and p['max_format']==version,'Official26.3 pack-format mismatch')
 for rid in ids:
  name=rid.split(':')[1];definition=json.loads((out/'java_datapack/data/nsp_cat_coats/cat_variant'/(name+'.json')).read_text())
  need(definition=={'asset_id':'nsp_cat_coats:entity/cat/'+name,'baby_asset_id':'nsp_cat_coats:entity/cat/'+name+'_baby','spawn_conditions':[]},'Variant references or no-auto-spawn boundary mismatch')
  for suffix,w,h in [('',64,32),('_baby',32,32)]:png(out/'java_resourcepack/assets/nsp_cat_coats/textures/entity/cat'/(name+suffix+'.png'),w,h)
 return {'validatedVariants':len(ids),'validatedOriginalPngs':len(ids)*2,'validatedFiles':len(expected),'automaticSpawnEntries':0,'vanillaNamespaceFiles':0,'nativeVerified':False,'liveInstalled':False}

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--assets-root',type=pathlib.Path,required=True);ap.add_argument('--ids',required=True);ap.add_argument('--out',type=pathlib.Path,required=True);ap.add_argument('--include-bedrock-authoring',action='store_true');a=ap.parse_args()
 manifest=compile_coats(a.assets_root,a.ids.split(','),a.out,a.include_bedrock_authoring);print(json.dumps({'customCoatsCompiled':manifest['customCoatsCompiled'],'nativeVerified':False}))
if __name__=='__main__':main()
