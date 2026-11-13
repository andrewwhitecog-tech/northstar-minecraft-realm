"""Inspect actual exported bytes. No game/native/visual-quality acceptance is inferred."""
from __future__ import annotations
import argparse,hashlib,io,json,math,struct
from pathlib import Path
from PIL import Image,ImageSequence
NS='nsp_pirate_fauna'
BASE={'mutant_rabbit_boss','velvet_hare_duelist','porcelain_rabbit_watchkeeper','stitched_hare_herald'}
SIZE={5126:4,5123:2};WIDTH={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}
def need(ok,message):
 if not ok:raise ValueError(message)
def near(a,b,tol=2e-4):return len(a)==len(b) and all(abs(x-y)<=tol for x,y in zip(a,b))
def readj(p):return json.loads(p.read_text(encoding='utf-8'))
def qmul(a,b):
 x,y,z,w=a;X,Y,Z,W=b
 return (w*X+x*W+y*Z-z*Y,w*Y-x*Z+y*W+z*X,w*Z+x*Y-y*X+z*W,w*W-x*X-y*Y-z*Z)
def rot(q,v):return qmul(qmul(q,(*v,0)),(-q[0],-q[1],-q[2],q[3]))[:3]
def q(axis,degrees):
 r=math.radians(degrees)/2;v=[0.,0.,0.,math.cos(r)];v[axis]=math.sin(r);return v

def open_glb(path):
 b=path.read_bytes();need(len(b)>=28,'Truncated GLB')
 magic,version,total=struct.unpack_from('<4sII',b);need(magic==b'glTF' and version==2 and total==len(b),'GLB header/size mismatch')
 jl,jt=struct.unpack_from('<I4s',b,12);need(jt==b'JSON' and jl%4==0,'Invalid JSON chunk')
 d=json.loads(b[20:20+jl]);bl,bt=struct.unpack_from('<I4s',b,20+jl);need(bt==b'BIN\0' and bl%4==0,'Invalid binary chunk')
 binary=b[28+jl:28+jl+bl];need(len(binary)==bl and 28+jl+bl==len(b),'GLB chunk bounds mismatch')
 need(d['buffers'][0]['byteLength']<=bl,'Declared buffer too long')
 def values(index):
  ac=d['accessors'][index];bv=d['bufferViews'][ac['bufferView']];component=ac['componentType'];width=WIDTH[ac['type']];unit=SIZE[component];start=bv.get('byteOffset',0)+ac.get('byteOffset',0);count=ac['count']
  need(start+count*width*unit<=bv.get('byteOffset',0)+bv['byteLength']<=len(binary),'Accessor escapes actual buffer')
  need(not bv.get('byteStride'),'Unexpected interleaved layout')
  nums=struct.unpack_from('<'+('f' if component==5126 else 'H')*(count*width),binary,start)
  need(all(math.isfinite(v) for v in nums),'Nonfinite GLB data')
  return [tuple(nums[i:i+width]) for i in range(0,len(nums),width)]
 return d,values,binary

def inspect_model(home):
 name=home.name;rig=readj(home/'MODEL/original_rig.json');need(rig['name']==name,'Asset/rig identity mismatch')
 bones=rig['bones'];need(1<len(bones)<=32,'Bone budget outside intended original asset policy')
 order=list(bones);need(order[0]=='root' and bones['root']['parent'] is None,'Missing unique root')
 for bn,b in bones.items():
  seen=set();cur=bn
  while cur is not None:
   need(cur in bones and cur not in seen,'Missing/cyclic parent');seen.add(cur);cur=bones[cur]['parent']
 need(all(min(c['size'])>0 for c in rig['cubes']),'Degenerate cube')
 d,values,binary=open_glb(home/'MODEL'/f'{name}.glb');node_by={n['name']:i for i,n in enumerate(d['nodes'])};need(set(node_by)==set(bones),'GLB bone identity drift')
 image=d['images'][0];need(image['mimeType']=='image/png','Embedded original PNG absent');iv=d['bufferViews'][image['bufferView']];texbytes=binary[iv.get('byteOffset',0):iv.get('byteOffset',0)+iv['byteLength']]
 need(hashlib.sha256(texbytes).digest()==hashlib.sha256((home/'MODEL/palette.png').read_bytes()).digest(),'GLB texture differs from native original atlas')
 with Image.open(io.BytesIO(texbytes)) as painted:
  painted.load();need(painted.size==(128,128) and len(painted.getcolors(16384) or [])>100,'Missing painted texture detail')
 for native in [home/f'java_resourcepack/assets/{NS}/textures/entity/{name}.png',home/f'bedrock_resourcepack/textures/entity/{name}.png']:need(native.read_bytes()==texbytes,'Native texture not identical to GLB embedded atlas')
 for material in d['materials']:need(material['pbrMetallicRoughness']['baseColorTexture']['index']==0,'Untextured GLB material')
 verts={bn:[] for bn in bones};triangle_count=0
 for bn,b in bones.items():
  node=d['nodes'][node_by[bn]];parent=b['parent'];p=b['pivot'];expected=p if parent is None else [p[i]-bones[parent]['pivot'][i] for i in range(3)]
  need(near(node['translation'],[v/16 for v in expected]),'GLB pivot translation drift: '+bn)
  expect_children={node_by[k] for k,v in bones.items() if v['parent']==bn};need(set(node.get('children',[]))==expect_children,'GLB child topology drift')
  if 'mesh' not in node:continue
  for primitive in d['meshes'][node['mesh']]['primitives']:
   pos=values(primitive['attributes']['POSITION']);normal=values(primitive['attributes']['NORMAL']);indices=values(primitive['indices']);uvs=values(primitive['attributes']['TEXCOORD_0']);need(len(pos)==len(normal)==len(uvs),'Normal/UV/vertex count mismatch');need(all(0<=u<=1 and 0<=v<=1 for u,v in uvs),'UV escapes atlas')
   need(all(abs(sum(v*v for v in n)-1)<1e-3 for n in normal),'Non-unit normal')
   need(all(0<=i[0]<len(pos) for i in indices),'Index outside actual vertices');triangle_count+=len(indices)//3;verts[bn].extend(set(pos))
 need(triangle_count==len(rig['cubes'])*12,'Actual geometry lost cubes/triangles')
 actual_clips={a['name']:a for a in d['animations']};expected_clips={k:v for k,v in rig['clips'].items() if v};need(set(actual_clips)==set(expected_clips),'GLB clip coverage drift')
 actual_poses={};motion=[]
 for clip,channels in expected_clips.items():
  anim=actual_clips[clip];got={d['nodes'][ch['target']['node']]['name']:ch for ch in anim['channels']};need(set(got)==set(channels),'Animation bone coverage drift')
  sample_times=None;rotations={}
  for bn,(axis,amp,phase) in channels.items():
   ch=got[bn];need(ch['target']['path']=='rotation','Unexpected animation target');sampler=anim['samplers'][ch['sampler']];times=[v[0] for v in values(sampler['input'])];qs=values(sampler['output'])
   need(len(times)==len(qs)>2 and times[0]==0 and all(b>a for a,b in zip(times,times[1:])),'Invalid animation time sequence')
   need(sample_times is None or times==sample_times,'Unaligned rig channels');sample_times=times
   need(all(abs(sum(v*v for v in r)-1)<2e-4 for r in qs),'Nonunit quaternion')
   for t,r in zip(times,qs):need(near(r,q(axis,amp*math.sin(t/times[-1]*math.tau+phase))),'Actual animation differs from rig channel')
   rotations[bn]=qs;motion.append(any(not near(qs[0],r,1e-5) for r in qs[1:]))
  poses=[]
  for frame in range(len(sample_times)-1):
   world={};points=[]
   for bn,b in bones.items():
    localq=rotations.get(bn,[(0,0,0,1)]*len(sample_times))[frame];parent=b['parent'];localp=tuple(d['nodes'][node_by[bn]]['translation'])
    if parent:
     pq,pp=world[parent];wq=qmul(pq,localq);rv=rot(pq,localp);wp=tuple(pp[k]+rv[k] for k in range(3))
    else:wq=localq;wp=localp
    world[bn]=(wq,wp)
    for v in verts[bn]:
     rv=rot(wq,v);points.append(tuple(wp[k]+rv[k] for k in range(3)))
   poses.append({'clip':clip,'frame':frame,'bones':{k:{'translation':v[1],'rotation':v[0]} for k,v in world.items()},'min':[min(p[k] for p in points) for k in range(3)],'max':[max(p[k] for p in points) for k in range(3)]})
  actual_poses[clip]=poses
 need(any(motion),'No actual articulated quaternion motion')
 reported=readj(home/'MODEL/POSE_BOUNDS_ACTUAL.json')
 expected_rows={(clip,frame) for clip in actual_poses for frame in range(16)}
 actual_rows={(row['clip'],row['frame']) for row in reported if row['clip'] in actual_poses}
 need(actual_rows==expected_rows,'Animated bounds receipt frame coverage drift')
 for row in reported:
  #Empty authored clips are allowed as no-op selectors, but cannot replace requested motion clips.
  if row['clip'] not in actual_poses:continue
  got=actual_poses[row['clip']][row['frame']];need(near(row['min'],got['min']) and near(row['max'],got['max']),'Actual GLB animated bounds disagree with pose receipt')
 geo_counts=0
 for layer in ['body','eyes']:
  geo=readj(home/f'bedrock_resourcepack/models/entity/{name}_{layer}.geo.json')['minecraft:geometry'][0];gb={b['name']:b for b in geo['bones']};need(set(gb)==set(bones),'Bedrock bone identity drift')
  for bn,b in bones.items():
   target=gb[bn];pv=b['pivot'];need(near(target['pivot'],[pv[0],pv[1],-pv[2]]),'Bedrock pivot conversion drift');need(target.get('parent')==b['parent'],'Bedrock parent drift')
   for cube in target.get('cubes',[]):need(min(cube['size'])>0,'Degenerate Bedrock cube');geo_counts+=1
 need(geo_counts==len(rig['cubes']),'Bedrock body/eye layer coverage drift')
 assembly=readj(home/'MODEL/java_bone_assembly.json')['parts'];need({p['bone'] for p in assembly}=={c['bone'] for c in rig['cubes']},'Java bone coverage drift')
 for part in assembly:
  bn=part['bone'];j=readj(home/f'java_resourcepack/assets/{NS}/models/item/{name}/{bn}.json')
  need(len(j['elements'])==sum(c['bone']==bn for c in rig['cubes']),'Java element loss')
  for el in j['elements']:need(all(-16<=v<=32 for v in el['from']+el['to']),'Java model element exceeds native coordinate limits')
 for clip,poses in actual_poses.items():
  for row in poses:
   file=home/f'java_datapack_src/data/{NS}/function/pose/{name}/{clip}/{row["frame"]:02d}.mcfunction';text=file.read_text();need(text.count('run data merge entity @s ')==len(assembly),'Java pose bone count drift')
   for line in text.splitlines():
    if 'run data merge entity @s ' not in line:continue
    payload=json.loads(line.split('run data merge entity @s ',1)[1]);tr=payload['transformation'];need(all(math.isfinite(v) for v in tr['translation']+tr['left_rotation']),'Nonfinite Java pose');bn=line.split('.bone.',1)[1].split(']',1)[0];need(near(tr['translation'],row['bones'][bn]['translation']) and near(tr['left_rotation'],row['bones'][bn]['rotation']),'Java pose differs from actual GLB animation')
 bd_anim=readj(home/f'bedrock_resourcepack/animations/{name}.animation.json')['animations']
 for clip,channels in expected_clips.items():
  key='animation.'+NS+'.'+name+'.'+clip;need(key in bd_anim,'Bedrock clip missing');bd=bd_anim[key];need(set(bd['bones'])==set(channels),'Bedrock animation-bone coverage drift')
  for bn,(axis,amp,phase) in channels.items():
   for keytime,degrees in bd['bones'][bn]['rotation'].items():
    expect=[0,0,0];expect[axis]=amp*math.sin(float(keytime)/bd['animation_length']*math.tau+phase)*(-1 if axis in [0,1] else 1);need(near(degrees,expect),'Bedrock animated rotation conversion drift')
 need(readj(home/f'bedrock_resourcepack/entity/{name}.entity.json')['minecraft:client_entity']['description']['identifier']==NS+':'+name,'Bedrock provisional ID drift')
 previews=home/'previews';pngs=list(previews.glob('*.png'));gifs=list(previews.glob('*.gif'));need(len(pngs)==1 and len(gifs)==(2 if 'breach' in rig['clips'] else 1),'Actual preview file count does not match recipe')
 with Image.open(pngs[0]) as im:
  im.load();need(im.size==(2000,2000),'Four-view sheet size drift');need(len(im.getcolors(im.width*im.height) or [])>8,'Uniform/unrendered model preview')
 counts=[]
 for path in gifs:
  with Image.open(path) as im:
   frame_hashes=[]
   for frame in ImageSequence.Iterator(im):
    need(frame.info.get('duration',0)>0,'GIF duration missing');frame_hashes.append(hashlib.sha256(frame.convert('RGB').tobytes()).hexdigest())
   need(len(frame_hashes)==16 and len(set(frame_hashes))>1,'No genuine distinct articulated preview frames');counts.append({'file':path.name,'frames':len(frame_hashes),'distinct':len(set(frame_hashes))})
 return {'id':NS+':'+name,'bones':len(bones),'cubes':len(rig['cubes']),'actual_triangles':triangle_count,'actual_clips':list(actual_clips),'java_displays':len(assembly),'preview_pngs':len(pngs),'preview_gifs':counts,'native_verified':False,'personal_visual_approved':False}

def inspect_set(out,expected):
 need(out.is_dir(),'Output directory absent');actual={p.name for p in out.iterdir() if p.is_dir()};need(actual==expected,'Requested model coverage mismatch: missing='+str(expected-actual)+' extra='+str(actual-expected))
 rows=[inspect_model(out/name) for name in sorted(expected)]
 return {'models':rows,'actual_model_count':len(rows),'actual_preview_sheet_count':sum(x['preview_pngs'] for x in rows),'actual_gif_count':sum(len(x['preview_gifs']) for x in rows),'native_verified':False,'personal_visual_approved':False}
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--output',required=True,type=Path);ap.add_argument('--receipt',required=True,type=Path);a=ap.parse_args()
 result=inspect_set(a.output,BASE);result['scope']='Four replacement rabbits: actual bytes, painted UV textures, rig/animation/bounds/preview validation; no visual/native acceptance';a.receipt.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({'actual_replacement_models':result['actual_model_count']}))
