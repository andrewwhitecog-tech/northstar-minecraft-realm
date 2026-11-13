#!/usr/bin/env python3
"""Original cat coat painter. Source-only until explicitly invoked in a new output folder.
No Mojang/third-party image input; no network, game/profile writes, numeric IDs or pet edits.
UV facts are independently transcribed from the installed official 26.3 feline model classes.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import zlib

HERE = Path(__file__).resolve().parent
IDENT = re.compile(r'nsp_cat_coats:[a-z][a-z0-9_]{1,80}\Z')
FACES = ('west', 'north', 'east', 'south', 'up', 'down')
RAINBOW = ((255,78,135),(255,158,62),(245,219,70),(69,224,148),(57,178,249),(155,104,250))

def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def color(value):
    if not isinstance(value,str) or re.fullmatch(r'#[0-9a-fA-F]{6}',value) is None:
        raise ValueError('RGB hex required')
    return tuple(bytes.fromhex(value[1:]))

def mix(a,b,t):
    t=max(0.,min(1.,t))
    return tuple(round(x+(y-x)*t) for x,y in zip(a,b))

def rainbow(t):
    t=(t%1)*len(RAINBOW); n=int(t)
    return mix(RAINBOW[n],RAINBOW[(n+1)%len(RAINBOW)],t-n)

def face_rects(uv,size):
    """Standard Java/Bedrock box UV net, dimensions BEFORE cube inflation."""
    if isinstance(uv,dict):
        if set(uv)!=set(FACES): raise ValueError('All six per-face UV regions required')
        return {f:(*uv[f]['uv'],*uv[f]['uv_size']) for f in FACES}
    u,v=uv; w,h,d=size
    return dict(zip(FACES,((u,v+d,d,h),(u+d,v+d,w,h),(u+d+w,v+d,d,h),
                           (u+2*d+w,v+d,w,h),(u+d,v,w,d),(u+d+w,v,w,d))))

def surface(face,u,v):
    # Local box coordinates; front is negative Z. Order matches preview vertices.
    return {'west':(0,1-v,1-u),'north':(u,1-v,0),'east':(1,1-v,u),
            'south':(1-u,1-v,1),'up':(u,1,1-v),'down':(u,0,1-v)}[face]

def canonical(cube,face,u,v,axis):
    x,y,z=surface(face,u,v)
    region=cube['region']
    # Surface UV uses Y-up. Java local Y is downward, so reverse it.
    local_y=1-y if axis=='java_down' else y
    if region=='body' and axis=='java_down' and abs(cube['rotation'][0]-90)<.01:
        return x,z,local_y  # adult long body is rotated; head and baby are NOT
    return x,(1-local_y if axis=='java_down' else local_y),z

def cell_distance(x,h,t,density,phase,elongation=1.):
    # Deliberately authored staggered rows, NOT random/hash noise.
    col=t*density+phase+.13*math.sin(h*8)
    row=h*3.2+.5*(math.floor(col)%2)
    return math.hypot(((col+.5)%1-.5)*elongation,(row+.5)%1-.5)

def fantasy_marking(s,x,h,t,region):
    """Localized aurora ink follows anatomy; most body pixels remain dark.
    Reference was personally inspected: readable black anatomy, narrow prismatic
    flowing ribbons and jewel accents, not an all-over striped recolor.
    """
    p=s['pattern']; phase=s['phase']
    if region=='crystal': return 'crystal'
    if region=='ear': return 'rainbow' if h>.8 else 'base'
    if region=='leg':
        cuff=.72+.07*math.sin(x*5+phase*4)
        return 'gold' if abs(h-cuff)<.035 else ('rainbow' if abs(h-cuff-.07)<.045 else 'base')
    if region=='head':
        brow=.79+.07*math.sin(x*7+phase*4)
        return 'rainbow' if abs(h-brow)<.055 else 'base'
    if region=='nose': return 'base'
    if region=='tail':
        arc=.58+.19*math.sin(t*6+phase*5)
        return 'rainbow' if abs(h-arc)<.065 else 'base'
    # Two thin, continuous, nonparallel streams, with reserved dark chest/belly.
    arc=.57+.16*math.sin(t*5.4+phase*5)
    secondary=.31+.08*math.sin(t*8.2+phase*4)
    gap=abs(h-arc); fine=abs(h-secondary)
    in_stream=.12<t<.94 and (gap<.052 or fine<.028)
    if p=='portal':
        eye=math.hypot((t-.56)/.19,(h-.56)/.14)
        if .84<eye<1.13: return 'gold'
        if eye<.72 and abs(t-.56)>.035: return 'rainbow'
        if eye<.72: return 'base'  # black slit remains readable
    if p=='guilloche':
        knot=math.hypot((t-.3)/.15,(h-.64)/.15)
        if .82<knot<1.1 and abs(math.sin(t*36+h*17))<.7: return 'gold'
        if in_stream and math.sin(t*32+h*17)>.25: return 'gold'
    if p=='loomwheel':
        dx=t-.68; dy=h-.62; radius=math.hypot(dx,dy)
        if .12<radius<.155: return 'gold'
        if .045<radius<.15 and abs(math.sin(math.atan2(dy,dx)*8))<.25: return 'gold'
    if p=='opal' and in_stream: return 'opal'
    if in_stream: return 'rainbow'
    if p=='aurora' and .12<t<.94 and .052<gap<.066: return 'gold'
    return 'base'

def marking(s,x,h,t,region):
    """Semantic mask independent of colors; useful for genuine topology regressions."""
    p=s['pattern']; d=s['density']; phase=s['phase']; mark=s['mark']
    # Intentional white gloves override point coloration; crystal extras stay jewel-like.
    if mark in ('socks','gloves','tuxedo') and region=='leg' and h<(.2 if mark=='gloves' else .36): return 'light'
    if region=='crystal': return 'crystal'
    q=cell_distance(x,h,t,d,phase)
    if p in ('points','lynx_points','mink'):
        point=region in ('ear','tail','nose') or (region=='leg' and h<.55) or region=='head'
        if point:
            if p=='lynx_points' and abs(math.sin(t*d*math.pi+h*4))>.76: return 'dark'
            return 'point' if p=='mink' else 'dark'
    if p in ('ticked','tipped') and (math.floor(t*d*3+h*11)%4==0): return 'dark'
    if p in ('mackerel','broken','tiger'):
        wave=math.sin(t*d*math.pi+.8*math.sin(h*7+phase*5))
        if abs(wave) > (.77 if p!='tiger' else .60+.25*(1-h)):
            if p!='broken' or math.sin(h*13+t*5)>.05: return 'dark'
    if p=='classic':
        whorl=math.sin(math.hypot((t-.51)*1.5,(h-.57))*(d+2)*math.pi+phase*4)
        if abs(whorl)>.73: return 'dark'
    if p in ('rosettes','snow_rosettes','ghost_rosettes') and .23<q<.44: return 'dark'
    if p in ('central_rosettes','ghost_central') and (.24<q<.46 or q<.11): return 'dark'
    if p in ('spots','tiny_spots') and q<(.17 if p=='tiny_spots' else .25): return 'dark'
    if p=='serval' and cell_distance(x,h,t,d,phase,.66)<.24: return 'dark'
    if p=='serval' and region=='head' and abs(math.sin(t*14+x*5))>.8: return 'dark'
    if p=='lynx' and q<.20: return 'dark'
    if p in ('wave','skin') and math.sin(t*d*math.pi+h*7)> .73: return 'dark'
    if p=='roan' and (math.floor(t*19)+math.floor(h*13)*2)%5 in (0,2): return 'light'
    if p=='patches' and math.sin(t*7+phase*5)+math.cos(h*6+x*4)>.4: return 'dark'
    if p in ('calico','mi_ke'):
        patch=math.sin(t*7+phase*4)+math.cos(h*6+x*3)
        if patch>.5: return 'dark'
        if patch<-.3: return 'ginger'
        return 'light'
    if p=='van' and (region=='tail' or (region=='head' and x<.45 and h>.45)): return 'dark'
    if p=='tuxedo':
        return 'light' if (h<.25 or (region=='head' and abs(x-.5)<.17 and h<.6)) else 'base'
    if p in ('portal','guilloche','opal','aurora','loomwheel'):
        return fantasy_marking(s,x,h,t,region)
    if p=='pastry':
        if region in ('body','pastry'):
            if h<.13 or h>.86 or t<.12 or t>.88: return 'crust'
            if (math.floor(t*18)+2*math.floor(h*13))%7==0: return 'sprinkle'
            return 'icing'
        if region=='ribbon': return 'rainbow_band'
        if region=='tail': return 'rainbow_tail'
    if region=='mane': return 'dark'
    if region=='crystal': return 'crystal'
    if region=='ear' and mark=='ear_tips' and h>.52: return 'dark'
    if mark in ('socks','gloves','tuxedo') and region=='leg' and h<(.2 if mark=='gloves' else .36): return 'light'
    if mark in ('bib','blaze_bib') and region=='body' and t<.25 and h<.48: return 'light'
    if mark in ('blaze','blaze_bib','heart_face') and region=='head' and abs(x-.5)<(.14+.12*(1-h)): return 'light'
    if mark=='belly' and h<.25: return 'light'
    if mark=='van' and region!='head' and region!='tail': return 'light'
    return 'base'

def sample(s,cube,face,u,v,axis):
    x,h,t=canonical(cube,face,u,v,axis); region=cube['region']
    base,dark,light,iris=map(color,(s['base'],s['dark'],s['light'],s['iris']))
    tag=marking(s,x,h,t,region)
    colors={'base':base,'dark':dark,'light':light,'point':mix(base,dark,.55),
            'ginger':(204,111,57),'gold':(241,195,69),'crystal':(81,241,227),
            'opal':mix((220,245,234),rainbow(t+h*.36),.48),'rainbow':rainbow(t+.17*math.sin(h*7)),
            'crust':(207,144,81),'icing':(255,164,208),'sprinkle':rainbow(t*2+h),
            'rainbow_band':RAINBOW[min(5,int(h*6))],'rainbow_tail':RAINBOW[min(5,int(((h+t)%1)*6))]}
    c=colors[tag]
    grain=s['grain']
    fantasy=s['pattern'] in ('portal','guilloche','opal','aurora','loomwheel')
    # Ordered hand-designed fur direction: subtle material structure, no per-pixel PRNG.
    strand=math.sin(t*(17 if grain in ('long','mane') else 29)+h*7+s['phase']*4)
    if grain in ('wave','curl','wire','wool'): strand=math.sin(t*34+1.8*math.sin(h*19))
    if grain=='skin': strand=math.sin(h*35+t*12)
    strength=.055 if grain not in ('wave','curl','wire','skin') else .11
    # Dark fantasy anatomy gets cool reflected sheen, not gold-speckled fur.
    c=mix(c,(42,56,78) if fantasy and tag=='base' else (light if strand>0 else dark),abs(strand)*(0.045 if fantasy and tag=='base' else strength))
    if region=='ear' and .15<x<.86 and .12<h<.78:
        c=mix(c,rainbow(h*.4+t*.15) if fantasy else (190,124,136),.38 if fantasy else .55)
    if region=='nose':
        c=mix(base,(43,32,71),.25) if fantasy else mix(light,(213,151,153),.28)
        if face=='north' and h>.55 and abs(x-.5)<.26: c=(55,31,70) if fantasy else (126,78,91)
        if face=='north' and h<.32 and abs(x-.5)<.10: c=dark
    if region=='head' and face=='north':
        # Actual front-face landmarks, sampled independently for 5x4 adult/baby and 6x5 Bedrock.
        if h<.25: c=mix(c,(42,39,67),.35) if fantasy else mix(c,light,.72)
        eye=(.12<x<.36 or .64<x<.88) and .43<h<.72
        if eye:
            c=(216,177,65) if s['mark']=='odd_eyes' and x>.5 else iris
        if (.12<x<.36 or .64<x<.88) and .72<=h<.87: c=dark
        if s['mark']=='tears' and (.19<x<.3 or .7<x<.81) and .13<h<.44: c=dark
        if s['pattern'] in ('caracal','cougar','lion') and abs(x-.5)<.25 and h<.43: c=light
        if h<.25 and abs(x-.5)<.14: c=(60,30,75) if fantasy else (132,82,91)
    return (*c,255)

def validate_models(models):
    for name,m in models.items():
        if name=='source' or name=='schema': continue
        if m['width'] not in (32,64) or m['height']!=32: raise ValueError('Unexpected Java atlas')
        for c in m['cubes']: validate_cube(c,m['width'],m['height'])

def validate_cube(c,width,height):
    if len(c['size'])!=3 or any(not isinstance(n,(int,float)) or isinstance(n,bool) or not math.isfinite(n) or n<=0 for n in c['size']): raise ValueError('Invalid cube')
    for _,(u,v,w,h) in face_rects(c['uv'],c['size']).items():
        if any(not isinstance(n,(int,float)) or isinstance(n,bool) or not math.isfinite(n) for n in (u,v,w,h)) or w<=0 or h<=0: raise ValueError('Malformed UV rectangle')
        if u<0 or v<0 or u+w>width+1e-6 or v+h>height+1e-6: raise ValueError('UV outside atlas: '+c['name'])

def bedrock_model(path,profile):
    doc=read_json(path); g=doc['minecraft:geometry'][0]; d=g['description']
    if (d['texture_width'],d['texture_height'])!=(128,64): raise ValueError('Bedrock atlas mismatch')
    bones={b['name']:b for b in g['bones']}; result=[]
    def chain(b):
        seen=set(); out=[]
        while b:
            if b['name'] in seen: raise ValueError('Bone cycle')
            seen.add(b['name']); out.append({'pivot':b.get('pivot',[0,0,0]),'rotation':b.get('rotation',[0,0,0])})
            parent=b.get('parent'); b=bones[parent] if parent else None
        return out
    for b in g['bones']:
        for i,c in enumerate(b.get('cubes',[])):
            name=b['name']; size=c['size']; region='body'
            if name.startswith('leg_'): region='leg'
            elif name.startswith('tail'): region='tail'
            elif name=='rainbow_ribbon': region='ribbon'
            elif name=='head':
                if i==0: region='head'
                elif size[0]>8: region='mane'
                elif max(size)<=1: region='crystal'
                elif profile=='broad_muzzle' and size[0]>4: region='nose'
                elif size[0]>4: region='ruff'
                else: region='ear'
            elif name=='body' and profile=='pastry_harness_rainbow_tail' and i>0: region='pastry'
            q={'name':name+'_'+str(i),'uv':c['uv'],'size':size,'origin':c['origin'],'pivot':c.get('pivot',b.get('pivot',[0,0,0])),
               'rotation':c.get('rotation',[0,0,0]),'chain':chain(b),'region':region,'inflate':c.get('inflate',0)}
            validate_cube(q,128,64); result.append(q)
    return {'width':128,'height':64,'axis':'bedrock_up','cubes':result,'geometry':doc}

def paint_model(model,recipe):
    width,height=model['width'],model['height']; pixels=bytearray(width*height*4); coverage=set()
    for c in model['cubes']:
        for face,(u,v,w,h) in face_rects(c['uv'],c['size']).items():
            # Cover edge texels for sub-pixel Bedrock cubes; sampling clamps inside face.
            for y in range(math.floor(v),math.ceil(v+h)):
                for x in range(math.floor(u),math.ceil(u+w)):
                    if not (0<=x<width and 0<=y<height): raise ValueError('Raster outside atlas')
                    a=max(0,min(1,(x+.5-u)/w)); b=max(0,min(1,(y+.5-v)/h))
                    pixels[(y*width+x)*4:(y*width+x)*4+4]=bytes(sample(recipe,c,face,a,b,model['axis']))
                    coverage.add((x,y))
    return bytes(pixels),len(coverage)

def png_bytes(width,height,pixels):
    if len(pixels)!=width*height*4: raise ValueError('Wrong RGBA length')
    def chunk(kind,data): return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    raw=b''.join(b'\x00'+pixels[y*width*4:(y+1)*width*4] for y in range(height))
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(raw,9))+chunk(b'IEND',b'')

def validate_inputs(root=HERE):
    roster=read_json(root/'roster_public.json')['entries']; recipes=read_json(root/'coat_recipes.json')['recipes']; models=read_json(root/'uv_models.json')
    if len(roster)!=65 or len({r['id'] for r in roster})!=65: raise ValueError('Expected exact 65 unique entries')
    new=[r for r in roster if not r['reuseVanilla']]; reused=[r for r in roster if r['reuseVanilla']]
    if len(new)!=61 or len(reused)!=4 or {r['id'] for r in new}!=set(recipes): raise ValueError('61 new /4 reused contract')
    if any(not IDENT.fullmatch(r['id']) for r in new): raise ValueError('Invalid owned identifier')
    validate_models(models)
    allmodels={}
    for r in new:
        s=recipes[r['id']]
        for k in ('base','dark','light','iris'): color(s[k])
        if not 2<=s['density']<=12 or not 0<=s['phase']<=1: raise ValueError('Paint parameters')
        profile=r['geometryProfile']
        if re.fullmatch(r'[a-z_]+',profile) is None: raise ValueError('Unsafe profile')
        allmodels[profile]=bedrock_model(root/'geometry_source'/(profile+'.geo.json'),profile)
    return roster,recipes,models,allmodels

def export(out,include_nyan=False):
    out=Path(out).resolve()
    if out.exists(): raise FileExistsError('Output must be a NEW staging folder')
    if any(p.lower() in ('saves','mods','resourcepacks','datapacks','world','v2_master','.minecraft') for p in out.parts): raise ValueError('No live/profile/world output')
    roster,recipes,models,bedrock=validate_inputs()
    if not include_nyan: raise ValueError('Complete61-set export requires explicit --include-nyan-original. This is only art authoring; no spawn/ID/mapping gate is enabled.')
    viewer=(HERE/'review_viewer.html').read_text(encoding='utf-8')
    if viewer.count('/*MODEL_DATA*/')!=1: raise ValueError('Viewer embedding marker')
    out.mkdir(parents=True,exist_ok=False)
    reviews=[]; files=[]
    def write(rel,data):
        target=out/rel; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(data)
        files.append({'path':rel,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    for r in roster:
        if r['reuseVanilla']:
            reviews.append({**r,'reusedReferenceOnly':True,'models':{}}); continue
        name=r['id'].split(':')[1]; s=recipes[r['id']]; ms={}; coverage={}
        for kind,m in (('adult',models['adult']),('baby',models['baby']),('bedrock',bedrock[r['geometryProfile']])):
            pixels,n=paint_model(m,s); png=png_bytes(m['width'],m['height'],pixels)
            write('originals/'+name+'/'+kind+'.png',png)
            ms[kind]={k:v for k,v in m.items() if k!='geometry'}
            ms[kind]['png']='data:image/png;base64,'+base64.b64encode(png).decode('ascii'); coverage[kind]=n
        reviews.append({**r,'models':ms,'coverage':coverage,'recipe':s})
    for profile,m in bedrock.items(): write('geometry_source/'+profile+'.geo.json',(json.dumps(m['geometry'],indent=2)+'\n').encode())
    data=json.dumps(reviews,separators=(',',':')).replace('<','\\u003c')
    write('RENDER_REVIEW.html',viewer.replace('/*MODEL_DATA*/',data).encode())
    receipt={'schema':'northstar.cat-original-paint-export.v1','exportedSets':61,'reusedReferences':4,'pngCount':183,
             'status':'ORIGINAL_PIXELS_EXPORTED_AWAITING_RENDERED_PERSONAL_QC_AND_NATIVE_ADOPTION',
             'nativeRun':False,'renderedPersonalQC':False,'gameInstalled':False,'mappingIDsAssigned':False,
             'nyanOriginalAuthoringOptIn':True,'nyanRuntimeSpawnEnabled':False,'geometryRuntimeRegistered':False,
             'limitations':['Vanilla Java CatVariant selects textures only; mane/ears/pastry need optional renderer implementation.',
                            'Bedrock authoring geometry is not Geyser/client mapping acceptance.',
                            'The3D viewer is a static authoring preview; no game animation, shader or native crossplay proof.',
                            'Natural coats are selected breed-inspired examples, not exhaustive breed/species or health claims.',
                            'Original Nyan-inspired pastry and rainbow pixels only; no borrowed GIF/model/audio.'],
             'files':files}
    (out/'EXPORT_ACTUAL.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    return receipt

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--out',type=Path,required=True)
    p.add_argument('--include-nyan-original',action='store_true',help='Explicit art-authoring gate; never enables rarity/mappings')
    a=p.parse_args(); r=export(a.out,a.include_nyan_original)
    print(json.dumps({'exportedSets':r['exportedSets'],'pngCount':r['pngCount'],'nativeRun':False,'out':str(a.out)}))
if __name__=='__main__': main()
