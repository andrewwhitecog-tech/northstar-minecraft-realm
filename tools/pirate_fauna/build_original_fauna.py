"""Original articulated pirate fauna assets; no provider, registry, native or live writes."""
from __future__ import annotations
import argparse,ctypes,hashlib,json,math,os,struct,sys,uuid,zipfile
from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parent
NS='nsp_pirate_fauna'
PALETTE={'bone':(218,204,167),'bone_light':(248,233,196),'bone_shadow':(135,119,91),'black':(20,24,35),'gold':(218,161,51),'teal':(31,190,179),'violet':(130,63,194),'red':(198,55,93),'blue':(51,111,208),'green':(69,167,123),'dark_skin':(39,64,76),'skin':(79,112,127),'belly':(181,201,196),'eye':(86,229,204)}
COLORS=list(PALETTE)
FACES=[((0,0,1),(0,1,2,3)),((0,0,-1),(5,4,7,6)),((1,0,0),(1,5,6,2)),((-1,0,0),(4,0,3,7)),((0,1,0),(3,2,6,7)),((0,-1,0),(4,5,1,0))]

def qmul(a,b):
 x,y,z,w=a; X,Y,Z,W=b
 return (w*X+x*W+y*Z-z*Y,w*Y-x*Z+y*W+z*X,w*Z+x*Y-y*X+z*W,w*W-x*X-y*Y-z*Z)
def quat(axis,angle):
 a=math.radians(angle)/2;s=math.sin(a);return tuple(s if i==axis else math.cos(a) if i==3 else 0 for i in range(4))
def rot(q,v):
 o=qmul(qmul(q,(*v,0)),(-q[0],-q[1],-q[2],q[3]));return o[:3]
def add(a,b):return tuple(x+y for x,y in zip(a,b))
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def scale(v,k):return tuple(x*k for x in v)
def points(c):
 x,y,z=c['min'];a,b,d=c['size'];return [(x,y,z+d),(x+a,y,z+d),(x+a,y+b,z+d),(x,y+b,z+d),(x,y,z),(x+a,y,z),(x+a,y+b,z),(x,y+b,z)]

class Asset:
 def __init__(self,name,label,carrier):self.name=name;self.label=label;self.carrier=carrier;self.bones={'root':{'parent':None,'pivot':(0,0,0)}};self.cubes=[];self.clips={}
 def bone(self,name,pivot,parent='root'):self.bones[name]={'parent':parent,'pivot':tuple(pivot)}
 def box(self,bone,center,size,mat='bone'):
  assert bone in self.bones and mat in PALETTE and min(size)>0
  self.cubes.append({'bone':bone,'min':tuple(center[i]-size[i]/2 for i in range(3)),'size':tuple(size),'material':mat})
 def bar(self,bone,a,b,thick=.65,mat='bone'):
  #Stepped original Minecraft anatomy, axis-aligned tiny segments; no imported geometry.
  length=math.dist(a,b);n=max(1,math.ceil(length/.8))
  for i in range(n):
   t=(i+.5)/n;self.box(bone,tuple(a[j]+(b[j]-a[j])*t for j in range(3)),(max(thick,abs(b[0]-a[0])/n+.04),max(thick,abs(b[1]-a[1])/n+.04),max(thick,abs(b[2]-a[2])/n+.04)),mat)
 def ring(self,bone,xr,yr,z,y=8,thick=.65):
  self.bar(bone,(-xr,y+yr,z),(xr,y+yr,z),thick,'bone_light');self.bar(bone,(-xr,y+yr,z),(-xr,y-yr,z),thick);self.bar(bone,(xr,y+yr,z),(xr,y-yr,z),thick);self.bar(bone,(-xr,y-yr,z),(xr,y-yr,z),thick,'bone_shadow')
 def pose(self,clip,t):
  out={}
  for name,b in self.bones.items():
   axis,amplitude,phase=self.clips.get(clip,{}).get(name,(1,0,0));q=quat(axis,amplitude*math.sin(t*math.tau+phase))
   p=b['pivot'];parent=b['parent']
   if parent:
    pq,pp=out[parent];out[name]=(qmul(pq,q),add(pp,rot(pq,sub(p,self.bones[parent]['pivot']))))
   else:out[name]=(q,p)
  return out
 def transformed(self,clip,t):
  pose=self.pose(clip,t);out=[]
  for c in self.cubes:
   q,p=pose[c['bone']];pivot=self.bones[c['bone']]['pivot'];out.append(([add(p,rot(q,sub(v,pivot))) for v in points(c)],c['material']))
  return out

def bird(owl=False):
 a=Asset('ossuary_owl' if owl else 'ossuary_parrot','Ossuary Owl' if owl else 'Ossuary Parrot','minecraft:parrot')
 a.bone('chest',(0,9,0));a.bone('head',(0,13,2),'chest');a.bone('jaw',(0,13,5),'head');a.bone('tail',(0,8,-3),'chest')
 for side,sgn in [('left',-1),('right',1)]:
  a.bone(side+'_wing',(sgn*2.3,11,0),'chest');a.bone(side+'_wrist',(sgn*8.5,10,-1),side+'_wing');a.bone(side+'_foot',(sgn*1.8,4,0),'chest')
 for z in [-2,-.5,1,2.5]:a.ring('chest',2.5,3.2,z,y=9,thick=.72)
 a.bar('chest',(0,6,-3),(0,13,2),.9,'gold');a.bar('chest',(-2,11,1),(2,11,1),.85)
 for s in [-1,1]:
  a.bar('chest',(0,12,1),(s*2.5,11,0),.7,'teal');a.box('chest',(s*2.8,10.7,-1),(1,1,1),'gold')
 if owl:
  #Forward-facing eye apertures, hooked beak; no fake mammal teeth.
  for s in [-1,1]:
   cx=s*2.35
   for p,q in [((cx-1.85,17.4,5),(cx+1.85,17.4,5)),((cx-1.85,13.6,5),(cx+1.85,13.6,5)),((cx-1.85,13.6,5),(cx-1.85,17.4,5)),((cx+1.85,13.6,5),(cx+1.85,17.4,5))]:a.bar('head',p,q,.75,'bone_light')
   a.box('head',(cx,15.5,5.1),(.85,1.05,.5),'eye');a.bar('head',(cx,18,4),(s*4.8,19,2.5),.7,'gold')
  a.box('head',(0,17.8,2.8),(7.5,1.1,4.4),'bone');a.box('head',(0,14.4,5.8),(1.1,2,1.8),'gold');a.box('jaw',(0,13.4,5.5),(1.1,.6,1.4),'bone_shadow')
 else:
  a.box('head',(0,17,2.7),(5.6,1.2,4.7),'bone_light');a.box('head',(0,14.1,1.5),(4.8,1,3.5),'bone_shadow')
  for s in [-1,1]:
   for y,z in [(16.7,1.2),(16.7,4.1),(14.4,1.2),(14.4,4.1)]:a.box('head',(s*2.55,y,z),(.7,.8,1.2),'bone')
   a.box('head',(s*2.9,15.6,2.9),(.5,.9,.8),'eye')
  a.box('head',(0,16.2,5.3),(3.6,2,2.8),'bone_light');a.box('head',(0,15.1,6.7),(2,2,1.4),'gold');a.box('head',(0,14,6.6),(1.1,1.4,1),'bone_shadow');a.box('jaw',(0,13.6,5),(2.4,.7,3.2),'bone')
 for side,s in [('left',-1),('right',1)]:
  a.bar(side+'_wing',(s*2.3,11,0),(s*8.5,10,-1),.9);a.bar(side+'_wrist',(s*8.5,10,-1),(s*14,10,-3),.7,'bone_light')
  for j in range(4):a.bar(side+'_wrist',(s*11,10,-2.2),(s*(16+j*.65),9.6,-(3+j*1.1)),.6,'bone' if j%2 else 'bone_light')
  a.box(side+'_wing',(s*5,10.8,-.3),(2,.5,1),'violet' if s<0 else 'teal')
  a.bar(side+'_foot',(s*1.8,6,0),(s*1.8,1.7,.5),.65)
  for dx,z in [(-.8,2),(.8,2),(-.65,-1.2),(.65,-1.2)]:a.bar(side+'_foot',(s*1.8,1.7,.5),(s*1.8+dx,.9,z),.5,'bone_shadow')
 for i in [-1,0,1]:a.bar('tail',(i*.7,8,-3),(i*1.2,6 if owl else 2,-(6 if owl else 10)),.7,'bone')
 a.clips={'idle':{'head':(1,12,.4),'jaw':(0,4,0),'tail':(1,4,1)},'swim':{}}
 a.clips['flight']={side+'_wing':(2,s*26,0) for side,s in [('left',-1),('right',1)]}
 a.clips['flight'].update({side+'_wrist':(2,s*17,.65) for side,s in [('left',-1),('right',1)]});a.clips['flight']['jaw']=(0,7,.2);a.clips['flight']['tail']=(0,7,.6)
 return a

def fish():
 a=Asset('ossuary_fish','Ossuary Fish','minecraft:cod');a.bone('body',(0,6,0));a.bone('head',(0,6,5),'body');a.bone('jaw',(0,5,6),'head');a.bone('tail',(0,6,-5),'body');a.bone('tail_fin',(0,6,-9),'tail');a.bone('left_fin',(-2.8,5.5,1),'body');a.bone('right_fin',(2.8,5.5,1),'body')
 for z in [-4,-2,0,2,4]:a.ring('body',2.5,2.6,z,y=6,thick=.65)
 a.bar('body',(0,6,5),(0,6,-6),1,'gold')
 for z in [-3,-1,1,3]:a.bar('body',(0,8.5,z),(0,11,z-.8),.6,'teal')
 a.box('head',(0,8.5,6.4),(5.4,.8,3.3),'bone_light');a.box('head',(0,6,7.8),(2.7,.7,1),'bone');a.box('jaw',(0,4.7,7),(4,.65,3),'bone_shadow')
 for s in [-1,1]:
  a.bar('head',(s*2.3,8,5),(s*2.3,5,7),.7);a.box('head',(s*2.6,7,6.4),(.6,.9,.9),'eye');a.bar('left_fin' if s<0 else 'right_fin',(s*2.4,5.5,1),(s*5.4,4.7,-1),.65,'violet' if s<0 else 'teal')
 for z in [-6,-7.5,-9]:a.box('tail',(0,6,z),(.85,.9,1.1),'bone')
 for dy in [-3,-1.5,0,1.5,3]:a.bar('tail_fin',(0,6,-9),(0,6+dy,-12),.55,'bone_light')
 a.clips={'idle':{'jaw':(0,6,0)},'swim':{'body':(1,3,0),'tail':(1,18,.7),'tail_fin':(1,18,1.2),'jaw':(0,7,.4),'left_fin':(2,12,0),'right_fin':(2,-12,0)}};return a

def marine(skeleton=False,dolphin=False):
 name='jewel_dolphin' if dolphin else 'ossuary_shark' if skeleton else 'reef_shark';a=Asset(name,name.replace('_',' ').title(),'minecraft:dolphin' if dolphin else 'minecraft:cod')
 a.bone('body',(0,7,0));a.bone('head',(0,7,10),'body');a.bone('jaw',(0,4.5,12),'head');a.bone('tail_base',(0,7,-8),'body');a.bone('tail_tip',(0,7,-16),'tail_base');a.bone('tail_fin',(0,7,-21),'tail_tip');a.bone('left_fin',(-4,6,5),'body');a.bone('right_fin',(4,6,5),'body');a.bone('dorsal',(0,10,-1),'body')
 if skeleton:
  for z in range(-10,12,3):a.ring('body',4 if z>-7 else 3,3.3,z,y=7,thick=.85)
  a.bar('body',(0,7,12),(0,7,-10),1.15,'gold')
  a.box('head',(0,10.2,13.5),(6.5,1.1,6),'bone_light');a.box('head',(0,8.7,17),(3.4,1.2,3.7),'bone');a.box('jaw',(0,3.7,14),(6.8,.9,7.5),'bone_shadow')
  for s in [-1,1]:
   a.bar('head',(s*3.5,10,11),(s*3.5,5,15),.9,'bone');a.bar('head',(s*3.5,5,15),(s*1.5,6,18),.8,'bone_light');a.box('head',(s*3.9,8.7,13),(.7,1.2,1.4),'eye')
  for z in range(-11,-17,-2):a.box('tail_base',(0,7,z),(1,1.1,1.5),'bone')
  for z in range(-17,-22,-2):a.box('tail_tip',(0,7,z),(.8,.9,1.5),'bone')
 else:
  #Stepped tapered countershading, no inflated ellipsoid or oversized cheek spheres.
  for z,w,h in [(-12,3.3,3.2),(-8,5.4,4.7),(-4,7.2,6.1),(0,8.5,7.2),(4,9,7.5),(8,7.6,6.5),(12,5.8,4.8)]:
   bone='tail_base' if z<-8 else 'body';a.box(bone,(0,8.5,z),(w,h*.65,4.1),'skin' if dolphin else 'dark_skin');a.box(bone,(0,8.5-h*.43,z),(w*.9,h*.35,4.1),'belly')
  a.box('head',(0,8,14.8),(4.6,3.1,4.2),'skin');a.box('head',(0,7.2,17 if dolphin else 16.7),(3 if dolphin else 4,1.7,4.8 if dolphin else 2.8),'skin' if dolphin else 'dark_skin');a.box('jaw',(0,5.3,15.5),(3.8,.9,5),'belly')
  for s in [-1,1]:a.box('head',(s*2.8,8.1,12.8),(.55,.9,1.1),'eye')
  for z,w in [(-15,2.2),(-18,1.5),(-21,.9)]:a.box('tail_tip',(0,7,z),(w,2.1,3.4),'skin')
 for s in [-1,1]:
  b='left_fin' if s<0 else 'right_fin'
  if skeleton:
   for j in range(3):a.bar(b,(s*3.5,6,5-j),(s*(10-j),4.4,1-j),.7,'bone_light')
  else:
   for j in range(5):a.box(b,(s*(4+j*.95),5.9-j*.24,4-j*.7),(1.5,.65,4.5-j*.5),'skin')
  a.bar(b,(s*4,6.5,4.8),(s*8.5,5.5,1.2),.35,'gold')
  if dolphin:
   for j,mat in enumerate(['red','gold','green','teal','blue','violet']):a.box(b,(s*(4.3+j*.65),6.25-j*.18,3.4-j*.4),(.42,.28,1.7),mat)
 #Dorsal fin: tapered stair triangle with negative space in ossuary version.
 for j in range(6):
  if not skeleton or j in (0,5):a.box('dorsal',(0,10.6+j*.65,-1-j*.45),(.65 if skeleton else .9,1,5-j*.65),'bone' if skeleton else 'skin')
 if skeleton:a.bar('dorsal',(0,10.5,1.2),(0,14.3,-3.1),.7,'gold')
 if dolphin:
  for s in [-1,1]:
   for j in range(6):a.box('tail_fin',(s*(.7+j*.8),7,-21.5-j*.35),(1.2,.7,3.8-j*.35),'skin')
   a.box('tail_fin',(s*3.7,7.45,-23.1),(2,.25,.6),'violet' if s<0 else 'teal')
  a.box('body',(0,11.1,8.8),(1.2,.3,.75),'black') #blowhole
 else:
  for j in range(7):
   a.box('tail_fin',(0,7+j*.9,-21.4-j*.35),(.65 if skeleton else .9,1.2,2.6-j*.18),'bone_light' if skeleton else 'dark_skin')
  for j in range(4):a.box('tail_fin',(0,6-j*.8,-21.6-j*.35),(.65 if skeleton else .9,1,2.4-j*.2),'bone' if skeleton else 'skin')
  #Few readable triangular stepped teeth, not an endless noise field.
  for s in [-1,1]:
   for z in [12.5,14.5,16.5]:
    a.box('jaw',(s*2.1,4.6,z),(.55,1.1,.7),'bone_light')
    a.box('head',(s*2.1,6.2,z),(.5,.7,.65),'bone_light')
  if not skeleton:
   for s in [-1,1]:
    for z in [6,7,8,9,10]:a.box('body',(s*3.85,7.3,z),(.22,2.4,.22),'black')
 a.clips={'idle':{'jaw':(0,3,.1),'head':(1,2,0)},'swim':{'body':(0 if dolphin else 1,2,0),'tail_base':(0 if dolphin else 1,9,0),'tail_tip':(0 if dolphin else 1,16,-.6),'tail_fin':(0 if dolphin else 1,17,-1.1),'left_fin':(2,5,0),'right_fin':(2,-5,0),'jaw':(0,4,.2)}}
 if dolphin:a.clips['breach']={'root':(0,45,-math.pi/2),'tail_base':(0,15,.2),'tail_tip':(0,22,-.4),'tail_fin':(0,18,-.8),'left_fin':(2,18,0),'right_fin':(2,-18,0)}
 return a

def all_assets():
 assets=[bird(False),bird(True),fish(),marine(),marine(True),marine(dolphin=True)]
 for a in assets:
  #Independent eye bones allow true Java display brightness without brightening skull/body.
  for side,s in [('left',-1),('right',1)]:
   eyes=[c for c in a.cubes if c['material']=='eye' and ('left' if c['min'][0]<0 else 'right')==side]
   if not eyes:continue
   p=tuple(eyes[0]['min'][k]+eyes[0]['size'][k]/2 for k in range(3));bn=side+'_eye';a.bone(bn,p,'head')
   for c in eyes:c['bone']=bn
 return assets

def atlas(path):
 im=Image.new('RGBA',(128,128),(0,0,0,0));d=ImageDraw.Draw(im)
 for i,key in enumerate(COLORS):
  x=(i%8)*16;y=(i//8)*16;c=PALETTE[key]
  for u in range(16):
   for v in range(16):
    k=((u*13+v*7+i*11)%9)-4;im.putpixel((x+u,y+v),tuple(max(0,min(255,b+k)) for b in c)+(255,))
 im.save(path)
def uv(mat):i=COLORS.index(mat);return [(i%8)*2,(i//8)*2,(i%8)*2+2,(i//8)*2+2]
def save_json(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
def primitive(c,pivot):
 vs=[];norm=[];ix=[];uvs=[];v=points(c)
 for normal,ids in FACES:
  k=len(vs);vs.extend([scale(sub(v[j],pivot),1/16) for j in ids]);norm.extend([normal]*4);ix.extend([k,k+1,k+2,k,k+2,k+3]);uvs.extend([(0,0),(1,0),(1,1),(0,1)])
 return vs,norm,ix

def glb(a,path):
 blob=bytearray();views=[];access=[]
 def buf(data,kind,count,ctype=5126,mins=None,maxs=None):
  while len(blob)%4:blob.append(0)
  offset=len(blob);blob.extend(data);vi=len(views);views.append({'buffer':0,'byteOffset':offset,'byteLength':len(data)});ac={'bufferView':vi,'componentType':ctype,'count':count,'type':kind}
  if mins is not None:ac['min']=mins;ac['max']=maxs
  access.append(ac);return len(access)-1
 def floats(values,kind):
  rows=list(values);flat=[x for row in rows for x in (row if isinstance(row,(tuple,list)) else [row])];return buf(struct.pack('<'+'f'*len(flat),*flat),kind,len(rows))
 nodes=[];meshes=[];names=list(a.bones)
 for name,b in a.bones.items():
  tr=b['pivot'] if b['parent'] is None else sub(b['pivot'],a.bones[b['parent']]['pivot'])
  nodes.append({'name':name,'translation':scale(tr,1/16),'children':[j for j,n in enumerate(names) if a.bones[n]['parent']==name]})
  ps=[]
  for c in a.cubes:
   if c['bone']!=name:continue
   vs,nr,ix=primitive(c,b['pivot']);pmin=[min(v[k] for v in vs) for k in range(3)];pmax=[max(v[k] for v in vs) for k in range(3)];pa=buf(struct.pack('<'+'f'*(len(vs)*3),*(x for v in vs for x in v)),'VEC3',len(vs),mins=pmin,maxs=pmax);na=floats(nr,'VEC3');ii=buf(struct.pack('<'+'H'*len(ix),*ix),'SCALAR',len(ix),5123);ps.append({'attributes':{'POSITION':pa,'NORMAL':na},'indices':ii,'material':COLORS.index(c['material'])})
  if ps:nodes[-1]['mesh']=len(meshes);meshes.append({'name':name,'primitives':ps})
 animations=[]
 for clip in a.clips:
  channels=[];samplers=[];times=[i/16*1.6 for i in range(17)];ti=floats(times,'SCALAR');access[ti]['min']=[0];access[ti]['max']=[1.6]
  for name,(axis,amp,phase) in a.clips[clip].items():
   qs=[quat(axis,amp*math.sin(i/16*math.tau+phase)) for i in range(17)];ri=floats(qs,'VEC4');samplers.append({'input':ti,'output':ri,'interpolation':'LINEAR'});channels.append({'sampler':len(samplers)-1,'target':{'node':names.index(name),'path':'rotation'}})
  if channels:animations.append({'name':clip,'channels':channels,'samplers':samplers})
 mats=[{'name':key,'pbrMetallicRoughness':{'baseColorFactor':[v/255 for v in PALETTE[key]]+[1],'metallicFactor':.65 if key in ['gold','teal','violet','red','blue','green'] else 0,'roughnessFactor':.35 if key=='gold' else .76},**({'emissiveFactor':[.15,.4,.35]} if key=='eye' else {})} for key in COLORS]
 doc={'asset':{'version':'2.0','generator':'NorthStar original pirate-fauna v01'},'scene':0,'scenes':[{'nodes':[0]}],'nodes':nodes,'meshes':meshes,'materials':mats,'animations':animations,'buffers':[{'byteLength':len(blob)}],'bufferViews':views,'accessors':access}
 js=json.dumps(doc,separators=(',',':')).encode();js+=b' '*((-len(js))%4);blob+=b'\0'*((-len(blob))%4);path.write_bytes(struct.pack('<4sII',b'glTF',2,12+8+len(js)+8+len(blob))+struct.pack('<I4s',len(js),b'JSON')+js+struct.pack('<I4s',len(blob),b'BIN\0')+blob)

def render(a,clip,t,size=600,yaw=35):
 #True software-projected original3D geometry and articulated pose, not imagegen or native footage.
 cubes=a.transformed(clip,t);allp=[p for v,_ in cubes for p in v];center=tuple((min(p[k] for p in allp)+max(p[k] for p in allp))/2 for k in range(3));rad=math.radians(yaw);el=math.radians(18)
 def camera(p):
  x,y,z=sub(p,center);xx=x*math.cos(rad)-z*math.sin(rad);zz=x*math.sin(rad)+z*math.cos(rad);return (xx,-y*math.cos(el)+zz*math.sin(el),zz*math.cos(el)+y*math.sin(el))
 cam=[camera(p) for p in allp];span=max(max(p[0] for p in cam)-min(p[0] for p in cam),max(p[1] for p in cam)-min(p[1] for p in cam));unit=(size-80)/span
 image=Image.new('RGB',(size,size),(12,19,29));draw=ImageDraw.Draw(image);polys=[]
 for verts,mat in cubes:
  cv=[camera(p) for p in verts]
  for ni,(normal,ids) in enumerate(FACES):
   points2=[(size/2+cv[j][0]*unit,size/2+cv[j][1]*unit) for j in ids];depth=sum(cv[j][2] for j in ids)/4;shade=[1,.6,.83,.7,1.12,.5][ni];c=PALETTE[mat];color=tuple(min(255,int(v*shade)) for v in c);polys.append((depth,points2,color))
 for _,pts,col in sorted(polys,key=lambda row:row[0]):draw.polygon(pts,fill=col)
 return image

def export_asset(a,dest):
 home=dest/a.name;home.mkdir();(home/'MODEL').mkdir();glb(a,home/'MODEL'/f'{a.name}.glb');atlas(home/'MODEL'/'palette.png')
 save_json(home/'MODEL'/'original_rig.json',{'name':a.name,'bones':a.bones,'cubes':a.cubes,'clips':a.clips,'units':'Minecraft pixels,16perblock,+Zforward,+Yup','provisional_namespaced_id':NS+':'+a.name,'numeric_id_allocated':False})
 jp=home/'java_resourcepack';bp=home/'bedrock_resourcepack';dp=home/'java_datapack_src';bp.mkdir();jp.mkdir();dp.mkdir()
 save_json(jp/'pack.mcmeta',{'pack':{'description':a.label+' — original source candidate','min_format':[97,1],'max_format':[97,1]}})
 tex=jp/f'assets/{NS}/textures/entity';tex.mkdir(parents=True);(tex/f'{a.name}.png').write_bytes((home/'MODEL'/'palette.png').read_bytes())
 bone_geometry=[];assembly=[]
 for bn,b in a.bones.items():
  elements=[]
  for c in a.cubes:
   if c['bone']!=bn:continue
   lo=add(sub(c['min'],b['pivot']),(8,8,8));hi=add(lo,c['size']);elements.append({'from':lo,'to':hi,'faces':{f:{'uv':uv(c['material']),'texture':'#0'} for f in ['north','south','east','west','up','down']}})
  if elements:
   save_json(jp/f'assets/{NS}/models/item/{a.name}/{bn}.json',{'textures':{'0':NS+':entity/'+a.name},'elements':elements});save_json(jp/f'assets/{NS}/items/{a.name}/{bn}.json',{'model':{'type':'minecraft:model','model':NS+':item/'+a.name+'/'+bn}});assembly.append({'bone':bn,'item_model':NS+':'+a.name+'/'+bn,'pivot_pixels':b['pivot']})
 save_json(home/'MODEL'/'java_bone_assembly.json',{'parts':assembly,'presentation':'one item_display passenger per nonempty bone; no numeric CMD; renderer wiring unproved'})
 #Bedrock full bone geometry plus separate emissive-eye geometry.
 geos=[]
 for layer in ['body','eyes']:
  bones=[]
  for bn,b in a.bones.items():
   pv=b['pivot'];bone={'name':bn,'pivot':[pv[0],pv[1],-pv[2]]}
   if b['parent']:bone['parent']=b['parent']
   cub=[]
   for c in a.cubes:
    if c['bone']!=bn or (c['material']=='eye')!=(layer=='eyes'):continue
    x,y,z=c['min'];sx,sy,sz=c['size'];u=uv(c['material']);cub.append({'origin':[x,y,-z-sz],'size':[sx,sy,sz],'uv':{f:{'uv':[u[0]*8,u[1]*8],'uv_size':[16,16]} for f in ['north','south','east','west','up','down']}})
   if cub:bone['cubes']=cub
   bones.append(bone)
  ident='geometry.'+NS+'.'+a.name+'.'+layer;save_json(bp/f'models/entity/{a.name}_{layer}.geo.json',{'format_version':'1.12.0','minecraft:geometry':[{'description':{'identifier':ident,'texture_width':128,'texture_height':128,'visible_bounds_width':7,'visible_bounds_height':5,'visible_bounds_offset':[0,.7,0]},'bones':bones}]})
 desc={'identifier':NS+':'+a.name,'materials':{'body':'entity_alphatest','eyes':'entity_emissive_alpha'},'textures':{'default':'textures/entity/'+a.name},'geometry':{'body':'geometry.'+NS+'.'+a.name+'.body','eyes':'geometry.'+NS+'.'+a.name+'.eyes'},'render_controllers':['controller.render.'+NS+'.'+a.name+'.'+l for l in ['body','eyes']],'animations':{},'scripts':{'animate':[]}}
 anims={}
 for clip,channels in a.clips.items():
  if not channels:continue
  animid='animation.'+NS+'.'+a.name+'.'+clip;bones={}
  for bn,(axis,amp,phase) in channels.items():
   values={}
   for i in range(17):
    v=[0,0,0];v[axis]=round(amp*math.sin(i/16*math.tau+phase)*(-1 if axis in [0,1] else 1),5);values[str(round(i/16*1.6,3))]=v
   bones[bn]={'rotation':values}
  anims[animid]={'loop':clip!='breach','animation_length':1.6,'bones':bones};desc['animations'][clip]=animid
 default='flight' if 'flight' in a.clips else 'swim';desc['scripts']['animate']=[default]
 save_json(bp/f'animations/{a.name}.animation.json',{'format_version':'1.8.0','animations':anims});save_json(bp/f'entity/{a.name}.entity.json',{'format_version':'1.10.0','minecraft:client_entity':{'description':desc}})
 save_json(bp/f'render_controllers/{a.name}.render_controllers.json',{'format_version':'1.8.0','render_controllers':{'controller.render.'+NS+'.'+a.name+'.'+l:{'geometry':'Geometry.'+l,'materials':[{'*':'Material.'+l}],'textures':['Texture.default']} for l in ['body','eyes']}})
 (bp/'textures/entity').mkdir(parents=True);(bp/f'textures/entity/{a.name}.png').write_bytes((home/'MODEL'/'palette.png').read_bytes());save_json(bp/'manifest.json',{'format_version':2,'header':{'name':a.label+' source RP','description':'Original unproved client geometry; Geyser registration not included','uuid':str(uuid.uuid5(uuid.NAMESPACE_URL,NS+':'+a.name)),'version':[0,1,0],'min_engine_version':[1,21,0]},'modules':[{'type':'resources','uuid':str(uuid.uuid5(uuid.NAMESPACE_URL,NS+':'+a.name+':resources')),'version':[0,1,0]}]})
 #Actual per-bone Java animation function source: invoked as the owner's exact live carrier.
 frame_count=16
 for clip in a.clips:
  if not a.clips[clip]:continue
  for i in range(frame_count):
   pose=a.pose(clip,i/frame_count);lines=['data modify storage nsp_pirate_fauna:pose rotation set from entity @s Rotation','execute on passengers if entity @s[tag=nsp_pirate_fauna.visual] run data modify entity @s Rotation set from storage nsp_pirate_fauna:pose rotation']
   for part in assembly:
    bn=part['bone'];q,p=pose[bn];tr=scale(p,1/16);state={'translation':tr,'left_rotation':q,'right_rotation':[0,0,0,1],'scale':[1,1,1]};payload=json.dumps({'start_interpolation':0,'interpolation_duration':2,'transformation':state},separators=(',',':'));lines.append('execute on passengers if entity @s[tag='+NS+'.bone.'+bn+'] run data merge entity @s '+payload)
   path=dp/f'data/{NS}/function/pose/{a.name}/{clip}/{i:02d}.mcfunction';path.parent.mkdir(parents=True,exist_ok=True);path.write_text('\n'.join(lines)+'\n',encoding='utf-8')
 #Assembly is explicitly opt-in source; independent actor registration/AI/movement belongs to Root.
 passengers=[]
 for part in assembly:
  bn=part['bone'];passengers.append({'id':'minecraft:item_display',**({'brightness':{'block':12,'sky':15}} if bn.endswith('_eye') else {}),'Tags':[NS+'.visual',NS+'.bone.'+bn],'item':{'id':'minecraft:paper','count':1,'components':{'minecraft:item_model':part['item_model']}},'item_display':'none','teleport_duration':2,'interpolation_duration':2})
 command='summon '+a.carrier+' ~ ~ ~ '+json.dumps({'Tags':[NS+'.actor',NS+'.'+a.name],'NoAI':True,'Silent':True,'Invulnerable':True,'PersistenceRequired':True,'Passengers':passengers},separators=(',',':'))
 spawn=dp/f'data/{NS}/function/opt_in_assembly/{a.name}.mcfunction';spawn.parent.mkdir(parents=True,exist_ok=True);spawn.write_text('#UNINSTALLED SOURCE: owner must add bounded site/cap/identity and appropriate safe water/air conditions before adoption.\nexecute unless data storage nsp_pirate_fauna:config {source_adopted:1b,site_guard_bound:1b,behavior_owner_bound:1b} run return 0\n'+command+'\n',encoding='utf-8')
 if a.name=='jewel_dolphin':
  trail=dp/f'data/{NS}/function/trail/dolphin.mcfunction';trail.parent.mkdir(parents=True,exist_ok=True)
  setup=dp/f'data/{NS}/function/setup_trail.mcfunction';setup.write_text('scoreboard objectives add npf_trail dummy\n',encoding='utf-8')
  lines=['#Explicit owner invocation only. Mark actual moving actor; never a projectile.','execute unless entity @s[tag=nsp_pirate_fauna.jewel_dolphin,tag=nsp_pirate_fauna.active_motion] run return 0','execute unless data storage nsp_pirate_fauna:config {trail_enabled:1b} run return 0','scoreboard players add @s npf_trail 1','execute unless score @s npf_trail matches 8.. run return 0','scoreboard players set @s npf_trail 0']
  for j,key in enumerate(['red','gold','green','teal','blue','violet']):
   col=','.join(str(round(v/255,4)) for v in PALETTE[key]);lines.append('particle minecraft:dust{color:['+col+'],scale:0.45} ^'+str(round((j-2.5)*.09,3))+' ^0.05 ^-1.3 0.01 0.01 0.01 0 1 normal @a[distance=..24]')
  trail.write_text('\n'.join(lines)+'\n',encoding='utf-8');save_json(home/'MODEL'/'rainbow_trail_profile.json',{'colors':[PALETTE[k] for k in ['red','gold','green','teal','blue','violet']],'maximum_particles_per_invocation':6,'cooldown_owner_calls':8,'invocation_frequency_contract':'owner calls at most once per actual server tick','enabled_by_default':False,'breach_behavior':'Root owner; no world trajectory in this asset'})
 save_json(dp/'pack.mcmeta',{'pack':{'description':a.label+' explicit uninstalled animation source only','min_format':[121,0],'max_format':[121,0]}})
 previews=home/'previews';previews.mkdir();views=[]
 for yaw in [30,150,270,0]:views.append(render(a,default,.15,600,yaw))
 sheet=Image.new('RGB',(1200,1200),(12,19,29))
 for i,im in enumerate(views):sheet.paste(im,((i%2)*600,(i//2)*600))
 sheet.save(previews/'four_views.png')
 frames=[render(a,default,i/16,500,35) for i in range(16)];frames[0].save(previews/'articulated_software_preview.gif',save_all=True,append_images=frames[1:],duration=100,loop=0)
 if 'breach' in a.clips:
  ims=[render(a,'breach',i/16,500,35) for i in range(16)];ims[0].save(previews/'breach_pose_software_preview.gif',save_all=True,append_images=ims[1:],duration=100,loop=0)
 rows=[]
 for clip in a.clips:
  for i in range(16):
   v=[p for pts,_ in a.transformed(clip,i/16) for p in pts];rows.append({'clip':clip,'frame':i,'min':[min(p[k] for p in v)/16 for k in range(3)],'max':[max(p[k] for p in v)/16 for k in range(3)]})
 save_json(home/'MODEL'/'POSE_BOUNDS_ACTUAL.json',rows)
 return {'id':NS+':'+a.name,'cubes':len(a.cubes),'bones':len(a.bones),'java_displays':len(assembly),'triangles':len(a.cubes)*12,'clips':[c for c in a.clips if a.clips[c]],'native_verified':False,'owner_visual_approved':False}

def validate_actual_files(out):
 checks=[]
 for p in out.rglob('*.glb'):
  b=p.read_bytes();magic,version,total=struct.unpack_from('<4sII',b);assert (magic,version,total)==(b'glTF',2,len(b)),str(p)
  jl,jt=struct.unpack_from('<I4s',b,12);assert jt==b'JSON';doc=json.loads(b[20:20+jl]);bl,bt=struct.unpack_from('<I4s',b,20+jl);assert bt==b'BIN\0';binary=b[28+jl:28+jl+bl];assert len(binary)==bl
  assert len(doc['nodes'])<64 and doc['animations']
  sizes={5126:4,5123:2};components={'SCALAR':1,'VEC3':3,'VEC4':4}
  for acc in doc['accessors']:
   view=doc['bufferViews'][acc['bufferView']];need=acc['count']*sizes[acc['componentType']]*components[acc['type']];assert need<=view['byteLength'];assert view['byteOffset']+view['byteLength']<=len(binary)
  for anim in doc['animations']:
   for ch in anim['channels']:assert ch['target']['node']<len(doc['nodes']) and ch['sampler']<len(anim['samplers'])
  checks.append({'file':str(p.relative_to(out)),'actual_glb_structure':'valid','nodes':len(doc['nodes']),'animation_clips':[a['name'] for a in doc['animations']]})
 for p in out.rglob('*.geo.json'):
  d=json.loads(p.read_text());g=d['minecraft:geometry'][0];names=[b['name'] for b in g['bones']];assert len(names)==len(set(names)) and len(names)<256
  for bone in g['bones']:
   assert bone.get('parent','root') in names
   for c in bone.get('cubes',[]):assert min(c['size'])>0
 for p in out.rglob('*.json'):
  d=json.loads(p.read_text())
  if '/java_resourcepack/' in p.as_posix() and '/models/' in p.as_posix():
   for el in d.get('elements',[]):assert all(-16<=v<=32 for v in el['from']+el['to']),str(p)
 for p in out.rglob('*.png'):
  with Image.open(p) as im:im.load();assert im.width>0 and im.height>0
 return checks

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',required=True,type=Path);a=ap.parse_args();out=a.output.resolve()
 if ROOT not in out.parents or out.exists():raise ValueError('Fresh output only inside owned source home')
 if os.name=='nt':ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(),0x40)
 out.mkdir(parents=True);rows=[]
 for asset in all_assets():rows.append(export_asset(asset,out))
 checks=validate_actual_files(out)
 save_json(out/'STATIC_FORMAT_VALIDATION_ACTUAL.json',{'actual_checks':checks,'native_verified':False})
 hashes={str(p.relative_to(out)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file()}
 save_json(out/'GENERATION_ACTUAL.json',{'assets':rows,'files':hashes,'provider_spend':0,'new_numeric_ids':0,'world_writes':0,'native_run':False,'preview_kind':'actual articulated3D software projection; not in-game evidence','source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()});print(json.dumps({'assets':rows,'files':len(hashes),'output':str(out)}))
if __name__=='__main__':main()
