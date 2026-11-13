"""Four representative original coats; no all61 export or runtime registration."""
import copy
import math
from pathlib import Path
import baseline_paint as B
ROOT=Path(__file__).resolve().parent

STYLES={
 'domestic_bengal':{'base':'#b67c42','dark':'#31271f','light':'#e9d7ad','iris':'#a4b958','pattern':'rosettes','grain':'short','phase':.33,'density':4,'mark':'none'},
 'domestic_maine_coon':{'base':'#766153','dark':'#292a2d','light':'#dacdb2','iris':'#b3bb75','pattern':'mackerel','grain':'long','phase':.2,'density':5,'mark':'bib'},
 'domestic_sphynx':{'base':'#c29d96','dark':'#746774','light':'#edd3c1','iris':'#94b897','pattern':'skin','grain':'skin','phase':.32,'density':5,'mark':'none'},
 'fantasy_obsidian_rainbow':{'base':'#0b121d','dark':'#040812','light':'#b8cee3','iris':'#59e6d5','pattern':'aurora','grain':'ink','phase':.4,'density':6,'mark':'gold'}
}
# Authored, staggered open rosettes: centerT,centerH,radiusT,radiusH,rotation,opening.
ROSETTES=((.16,.37,.07,.12,-.3,.4),(.31,.55,.085,.15,.3,2.3),(.48,.37,.075,.13,-.2,4.1),
          (.65,.56,.085,.15,.4,1.7),(.82,.38,.07,.13,-.3,5.3),(.23,.81,.07,.11,.2,3.1),
          (.49,.83,.08,.12,-.4,.7),(.77,.83,.075,.11,.3,4.3))

def rosette_mask(t,h,x=.0):
    """Broken annuli with an actual open center; not a sinusoidal stripe field."""
    best=None
    for ct,ch,rt,rh,rot,opening in ROSETTES:
        ct+=.018*math.sin(x*3+ch*9)
        dx=(t-ct)/rt; dy=(h-ch)/rh
        qx=dx*math.cos(rot)-dy*math.sin(rot); qy=dx*math.sin(rot)+dy*math.cos(rot)
        d=math.hypot(qx,qy); a=math.atan2(qy,qx)
        broken=math.cos(a-opening)>.92
        if .69<d<1.06 and not broken: return 'rim'
        if .35<d<.69: best='copper'
        elif d<=.35: best='center'
    return best or 'coat'

def model_sources():
    facts=B.read_json(ROOT/'uv_models.json'); cfg=B.read_json(ROOT/'representatives.json')
    out={}
    for r in cfg['entries']:
        name=r['id'].split(':')[1]; path=ROOT/'geometry_source'/(r['geometryProfile']+'.geo.json')
        m=B.bedrock_model(path,r['geometryProfile'])
        source_cubes=[c for b in m['geometry']['minecraft:geometry'][0]['bones'] for c in b.get('cubes',[])]
        for q,c in zip(m['cubes'],source_cubes): q['region']=c.get('paintRegion',q['region'])
        clean=copy.deepcopy(m['geometry'])
        for b in clean['minecraft:geometry'][0]['bones']:
            for c in b.get('cubes',[]): c.pop('paintRegion',None)
        m['geometry']=clean
        out[name]={'adult':facts['adult'],'baby':facts['baby'],'bedrock':m}
    if set(out)!=set(STYLES): raise ValueError('Exactly four selected coats required')
    return cfg,out

def coat_color(name,region,face,x,h,t):
    s=STYLES[name]; base,dark,light=map(B.color,(s['base'],s['dark'],s['light']))
    if name=='domestic_bengal':
        c=B.mix(base,light,max(0,.32-h)*1.8)
        if region in ('body','ruff'):
            tag=rosette_mask(t,h,x)
            if tag=='rim': c=dark
            elif tag=='copper': c=(155,91,43)
            elif tag=='center': c=(208,154,83)
            if h>.91 and abs(x-.5)<.17: c=B.mix(c,dark,.65)
        elif region=='tail':
            if abs(math.sin((t+h*.2)*13))>.87: c=dark
        elif region=='head':
            if face!='north' and abs(math.sin(t*13+h*4))>.93: c=B.mix(c,dark,.8)
        elif region=='leg' and h>.3 and abs(math.sin(h*14+t*2))>.94: c=B.mix(c,dark,.7)
        return c
    if name=='domestic_maine_coon':
        c=B.mix(base,light,max(0,.35-h)*.8)
        if region=='ruff' or (region=='body' and t<.25 and h<.7): c=B.mix(light,base,.16+.2*h)
        if region in ('body','head','tail'):
            wave=math.sin(t*19+.9*math.sin(h*5)+.4*math.sin(x*7))
            if abs(wave)>.86 and h>.22: c=B.mix(c,dark,.87)
        # Long overlapping tapered fur strokes with light tips, never random pixels.
        strand=math.sin(t*52+2*math.sin(h*17+x*3))
        if strand>.75: c=B.mix(c,light,.13)
        elif strand<-.8: c=B.mix(c,dark,.13)
        if region=='ear_tuft': c=B.mix(base,dark,.75)
        return c
    if name=='domestic_sphynx':
        c=B.mix(base,light,max(0,.5-h)*.48)
        # Fold sites are localized to brow/neck/ankle; belly is not striped.
        fold=100.
        if region=='head':
            for hh in (.64,.78,.9): fold=min(fold,abs(h-hh-.035*math.sin(x*11)))
        elif region=='body' and t<.27:
            for hh in (.32,.53,.72): fold=min(fold,abs(h-hh-.04*math.sin(t*18)))
        elif region=='leg' and h<.3: fold=abs(h-.17-.025*math.sin(t*9))
        if fold<.015: c=B.mix(c,dark,.37)
        elif .015<=fold<.027: c=B.mix(c,light,.5)
        if region=='head' and face!='north': c=B.mix(c,dark,.15)
        return c
    # Prismatic ink stays concentrated on actual flowing anatomy, matching rat direction.
    tag=B.fantasy_marking(s,x,h,t,region)
    if tag=='rainbow':
        return B.mix(B.rainbow(t*.9+h*.21),B.rainbow(t*.9+h*.21+.18),.18)
    if tag=='gold': return (218,177,70)
    if tag=='crystal' or region=='crystal': return B.mix((77,224,235),(185,100,241),t)
    c=B.mix(base,(36,49,69),.13*max(0,math.sin(t*10+h*5)))
    return c

def sample(name,cube,face,u,v,axis):
    x,h,t=B.canonical(cube,face,u,v,axis); region=cube['region']; s=STYLES[name]
    c=coat_color(name,region,face,x,h,t); dark=B.color(s['dark']); light=B.color(s['light'])
    fantasy=name.startswith('fantasy_')
    if region.startswith('ear') and .18<x<.84 and .12<h<.78:
        c=B.mix(c,B.rainbow(h*.5) if fantasy else (178,119,126),.42)
    if region in ('muzzle','nose'):
        c=B.mix(B.color(s['base']),light,.55 if name!='domestic_sphynx' else .16)
        if face=='north' and abs(x-.5)<.16 and .45<h<.85: c=(63,34,70) if fantasy else (132,88,89)
        if face=='north' and abs(x-.5)<.035 and h<.45: c=dark
    if region=='head' and face=='north':
        for center in (.23,.77):
            eye=((x-center)/.095)**2+((h-.61)/.105)**2
            if eye<1.2: c=dark
            if eye<.76: c=B.color(s['iris'])
            if eye<.7 and abs(x-center)<.018: c=(12,18,24)
            if ((x-(center-.025))/.018)**2+((h-.65)/.022)**2<1: c=(225,238,207)
        if name=='domestic_bengal' and (.19<x<.26 or .74<x<.81) and .2<h<.48: c=B.mix(dark,c,.2)
        if name=='domestic_maine_coon' and h<.26: c=B.mix(c,light,.64)
        if h<.28 and abs(x-.5)<.12: c=(61,30,75) if fantasy else (139,94,94)
    return (*c,255)

def paint(name,model,scale=4):
    if type(scale) is not int or scale not in (1,4): raise ValueError('Only compatibility1 or detail4 scale')
    width,height=model['width']*scale,model['height']*scale
    pixels=bytearray(width*height*4); count=0
    for c in model['cubes']:
        B.validate_cube(c,model['width'],model['height'])
        for face,(u,v,w,h) in B.face_rects(c['uv'],c['size']).items():
            for y in range(math.floor(v*scale),math.ceil((v+h)*scale)):
                for x in range(math.floor(u*scale),math.ceil((u+w)*scale)):
                    a=max(0,min(1,((x+.5)/scale-u)/w)); b=max(0,min(1,((y+.5)/scale-v)/h))
                    pixels[(y*width+x)*4:(y*width+x)*4+4]=bytes(sample(name,c,face,a,b,model['axis']));count+=1
    return width,height,bytes(pixels),count
