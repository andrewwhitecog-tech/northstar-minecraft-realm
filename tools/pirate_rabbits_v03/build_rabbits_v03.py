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


# Four replacement rabbits only. Geometry is original; animal and dress references are documented separately.
PALETTE.update({'fur_charcoal':(62,69,83),'fur_ash':(144,151,154),'fur_brown':(112,89,79),
 'velvet':(100,26,65),'brocade':(80,39,111),'oilcloth':(48,68,88),'porcelain':(223,230,218),
 'crack':(46,48,62),'ivory':(234,218,179),'gold_old':(213,165,70),'pink':(109,53,78),
 'cyan':(40,219,218),'magenta':(218,47,166),'amber':(245,181,46),'cobalt':(61,103,230),'emerald':(35,224,153),'eye_purple':(215,75,243)})
COLORS=list(PALETTE)

def stepped(a,bone,rows,mat):
 for center,size in rows:a.box(bone,center,size,mat)

def hare_face(a,pivot,scale_factor=1,mask=False):
 x,y,z=pivot;s=scale_factor
 a.bone('head',pivot,'chest');a.bone('muzzle',(x,y-3*s,z+6*s),'head');a.bone('jaw',(x,y-4*s,z+3*s),'head')
 for side,sgn in [('left',-1),('right',1)]:a.bone(side+'_eye',(x+sgn*3.5*s,y+1.3*s,z+3.7*s),'head')
 fur='porcelain' if mask else 'fur_charcoal';cheek='porcelain' if mask else 'fur_ash'
 # Tapered cranium, forward orbital shelves and visible cheek breaks, not a cube with a beak.
 for dy,w,h,d,dz in [(1.8,6.7,3.2,6,0),(0,8.2,3.4,6.8,.8),(-2.2,6.4,2.2,5.8,1.5)]:
  a.box('head',(x,y+dy*s,z+dz*s),(w*s,h*s,d*s),fur)
 for sg in [-1,1]:
  a.box('head',(x+sg*3.4*s,y+1.8*s,z+4*s),(2.4*s,1.2*s,2.6*s),'porcelain' if mask else 'oilcloth')
  # Sockets behind tiny luminous pupils retain a clear animal eye line.
  a.box('head',(x+sg*3.5*s,y+.1*s,z+4.1*s),(2*s,1.5*s,.8*s),'crack')
  a.box(('left' if sg<0 else 'right')+'_eye',(x+sg*3.5*s,y+.1*s,z+4.62*s),(.64*s,.8*s,.3*s),'eye')
  # Separate paired whisker beds, small black nose, cleft lip and two front incisors.
  for dz,ww,hh in [(4.8,3.1,2.5),(6.3,2.7,2.2),(7.1,1.9,1.6)]:
   a.box('muzzle',(x+sg*1.25*s,y-2.8*s,z+dz*s),(ww*s,hh*s,1.5*s),cheek)
  for j in range(3):
   p=(x+sg*2.2*s,y-(2.2+j*.55)*s,z+6.9*s);q=(x+sg*(6+j*.65)*s,y-(1.6+j*.9)*s,z+(7.8-j*.3)*s)
   a.bar('muzzle',p,q,.13*s,'ivory' if not mask else 'gold_old')
  a.box('jaw',(x+sg*.53*s,y-5.4*s,z+6.2*s),(.82*s,2.4*s,.95*s),'ivory')
 a.box('muzzle',(x,y-2.25*s,z+8.1*s),(1.55*s,.7*s,.65*s),'crack')
 a.box('muzzle',(x,y-2.72*s,z+8.04*s),(.8*s,.5*s,.48*s),'pink' if not mask else 'crack')
 a.box('muzzle',(x,y-3.2*s,z+7.91*s),(.18*s,.8*s,.18*s),'crack')
 a.box('jaw',(x,y-4.5*s,z+4.5*s),(4.3*s,1.5*s,4*s),cheek)
 if mask:
  # Thin irregular seams and displaced shards, never a gold protruding nose.
  for p,q in [((-2,3.2,3.65),(-1.5,1.8,4.4)),((-1.5,1.8,4.4),(-2.3,.8,4.5)),((1.3,3.1,3.7),(2.3,2.1,4.5)),((3,-1,4.3),(2.1,-2.8,5.8))]:
   a.bar('head',tuple(pivot[i]+p[i]*s for i in range(3)),tuple(pivot[i]+q[i]*s for i in range(3)),.14*s,'crack')
  a.box('head',(x-4.25*s,y-1.5*s,z+2.1*s),(.6*s,1.8*s,2*s),'gold_old')

def crooked_ears(a,origin,s=1,material='fur_charcoal'):
 x,y,z=origin
 for side,sgn in [('left',-1),('right',1)]:
  base=side+'_ear_base';tip=side+'_ear_tip';a.bone(base,(x+sgn*2.3*s,y,z),'head')
  # Asymmetry is in real geometry and two joints per ear.
  end=(x+sgn*(4.7 if sgn<0 else 3.2)*s,y+(11 if sgn<0 else 13)*s,z-(1.7 if sgn<0 else .8)*s)
  a.bone(tip,end,base)
  a.bar(base,(x+sgn*2.3*s,y,z),end,2.15*s,material)
  a.bar(base,(x+sgn*2.3*s,y+.8*s,z+1.13*s),(end[0],end[1]-.7*s,end[2]+1.13*s),.9*s,'velvet')
  bent=(end[0]+sgn*(4.4 if sgn<0 else -1.8)*s,end[1]+(7.2 if sgn<0 else 10)*s,end[2]+(3.4 if sgn<0 else -3.2)*s)
  a.bar(tip,end,bent,1.7*s,material);a.bar(tip,(end[0],end[1],end[2]+.9*s),(bent[0],bent[1]-.5*s,bent[2]+.9*s),.65*s,'pink')
  a.box(tip,bent,(1.7*s,1.8*s,1.5*s),'gold_old' if sgn<0 else material)


def eye_seal(a,bone,center,width,height):
 x,y,z=center
 pts=[(x+math.cos(i*math.tau/12)*width/2,y+math.sin(i*math.tau/12)*height/2,z) for i in range(12)]
 for p,q in zip(pts,pts[1:]+pts[:1]):a.bar(bone,p,q,.32,'gold_old')
 a.box(bone,(x,y,z+.25),(.65,height*.64,.38),'magenta');a.box(bone,(x,y,z+.48),(.22,height*.58,.16),'crack')
 for sg in [-1,1]:a.bar(bone,(x+sg*width*.2,y-height*.45,z),(x+sg*width*.3,y-height*.78,z),.22,'gold_old')

def victorian_v03(kind):
 names={'duelist':'velvet_hare_duelist','watchkeeper':'porcelain_rabbit_watchkeeper','herald':'stitched_hare_herald'}
 a=Asset(names[kind],names[kind].replace('_',' ').title()+' v03','minecraft:rabbit')
 # Each character has an animal hunch, narrow waist, bent hocks and head forward of its shoulders.
 tall=kind=='herald';hy=18 if tall else 15;cy=31 if tall else 28
 a.bone('hips',(0,hy,-2));a.bone('body',(0,cy-7,-.7),'hips');a.bone('chest',(0,cy,1.8),'body')
 face=(0,cy+8,5.5);hare_face(a,face,1.05 if tall else 1,kind=='watchkeeper');crooked_ears(a,(0,cy+11,4.8),.8 if kind=='duelist' else .9,'porcelain' if kind=='watchkeeper' else 'fur_brown' if tall else 'fur_charcoal')
 cloth='velvet' if kind=='duelist' else 'oilcloth' if kind=='watchkeeper' else 'brocade'
 for c,sz in [((0,hy,-2),(7,8,7)),((0,cy-7,-.4),(7.4,8,6.5)),((0,cy-1,1),(9.6,8,8)),((0,cy+3,1.5),(8,3.5,7))]:a.box('body' if c[1]<cy-3 else 'chest',c,sz,cloth)
 # Three-dimensional rolled lapels form a V, layered shirt, cravat and shaped double-breasted fronts.
 a.box('chest',(0,cy-.2,5.2),(3.3,8.4,.55),'ivory');a.box('chest',(0,cy+2.8,5.8),(2,1.4,1),'velvet')
 a.box('chest',(0,cy+1.3,5.9),(1.1,2.2,.6),'gold_old')
 for sg in [-1,1]:
  for j in range(5):a.box('chest',(sg*(3.5-j*.4),cy+3-j*1.5,5.55),(.9,1.9,.8),'gold_old' if j==0 else cloth)
  for j in range(3):a.box('body',(sg*2.3,cy-5.3-j*1.6,3.2),(.52,.55,.45),'gold_old')
  a.box('chest',(sg*4.3,cy+2,1.6),(2,2.8,6.8),'oilcloth')
  # Segmented coat tails move independently and end in different weathered lengths.
  bn=('left' if sg<0 else 'right')+'_coat_tail';a.bone(bn,(sg*2.4,hy+1,-4),'hips')
  for j in range(5):
   a.box(bn,(sg*(2.5+j*.15),hy-1-j*1.5,-4.5-j*.12),(4.2-j*.25,2.2,.85),cloth)
  a.box(bn,(sg*3.7,hy-7.6,-5.15),(.7,1.3,.5),'gold_old')
 # Non-human legs: enlarged thighs, backward hock break, long rabbit feet in worn spats.
 for side,sg in [('left',-1),('right',1)]:
  thigh=side+'_thigh';hock=side+'_hock';foot=side+'_foot';a.bone(thigh,(sg*3,hy-2,-1.8),'hips');a.bone(hock,(sg*3,hy-8,-4.8),thigh);a.bone(foot,(sg*3,3,1.5),hock)
  a.box(thigh,(sg*3.3,hy-4.5,-1.9),(4.4,7,6.3),'fur_charcoal');a.bar(hock,(sg*3,hy-7,-4.3),(sg*3,4,-1),2.4,'fur_charcoal')
  for z,w in [(0,3.3),(3,4),(5.8,3.2)]:a.box(foot,(sg*3,2.3,z),(w,3,3),'fur_charcoal')
  a.box(foot,(sg*3,4,-.4),(3.3,3,3),'ivory')
  for dz in [-1,.1,1.2]:a.box(foot,(sg*4.8,4,dz),(.3,.4,.5),'gold_old')
  arm=side+'_arm';fore=side+'_forearm';hand=side+'_hand';a.bone(arm,(sg*5,cy+1.4,2),'chest');a.bone(fore,(sg*7.1,cy-5,2.5),arm);a.bone(hand,(sg*7.2,cy-11,4.3),fore)
  a.bar(arm,(sg*5,cy+.8,2),(sg*7,cy-5,2.5),3.1,cloth);a.bar(fore,(sg*7,cy-5,2.5),(sg*7.2,cy-10,4),2.6,cloth)
  a.box(fore,(sg*7.2,cy-10,4),(3.4,1.7,3.7),'gold_old');a.box(fore,(sg*7.2,cy-10.7,4.2),(3.2,.8,3.5),'ivory')
  a.box(hand,(sg*7.2,cy-12,4.8),(2.9,2.6,3.5),'fur_ash')
  for x in [-.8,0,.8]:a.box(hand,(sg*7.2+x,cy-13,6.5),(.6,1,.7),'ivory')
 # Deliberate VORATH inlaid seams and original saturated patches, not featureless flat coats.
 for j,mat in enumerate(['cyan','magenta','cobalt','amber']):
  a.box('body',(-2.9,cy-7+j*.8,3.45),(1.4,.35,.3),mat)
 if tall:
  a.box('chest',(-3,cy,5.6),(2.1,3,.45),'fur_ash')
  for j in range(4):a.bar('chest',(-4,cy-1+j*.8,5.9),(-2.1,cy-.8+j*.8,5.9),.14,'gold_old')
 if kind=='duelist':
  a.bone('blade',(-7.2,cy-11,4.3),'left_hand')
  # Curved stepped sabre, pierced basket guard, a separate slanted scabbard.
  for j in range(19):a.box('blade',(-7.2-j*j*.008,cy-10+j*.75,7),(.42,.9,.8),'ivory')
  for sg in [-1,1]:a.bar('blade',(-7.2,cy-11,6),(-7.2+sg*2,cy-9.5,7),.35,'gold_old')
  a.box('blade',(-7.2,cy-12,7),(.8,3,.9),'crack')
  a.bar('hips',(4.3,hy+2,-1),(6.7,hy-8,-4),.8,'gold_old')
 if kind=='watchkeeper':
  # Pocket chronometer, scalloped collar and original blind eye-seal ornament.
  a.bone('watch',(6.5,cy-12,7),'right_hand');a.box('watch',(6.5,cy-12,7),(3.1,3.1,1),'gold_old');a.box('watch',(6.5,cy-12,7.6),(2.3,2.3,.3),'porcelain')
  a.bar('body',(3,cy-5,3.7),(5,cy-7,3.2),.2,'gold_old')
  for sg in [-1,1]:a.box('chest',(sg*2.2,cy+4.2,5),(2.8,1.1,2.2),'ivory')
 if tall:
  a.bone('staff',(7.2,cy-5,7),'right_hand');a.bar('staff',(7.2,3,7),(7.2,cy+13,7),.6,'gold_old')
  a.box('staff',(7.2,cy+14,7),(3.5,3.5,2),'oilcloth');a.box('staff',(7.2,cy+14,8.2),(.8,1.1,.3),'eye')
 eye_seal(a,'chest',(0,cy+1,-3.5),5,2.4)
 a.clips={'idle':{'chest':(0,2,.5),'head':(1,6,0),'muzzle':(0,1,.2),'jaw':(0,4,.5),'left_ear_tip':(2,5,.1),'right_ear_tip':(0,7,.8)},
 'stalk':{'hips':(0,2,0),'left_thigh':(0,12,0),'right_thigh':(0,12,math.pi),'left_hock':(0,9,math.pi),'right_hock':(0,9,0),'left_arm':(0,10,math.pi),'right_arm':(0,10,0),'left_coat_tail':(0,8,.7),'right_coat_tail':(0,10,.1),'head':(1,4,0)},
 'telegraph':{'chest':(0,5,0),'head':(1,10,.4),'jaw':(0,13,0),'left_arm':(0,28,0),'left_forearm':(0,17,.6),'right_ear_tip':(2,-14,.2)}}
 a.preview_clip='idle';return a

def boss_v03():
 a=Asset('mutant_rabbit_boss','Aurora Ossuary Hare v03','minecraft:rabbit')
 # Horizontal crouched power-hare: dominant haunches, folded long hocks, small forequarters, NO gorilla hands.
 a.bone('hips',(0,37,-15));a.bone('body',(0,49,-4),'hips');a.bone('chest',(0,46,16),'body')
 stepped(a,'hips',[((0,33,-16),(34,35,31)),((0,42,-17),(31,25,33)),((0,25,-16),(29,22,26))],'fur_charcoal')
 stepped(a,'body',[((0,48,-1),(29,26,35)),((0,55,-4),(26,15,32)),((0,41,5),(24,20,30))],'oilcloth')
 stepped(a,'chest',[((0,44,17),(24,25,25)),((0,51,17),(21,18,23)),((0,36,21),(18,17,20))],'fur_charcoal')
 hare_face(a,(0,67,31),2.2,False);crooked_ears(a,(0,75,28),1.7,'fur_charcoal')
 a.box('head',(0,61,29),(13,11,17),'fur_charcoal')
 # Broad brow and cheek scar ridges break the face into animal planes.
 for sg in [-1,1]:
  a.bar('head',(sg*4,72,39),(sg*10,71,39),2,'oilcloth')
  for j in range(3):a.box('chest',(sg*(11-j*1.6),44-j*3,24+j*.5),(2.2,2,4),'fur_ash')
  thigh=('left' if sg<0 else 'right')+'_thigh';hock=('left' if sg<0 else 'right')+'_hock';foot=('left' if sg<0 else 'right')+'_foot'
  a.bone(thigh,(sg*16,34,-13),'hips');a.bone(hock,(sg*18,17,-28),thigh);a.bone(foot,(sg*18,5,-8),hock)
  for cy,w,h,d,z in [(32,17,26,26,-15),(25,18,22,23,-17),(40,13,13,20,-16)]:a.box(thigh,(sg*17,cy,z),(w,h,d),'fur_charcoal')
  a.bar(hock,(sg*18,20,-28),(sg*18,6,-14),7,'oilcloth')
  for j in range(4):a.box(foot,(sg*18,4.3,-9+j*6),(10.7-j*.6,6.2,7),'fur_charcoal')
  for x in [-3,0,3]:a.box(foot,(sg*18+x,3.3,13),(1.8,3.3,3),'ivory')
  fore=('left' if sg<0 else 'right')+'_foreleg';wrist=('left' if sg<0 else 'right')+'_wrist';paw=('left' if sg<0 else 'right')+'_forepaw'
  a.bone(fore,(sg*10,44,19),'chest');a.bone(wrist,(sg*12,24,28),fore);a.bone(paw,(sg*12,6,33),wrist)
  a.bar(fore,(sg*10,43,19),(sg*12,25,28),6.8,'fur_charcoal');a.bar(wrist,(sg*12,25,28),(sg*12,7,33),4.5,'oilcloth')
  a.box(paw,(sg*12,5,36),(8,6,12),'fur_charcoal')
  for x in [-2.5,0,2.5]:a.box(paw,(sg*12+x,3.6,43),(1.6,2.5,3),'ivory')
 # Split quartz/aurora ridge follows the actual spine, with distinct moving sections.
 for index,(y,z) in enumerate([(53,-23),(62,-3),(58,15)]):
  bn='spine_crystal_'+str(index);a.bone(bn,(0,y,z),'body' if index<2 else 'chest')
  for j in range(4):
   color=['cyan','magenta','violet','emerald'][(index+j)%4]
   a.box(bn,((j-1.5)*2.5,y+3+j%2*2,z-j*.8),(2.2,6+j%2*4,3.1),color)
   a.box(bn,((j-1.5)*2.5,y+7+j%2*3,z-j*.8),(1.1,2,1.5),'gold_old')
 a.bone('tail',(0,31,-33),'hips');stepped(a,'tail',[((0,31,-34),(13,12,9)),((0,32,-39),(9,8,5))],'fur_ash')
 # Readable golden eye-seal at shoulder, luminous pupils are independent displays only.
 for j,mat in enumerate(['cyan','violet','magenta','emerald']):a.box('body',(15,47+j*2,-1),(1.2,1.3,8-j),mat)

 # Layered original fur-edge geometry, each shard follows a body surface rather than enlarging the collider.
 for bone,pivot,surface,ys,zs in [
  ('hips',(0,37,-15),17.2,[22,29,36,43],[-25,-18,-11,-5]),
  ('body',(0,49,-4),15.2,[40,47,54],[-16,-9,-2,5,12]),
  ('chest',(0,46,16),12.3,[34,41,48],[12,18,24])]:
  for sg in [-1,1]:
   for iy,y in enumerate(ys):
    for iz,z in enumerate(zs):
     color=['fur_charcoal','fur_ash','oilcloth'][(iy+iz)%3]
     a.box(bone,(sg*(surface+(iz%2)*.55),y+(iz%2)*.6,z),(1.5,4.8,3.7),color)
     a.box(bone,(sg*(surface+.55),y-2.6,z+.8),(1.1,1.5,2.3),'fur_charcoal')
 # Raked cheek/haunch tufts and broad rear feet keep the silhouette hare-like.
 for sg in [-1,1]:
  for j in range(7):
   a.box('head',(sg*(8.8+j%2*.8),66-j*1.35,34+j*.7),(1.6,2.8,3.2),'fur_ash' if j%3 else 'oilcloth')
  for j in range(5):
   a.box('hips',(sg*(14.5+j*.5),47-j*1.7,-25-j*.1),(2,3.8,3),'fur_ash' if j%2 else 'fur_charcoal')
 # Eye-seal ornament is original fiction, embedded in metal harness geometry.
 eye_seal(a,'chest',(0,43,29.7),10,5)
 eye_seal(a,'head',(0,73.4,35.8),5.4,2.5)
 for sg in [-1,1]:
  a.bar('chest',(sg*7,47,29.4),(sg*10.7,36,25),.65,'gold_old')
  a.box(('left' if sg<0 else 'right')+'_wrist',(sg*12,13,31.8),(5.2,2,5.2),'gold_old')

 a.clips={'idle':{'body':(0,2,.2),'chest':(0,3,0),'head':(1,5,.6),'jaw':(0,5,.1),'left_ear_tip':(2,5,.2),'right_ear_tip':(0,-8,.3),'spine_crystal_1':(2,3,0)},
 'prowl':{'hips':(0,2,0),'left_thigh':(0,13,0),'right_thigh':(0,13,math.pi),'left_hock':(0,10,math.pi),'right_hock':(0,10,0),'left_foreleg':(0,14,math.pi),'right_foreleg':(0,14,0),'left_wrist':(0,9,0),'right_wrist':(0,9,math.pi),'head':(1,5,.1)},
 'snarl_telegraph':{'chest':(0,7,0),'head':(0,-12,.7),'jaw':(0,24,0),'left_ear_base':(0,9,0),'right_ear_tip':(2,17,.4),'spine_crystal_0':(2,-7,0),'spine_crystal_1':(2,9,0),'spine_crystal_2':(2,-8,0)}}
 for c in a.cubes:
  if c['bone']=='right_eye':c['material']='eye_purple'
 a.preview_clip='idle';return a

def all_assets():return [boss_v03(),victorian_v03('duelist'),victorian_v03('watchkeeper'),victorian_v03('herald')]

def texture_atlas():
 # Original painted pixel tiles: worn fur, woven brocade, oil-slick stitch bands and porcelain fissures.
 if hasattr(texture_atlas,'image'):return texture_atlas.image
 im=Image.new('RGBA',(128,128),(0,0,0,0))
 jewel=['cyan','cobalt','magenta','emerald','teal','violet']
 for index,key in enumerate(COLORS):
  ox=(index%8)*16;oy=(index//8)*16;tile=Image.new('RGBA',(16,16));d=ImageDraw.Draw(tile);base=PALETTE[key]
  for y in range(16):
   for x in range(16):
    grain=((x*17+y*29+index*11)%13)-6
    edge=-11 if min(x,y,15-x,15-y)<1 else 0
    tile.putpixel((x,y),tuple(max(0,min(255,v+grain+edge)) for v in base)+(255,))
  if key in ['oilcloth','brocade','velvet']:
   # Authored interlaced chevrons and dotted stitch lines, with exposed worn-thread patches.
   for y in range(2,16,4):
    col=PALETTE[jewel[(y//4+index)%len(jewel)]]
    d.line([(0,y),(3,y-2),(7,y+1),(11,y-1),(15,y+1)],fill=(*col,255),width=1)
   for x in [1,14]:
    for y in range(1,16,3):d.point((x,y),fill=(*PALETTE['gold_old'],255))
   d.line([(5,12),(7,11),(8,12)],fill=(*PALETTE['fur_ash'],255))
  elif key.startswith('fur'):
   for j in range(14):
    x=(j*7+index)%16;y=(j*11+3)%16
    d.line([(x,y),(max(0,x-1),min(15,y+2))],fill=tuple(max(0,v-20) for v in base)+(255,))
  elif key=='porcelain':
   d.line([(2,0),(4,4),(3,7),(7,11),(6,15)],fill=(*PALETTE['crack'],255),width=1)
   d.line([(3,7),(0,8)],fill=(*PALETTE['crack'],255));d.line([(7,11),(12,9)],fill=(*PALETTE['gold_old'],255))
  elif key in ['gold_old','gold']:
   d.line([(0,2),(15,2),(15,4),(3,4),(3,12),(13,12)],fill=(251,216,121,255))
   for p in [(7,7),(11,6),(2,14)]:d.point(p,fill=(52,133,128,255))
  elif key in jewel:
   d.line([(0,14),(5,7),(9,10),(15,1)],fill=(245,240,211,255))
   d.line([(0,15),(6,8),(10,11),(15,2)],fill=(*PALETTE[jewel[(jewel.index(key)+2)%len(jewel)]],255))
  elif key=='ivory':
   d.line([(2,0),(2,15)],fill=(174,151,120,255));d.line([(13,0),(13,15)],fill=(253,244,211,255))
  im.paste(tile,(ox,oy))
 texture_atlas.image=im
 return im

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
 doc={'asset':{'version':'2.0','generator':'NorthStar original rabbit rebuild v03'},'scene':0,'scenes':[{'nodes':[0]}],'nodes':nodes,'meshes':meshes,'materials':mats,'images':[{'bufferView':image_view,'mimeType':'image/png'}],'samplers':[{'magFilter':9728,'minFilter':9728,'wrapS':33071,'wrapT':33071}],'textures':[{'sampler':0,'source':0}],'animations':animations,'buffers':[{'byteLength':len(blob)}],'bufferViews':views,'accessors':access}
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
   shade=max(1,[1,.74,.9,.8,1.12,.66][ni]) if mat.startswith('eye') else [1,.74,.9,.8,1.12,.66][ni]
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
 save_json(home/'MODEL'/'original_rig.json',{'name':a.name,'revision':'rabbit_v03','carrier':a.carrier,'bones':a.bones,'cubes':a.cubes,'clips':a.clips,'units':'Minecraft pixels,16perblock,+Zforward,+Yup','provisional_namespaced_id':NS+':'+a.name,'numeric_id_allocated':False})
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
