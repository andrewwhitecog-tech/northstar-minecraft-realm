"""Original articulated pirate fauna assets; no provider, registry, native or live writes."""
from __future__ import annotations
import argparse,ctypes,hashlib,json,math,os,struct,sys,uuid,zipfile
from pathlib import Path
from PIL import Image,ImageDraw,ImageEnhance
import io
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



# Original v04 voxel sculpt: one hare boss, no inherited rectangular rabbit body.
PALETTE={'fur_black':(38,41,49),'fur_mid':(51,53,65),'fur_edge':(66,65,77),'fur_belly':(72,67,75),
 'inner_ear':(78,22,50),'inner_ear_edge':(104,36,73),'skin_nose':(78,36,48),'ivory':(218,204,173),
 'gold_old':(187,137,50),'gold_light':(238,196,101),'eye':(38,231,224),'eye_purple':(218,64,242),
 'cyan':(26,190,213),'magenta':(191,38,175),'emerald':(30,191,139),'violet':(101,49,183),
 'gem_dark':(28,33,68),'crack':(16,17,27),'whisker':(147,132,151)}
COLORS=list(PALETTE)

def oval_sculpt(a,bone,center,radius,mat='fur_black',step=3.2):
 """Filled oval slices, merging each X run. Smooth voxel silhouette without a cuboid outer hull."""
 cx,cy,cz=center;rx,ry,rz=radius;ny=math.ceil(2*ry/step);nz=math.ceil(2*rz/step);dy=2*ry/ny;dz=2*rz/nz
 for iy in range(ny):
  y=cy-ry+(iy+.5)*dy;fy=(y-cy)/ry
  for iz in range(nz):
   z=cz-rz+(iz+.5)*dz;fz=(z-cz)/rz;q=1-fy*fy-fz*fz
   if q<=0:continue
   width=2*rx*math.sqrt(q)
   if width<.45:continue
   a.box(bone,(cx,y,z),(width,dy+.025,dz+.025),mat)

def fur_blade(a,bone,p,d,length=4,width=.8,mat='fur_mid'):
 norm=math.sqrt(sum(v*v for v in d));d=tuple(v/norm for v in d)
 for i,f in enumerate([.2,.52,.82]):
  c=tuple(p[k]+d[k]*length*f for k in range(3));a.box(bone,c,(width*(1-i*.2),max(.5,abs(d[1])*length/3+.3),max(.65,abs(d[2])*length/3+.3)),mat)

def leaf_ear(a,bone,sections,inner=False):
 # y, centerx, centerz, width, depth; separate inset inner pinna on the forward face.
 for i in range(len(sections)-1):
  y,x,z,w,d=sections[i];Y,X,Z,W,D=sections[i+1];n=max(1,math.ceil((Y-y)/2))
  for j in range(n):
   f=(j+.5)/n;xx=x+(X-x)*f;zz=z+(Z-z)*f;ww=w+(W-w)*f;dd=d+(D-d)*f;yy=y+(Y-y)*f
   a.box(bone,(xx,yy,zz),(ww,(Y-y)/n+.02,dd),'fur_black')
   if ww>3.2:
    a.box(bone,(xx,yy,zz+dd*.5+.08),(ww*.58,(Y-y)/n+.025,.28),'inner_ear')
    # Outer pale/dark fur edge uses geometry, not rainbow wallpaper.
    a.box(bone,(xx-ww*.46,yy,zz+.2),(.65,(Y-y)/n+.1,dd*.7),'fur_edge')

def seal(a,bone,c,width=5,height=2.6):
 x,y,z=c;p=[(x+math.cos(i*math.tau/16)*width/2,y+math.sin(i*math.tau/16)*height/2,z) for i in range(16)]
 for u,v in zip(p,p[1:]+p[:1]):a.bar(bone,u,v,.27,'gold_light')
 oval_sculpt(a,bone,(x,y,z+.2),(.47,height*.34,.25),'violet',step=.5)
 a.box(bone,(x,y,z+.5),(.18,height*.57,.18),'crack')
 for sg in [-1,1]:a.bar(bone,(x+sg*width*.22,y-height*.4,z),(x+sg*width*.35,y-height*.75,z),.2,'gold_old')

def crystal(a,bone,p,height,width,lean,mat):
 # Chisel-like faceted stepped shard with a tapered point, not a cuboid capped by a gold cube.
 x,y,z=p
 for j in range(6):
  f=j/6;w=width*(1-f*.87)
  a.box(bone,(x+lean*f,y+height*(f+1/12),z-lean*.25*f),(w,height/6+.03,w*.72),mat if j<4 else 'cyan' if mat=='emerald' else mat)
  if j in [1,3]:a.box(bone,(x+lean*f+w*.4,y+height*(f+1/12),z+w*.34),(w*.13,height/6,w*.13),'gem_dark')

def boss_v04():
 a=Asset('mutant_rabbit_boss','The Prism Warren — sculpted hare boss v04','minecraft:rabbit')
 a.bone('hips',(0,46,-20));a.bone('body',(0,56,-2),'hips');a.bone('chest',(0,46,19),'body')
 # Arched rear body and narrower falling forequarters. No broad upright humanoid torso.
 oval_sculpt(a,'hips',(0,46,-20),(20,21,20),step=3.5)
 oval_sculpt(a,'body',(0,56,-2),(17.5,16.5,21),step=3.3)
 oval_sculpt(a,'chest',(0,47,19),(14,18,17),step=3.1)
 oval_sculpt(a,'chest',(0,35,23),(10,12,12),'fur_belly',step=3.2)
 a.bone('head',(0,63,43),'chest');a.bone('muzzle',(0,59,59),'head');a.bone('jaw',(0,55,57),'head')
 # Long narrow rabbit skull; tapered nasal bridge projects beyond the eye plane.
 oval_sculpt(a,'head',(0,65,43),(11.5,12.5,14),step=2.25)
 oval_sculpt(a,'head',(0,57,36),(8,10,10),step=2.6)
 for j,(z,cy,w,h) in enumerate([(51,62,16,12),(54.5,61.5,14,10),(58,61,11.5,8),(61,60.4,9.5,6.5),(64,60,7.5,5)]):
  oval_sculpt(a,'muzzle',(0,cy,z),(w/2,h/2,2.6),'fur_mid' if j>2 else 'fur_black',step=1.8)
 # Paired modest whisker pads. They have curved surfaces and a visible dark central cleft.
 for sg in [-1,1]:
  oval_sculpt(a,'muzzle',(sg*2.7,58.9,64),(3.5,3.2,5),'fur_belly',step=1.2)
  for j in range(8):
   ang=j*math.tau/8;a.box('muzzle',(sg*2.7+math.cos(ang)*2.8,58.9+math.sin(ang)*2.45,67.7),(.42,.42,.3),'fur_edge')
 a.box('muzzle',(-.75,61.1,69.5),(1.6,.8,.65),'skin_nose');a.box('muzzle',(.75,61.1,69.5),(1.6,.8,.65),'skin_nose')
 a.box('muzzle',(0,60.5,69.9),(1.4,.7,.55),'skin_nose');a.box('muzzle',(0,59.5,69.2),(.3,1.8,.3),'crack')
 # A thin divided upper lip, independent jaw and two broad upper incisors.
 for sg in [-1,1]:a.bar('muzzle',(0,58.9,68.7),(sg*2.1,58,68.6),.24,'crack')
 oval_sculpt(a,'jaw',(0,55.5,62),(5.8,2.6,6),'fur_black',step=1.8)
 for sg in [-1,1]:
  a.box('jaw',(sg*1.15,54.2,66.2),(1.85,5.7,1.3),'ivory');a.box('jaw',(sg*1.15,51.4,66.5),(1.45,.6,.9),'ivory')
 # Five delicate whiskers per cheek curve outward; no gray rectangular muzzle plate.
 for sg in [-1,1]:
  for j in range(5):
   p=(sg*4.6,59.5-j*.55,66.6);q=(sg*(12+j*.55),60.8-j*1.05,68-j*.2);r=(sg*(20.4+j*.35),62-j*1.7,67-j*.5)
   a.bar('muzzle',p,q,.13,'whisker');a.bar('muzzle',q,r,.105,'whisker')
 # Strong bright eye apertures under sculpted brows, not tiny points on a flat square face.
 for side,sg,eye in [('left',-1,'eye'),('right',1,'eye_purple')]:
  a.bone(side+'_eye',(sg*7.7,66.1,54),'head')
  oval_sculpt(a,'head',(sg*7.3,66,53.3),(4.1,2.7,1.1),'crack',step=1)
  oval_sculpt(a,side+'_eye',(sg*7.3,66,54.3),(2.85,1.65,.55),eye,step=.7)
  a.box(side+'_eye',(sg*7.3,66,54.9),(.7,2.3,.18),'crack')
  # Brows rake up and outward but leave the animal eyes visible.
  for j in range(7):fur_blade(a,'head',(sg*(3.3+j*.85),69+j*.6,56.7-j*.25),(sg*.9,.45,-.25),3.2,1.05,'fur_edge')
 # Wide lance-shaped ears have a cupped inner surface and an asymmetric articulated fold.
 for side,sg in [('left',-1),('right',1)]:
  a.bone(side+'_ear_base',(sg*8,87,37),'head');a.bone(side+'_ear_tip',(sg*21,114,41),side+'_ear_base')
  leaf_ear(a,side+'_ear_base',[(74,sg*6.5,38,5,4),(82,sg*8.5,37,10,4),(91,sg*12,36,13,3.6),(101,sg*15,37,11,3)])
  sections=[(100,sg*15,37,11,3),(109,sg*22,40,12,2.8),(117,sg*29,45,7,2.4),(120,sg*32,48,1.5,1.3)] if sg<0 else [(100,15,37,11,3),(111,18,37,12,2.8),(124,19,40,7,2.3),(136,15,44,1.2,1.1)]
  leaf_ear(a,side+'_ear_tip',sections)
  for j in range(5):fur_blade(a,side+'_ear_base',(sg*(8+j*.9),81+j*3.6,39),(sg*.8,-.6,.2),2.5,.7,'fur_mid')
 # Folded, massively stronger rear legs and elongated rabbit hindfeet; smaller forward paws.
 for side,sg in [('left',-1),('right',1)]:
  thigh=side+'_thigh';hock=side+'_hock';foot=side+'_foot'
  a.bone(thigh,(sg*18,31,-20),'hips');a.bone(hock,(sg*20,16,-28),thigh);a.bone(foot,(sg*20,6,3),hock)
  oval_sculpt(a,thigh,(sg*18,31,-20),(11,20,16),step=2.8)
  oval_sculpt(a,hock,(sg*20,14,-22),(5.7,11,10),'fur_mid',step=2.5)
  oval_sculpt(a,foot,(sg*20,6,3),(8.5,5,19),step=2.3)
  for j,x in enumerate([-5.2,-1.7,1.7,5.2]):
   oval_sculpt(a,foot,(sg*20+x,5.8,18.3),(1.85,2.4,4),'fur_mid',step=1.3)
   a.box(foot,(sg*20+x,4.6,22.1),(1.35,1.5,2.1),'ivory')
  upper=side+'_foreleg';wrist=side+'_wrist';paw=side+'_forepaw'
  a.bone(upper,(sg*10,42,22),'chest');a.bone(wrist,(sg*11,23,34),upper);a.bone(paw,(sg*11,6,45),wrist)
  oval_sculpt(a,upper,(sg*10.5,34,27),(4.7,12,7),step=2.3)
  oval_sculpt(a,wrist,(sg*11,18,37),(3.2,11,6),'fur_mid',step=2.1)
  oval_sculpt(a,paw,(sg*11,5.3,45),(4.9,4.1,8),'fur_black',step=1.8)
  for x in [-2.7,-.9,.9,2.7]:a.box(paw,(sg*11+x,4,52.4),(1.1,1.3,1.6),'ivory')
 # Overlapping raked fur follows curved haunch/shoulder contours, not flat armor panels.
 for bn,surface,ys,zs in [('hips',19,[34,42,48],[-29,-23,-17,-11]),('body',16,[49,56,61],[-12,-5,2,9]),('chest',13,[39,46,52],[13,20,27])]:
  for sg in [-1,1]:
   for j,y in enumerate(ys):
    for k,z in enumerate(zs):fur_blade(a,bn,(sg*(surface-.4*(j%2)),y,z),(sg*.65,-.7,-1),4.8,.9,'fur_mid' if (j+k)%3 else 'fur_edge')
 for sg in [-1,1]:
  for j in range(9):fur_blade(a,'head',(sg*(8.8+j%2),64-j*.65,46+j*.7),(sg*.85,-.6,-.7),4.3,.8,'fur_mid')
 # Localized mineral ridge on real arched spine; neither a rainbow blanket nor generic stripes.
 for index,(y,z) in enumerate([(63,-22),(71,-2),(63,18)]):
  bn='spine_crystal_'+str(index);a.bone(bn,(0,y,z),'body' if index<2 else 'chest')
  for j in range(5):
   material=['emerald','cyan','violet','magenta','gem_dark'][(j+index)%5]
   crystal(a,bn,((j-2)*2.5,y,z-j*.5),8+(j%3)*2.3,2.9,(j-2)*.7,material)
 # Gold and prism insignia are sculpted, localized jewelry, not large colored body squares.
 seal(a,'head',(0,73,55),6,2.9);seal(a,'chest',(0,43,36),7,3.4)
 for sg in [-1,1]:
  a.bar('chest',(sg*3,45,35.5),(sg*8,51,32),.42,'gold_old')
  a.bar('chest',(sg*8,51,32),(sg*11,47,28),.42,'gold_old')
  a.box(('left' if sg<0 else 'right')+'_wrist',(sg*11,14,42.8),(5.8,1.1,.8),'gold_old')
 a.bone('tail',(0,39,-39),'hips');oval_sculpt(a,'tail',(0,39,-41),(6,6.3,6),'fur_mid',step=2.1)
 a.clips={'idle':{'body':(0,1.2,.2),'chest':(0,1.8,0),'head':(1,3,.6),'muzzle':(0,.6,0),'jaw':(0,2,.1),'left_ear_tip':(2,3,.2),'right_ear_tip':(0,-4,.3)},
 'prowl':{'hips':(0,1.5,0),'left_thigh':(0,9,0),'right_thigh':(0,9,math.pi),'left_hock':(0,7,math.pi),'right_hock':(0,7,0),'left_foreleg':(0,11,math.pi),'right_foreleg':(0,11,0),'left_wrist':(0,7,0),'right_wrist':(0,7,math.pi),'head':(1,3,.1)},
 'snarl_telegraph':{'chest':(0,5,0),'head':(0,-7,.7),'jaw':(0,19,0),'left_ear_base':(0,5,0),'right_ear_tip':(2,8,.4),'spine_crystal_0':(2,-3,0),'spine_crystal_1':(2,3,0)}}
 a.preview_clip='idle';return a

def all_assets():return [boss_v04()]

def texture_atlas():
 if hasattr(texture_atlas,'image'):return texture_atlas.image
 im=Image.new('RGBA',(128,128),(0,0,0,0))
 for index,key in enumerate(COLORS):
  ox=(index%8)*16;oy=(index//8)*16;base=PALETTE[key];tile=Image.new('RGBA',(16,16));d=ImageDraw.Draw(tile)
  for y in range(16):
   for x in range(16):
    grain=((x*7+y*11+index*5)%7)-3
    if key.startswith('fur'):grain=grain//2
    color=tuple(max(0,min(255,v+grain)) for v in base)
    if key in ['cyan','magenta','emerald','violet','gem_dark']:
     phase=(x*.06+y*.031+.14*math.sin(y*.45)+index*.15)%1
     stops=[(20,137,174),(57,41,141),(160,26,149),(23,149,112)];q=phase*4;j=int(q);f=q-j;color=tuple(round(stops[j][k]*(1-f)+stops[(j+1)%4][k]*f) for k in range(3))
    tile.putpixel((x,y),(*color,255))
  if key.startswith('fur'):
   for j in range(7):
    x=(j*7+index*3)%16;y=(j*11)%16;c=tuple(min(255,v+5) for v in base)+(255,)
    d.line([(x,y),(max(0,x-1),min(15,y+3))],fill=c)
  elif key.startswith('eye'):
   d.ellipse((1,1,14,14),fill=(*base,255));d.rectangle((7,2,9,14),fill=(12,12,23,255));d.point((4,4),fill=(225,244,233,255))
  elif key in ['gold_old','gold_light']:
   d.arc((2,2,13,13),0,280,fill=(245,209,121,255),width=1);d.arc((5,5,10,10),30,320,fill=(92,62,32,255))
  elif key=='inner_ear':
   for x in [3,7,11]:d.line([(x,0),(x+1,15)],fill=(88,28,57,255))
  im.paste(tile,(ox,oy))
 texture_atlas.image=im;return im

def atlas(path):texture_atlas().save(path)

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
   vs,nr,ix=primitive(c,b['pivot']);pmin=[min(v[k] for v in vs) for k in range(3)];pmax=[max(v[k] for v in vs) for k in range(3)];pa=buf(struct.pack('<'+'f'*(len(vs)*3),*(x for v in vs for x in v)),'VEC3',len(vs),mins=pmin,maxs=pmax);na=floats(nr,'VEC3');tile=COLORS.index(c['material']);u0=((tile%8)*16+.5)/128;v0=((tile//8)*16+.5)/128;u1=u0+15/128;v1=v0+15/128;ta=floats([(u0,v0),(u1,v0),(u1,v1),(u0,v1)]*6,'VEC2');ii=buf(struct.pack('<'+'H'*len(ix),*ix),'SCALAR',len(ix),5123);ps.append({'attributes':{'POSITION':pa,'NORMAL':na,'TEXCOORD_0':ta},'indices':ii,'material':COLORS.index(c['material'])})
  if ps:nodes[-1]['mesh']=len(meshes);meshes.append({'name':name,'primitives':ps})
 animations=[]
 for clip in a.clips:
  channels=[];samplers=[];times=[i/16*1.6 for i in range(17)];ti=floats(times,'SCALAR');access[ti]['min']=[0];access[ti]['max']=[1.6]
  for name,(axis,amp,phase) in a.clips[clip].items():
   qs=[quat(axis,amp*math.sin(i/16*math.tau+phase)) for i in range(17)];ri=floats(qs,'VEC4');samplers.append({'input':ti,'output':ri,'interpolation':'LINEAR'});channels.append({'sampler':len(samplers)-1,'target':{'node':names.index(name),'path':'rotation'}})
  if channels:animations.append({'name':clip,'channels':channels,'samplers':samplers})
 mats=[{'name':key,'pbrMetallicRoughness':{'baseColorTexture':{'index':0},'metallicFactor':.55 if key in ['gold','gold_old','cyan','cobalt','magenta','amber'] else 0,'roughnessFactor':.4 if key in ['gold','gold_old','porcelain'] else .8},**({'emissiveTexture':{'index':0},'emissiveFactor':[.65,.65,.65]} if key.startswith('eye') else {})} for key in COLORS]
 texture=io.BytesIO();texture_atlas().save(texture,format='PNG');png=texture.getvalue()
 while len(blob)%4:blob.append(0)
 image_view=len(views);views.append({'buffer':0,'byteOffset':len(blob),'byteLength':len(png)});blob.extend(png)
 doc={'asset':{'version':'2.0','generator':'NorthStar original voxel-sculpt hare boss v04'},'scene':0,'scenes':[{'nodes':[0]}],'nodes':nodes,'meshes':meshes,'materials':mats,'images':[{'bufferView':image_view,'mimeType':'image/png'}],'samplers':[{'magFilter':9728,'minFilter':9728,'wrapS':33071,'wrapT':33071}],'textures':[{'sampler':0,'source':0}],'animations':animations,'buffers':[{'byteLength':len(blob)}],'bufferViews':views,'accessors':access}
 js=json.dumps(doc,separators=(',',':')).encode();js+=b' '*((-len(js))%4);blob+=b'\0'*((-len(blob))%4);path.write_bytes(struct.pack('<4sII',b'glTF',2,12+8+len(js)+8+len(blob))+struct.pack('<I4s',len(js),b'JSON')+js+struct.pack('<I4s',len(blob),b'BIN\0')+blob)

def render(a,clip,t,size=600,yaw=35):
 # Genuine articulated orthographic3D projection. Fixed rest-space camera; actual painted atlas UV sampling.
 cubes=a.transformed(clip,t);rest=[p for c in a.cubes for p in points(c)]
 center=tuple((min(p[k] for p in rest)+max(p[k] for p in rest))/2 for k in range(3));rad=math.radians(yaw);el=math.radians(18)
 def camera(p):
  x,y,z=sub(p,center);xx=x*math.cos(rad)-z*math.sin(rad);zz=x*math.sin(rad)+z*math.cos(rad)
  return (xx,-y*math.cos(el)+zz*math.sin(el),zz*math.cos(el)+y*math.sin(el))
 base=[camera(p) for p in rest];span=max(max(p[0] for p in base)-min(p[0] for p in base),max(p[1] for p in base)-min(p[1] for p in base))*1.16;unit=(size-56)/span
 image=Image.new('RGB',(size,size),(24,31,45));polys=[];paint=texture_atlas().convert('RGB')
 for verts,mat in cubes:
  cv=[camera(p) for p in verts]
  for ni,(normal,ids) in enumerate(FACES):
   ps=[(size/2+cv[j][0]*unit,size/2+cv[j][1]*unit) for j in ids];depth=sum(cv[j][2] for j in ids)/4
   #Cull hidden cube faces and use the actual articulated face normal for diffuse lighting.
   area=(ps[1][0]-ps[0][0])*(ps[3][1]-ps[0][1])-(ps[1][1]-ps[0][1])*(ps[3][0]-ps[0][0])
   if area>=-.01:continue
   u=sub(verts[ids[1]],verts[ids[0]]);v=sub(verts[ids[3]],verts[ids[0]]);n=(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]);length=math.sqrt(sum(q*q for q in n));light=(-.35,.75,.55);dot=sum(n[k]*light[k] for k in range(3))/max(length,1e-8)
   shade=1.05 if mat.startswith('eye') else .48+.68*max(0,dot)
   polys.append((depth,ps,mat,shade))
 for _,ps,mat,shade in sorted(polys,key=lambda row:row[0]):
  ex,ey=ps[1][0]-ps[0][0],ps[1][1]-ps[0][1];fx,fy=ps[3][0]-ps[0][0],ps[3][1]-ps[0][1];det=ex*fy-ey*fx
  if abs(det)<.05:continue
  left=max(0,math.floor(min(p[0] for p in ps)));top=max(0,math.floor(min(p[1] for p in ps)));right=min(size,math.ceil(max(p[0] for p in ps)));bottom=min(size,math.ceil(max(p[1] for p in ps)))
  if right<=left or bottom<=top:continue
  index=COLORS.index(mat);ox=(index%8)*16;oy=(index//8)*16;dx=left-ps[0][0];dy=top-ps[0][1]
  coeff=(15*fy/det,-15*fx/det,ox+15*(dx*fy-dy*fx)/det,-15*ey/det,15*ex/det,oy+15*(-dx*ey+dy*ex)/det)
  layer=paint.transform((right-left,bottom-top),Image.Transform.AFFINE,coeff,resample=Image.Resampling.NEAREST)
  layer=ImageEnhance.Brightness(layer).enhance(shade);mask=Image.new('L',layer.size);ImageDraw.Draw(mask).polygon([(p[0]-left,p[1]-top) for p in ps],fill=255)
  image.paste(layer,(left,top),mask)
 return image

def export_asset(a,dest):
 home=dest/a.name;home.mkdir();(home/'MODEL').mkdir();glb(a,home/'MODEL'/f'{a.name}.glb');atlas(home/'MODEL'/'palette.png')
 save_json(home/'MODEL'/'original_rig.json',{'name':a.name,'revision':'boss_v04','carrier':a.carrier,'bones':a.bones,'cubes':a.cubes,'clips':a.clips,'units':'Minecraft pixels,16perblock,+Zforward,+Yup','provisional_namespaced_id':NS+':'+a.name,'numeric_id_allocated':False})
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
    if c['bone']!=bn or c['material'].startswith('eye')!=(layer=='eyes'):continue
    x,y,z=c['min'];sx,sy,sz=c['size'];u=uv(c['material']);cub.append({'origin':[x,y,-z-sz],'size':[sx,sy,sz],'uv':{f:{'uv':[u[0]*8,u[1]*8],'uv_size':[16,16]} for f in ['north','south','east','west','up','down']}})
   if cub:bone['cubes']=cub
   bones.append(bone)
  ident='geometry.'+NS+'.'+a.name+'.'+layer;save_json(bp/f'models/entity/{a.name}_{layer}.geo.json',{'format_version':'1.12.0','minecraft:geometry':[{'description':{'identifier':ident,'texture_width':128,'texture_height':128,'visible_bounds_width':max(7,(max(c['min'][0]+c['size'][0] for c in a.cubes)-min(c['min'][0] for c in a.cubes))/16+2),'visible_bounds_height':max(5,(max(c['min'][1]+c['size'][1] for c in a.cubes)-min(c['min'][1] for c in a.cubes))/16+2),'visible_bounds_offset':[0,(max(c['min'][1]+c['size'][1] for c in a.cubes)+min(c['min'][1] for c in a.cubes))/32,0]},'bones':bones}]})
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
 default=a.preview_clip;desc['scripts']['animate']=[default]
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
 for yaw in [30,150,270,0]:views.append(render(a,default,.15,1000,yaw))
 sheet=Image.new('RGB',(2000,2000),(24,31,45))
 for i,im in enumerate(views):sheet.paste(im,((i%2)*1000,(i//2)*1000))
 sheet.save(previews/'four_views.png')
 frames=[render(a,default,i/16,650,35) for i in range(16)];frames[0].save(previews/'articulated_software_preview.gif',save_all=True,append_images=frames[1:],duration=100,loop=0)
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
  sizes={5126:4,5123:2};components={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}
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
