"""Portable CPU textured-triangle renderer. Produces real static geometry views, not native-game screenshots."""
import math
import struct
import zlib
from pathlib import Path
import baseline_paint as B

VIEWS=(('front',0,.16),('three_quarter',-.70,.21),('side',math.pi/2,.16),('back',math.pi,.16))

def decode_png(path):
    b=Path(path).read_bytes()
    if b[:8]!=b'\x89PNG\r\n\x1a\n': raise ValueError('PNG signature')
    pos=8; packed=b''; size=None; ended=False
    while pos<len(b):
        if pos+12>len(b): raise ValueError('Truncated chunk')
        n=struct.unpack('>I',b[pos:pos+4])[0]; kind=b[pos+4:pos+8]; d=b[pos+8:pos+8+n]
        if pos+12+n>len(b) or zlib.crc32(kind+d)&0xffffffff!=struct.unpack('>I',b[pos+8+n:pos+12+n])[0]: raise ValueError('PNG CRC/length')
        if kind==b'IHDR':
            w,h,depth,mode,cp,fi,inter=struct.unpack('>IIBBBBB',d)
            if (depth,mode,cp,fi,inter)!=(8,6,0,0,0) or not 1<=w<=1024 or not 1<=h<=1024: raise ValueError('Bounded RGBA8 PNG required')
            size=w,h
        elif kind==b'IDAT': packed+=d
        elif kind==b'IEND': ended=True
        pos+=12+n
    if not ended or pos!=len(b) or size is None: raise ValueError('Missing PNG data')
    w,h=size; decoder=zlib.decompressobj(); raw=decoder.decompress(packed,(w*4+1)*h+1)
    if not decoder.eof or decoder.unused_data or decoder.unconsumed_tail: raise ValueError('Unbounded/trailing PNG stream')
    if len(raw)!=(w*4+1)*h or any(raw[y*(w*4+1)]!=0 for y in range(h)): raise ValueError('Unsupported PNG rows')
    pixels=b''.join(raw[y*(w*4+1)+1:(y+1)*(w*4+1)] for y in range(h))
    return w,h,pixels

def rotate(p,angles,pivot=(0,0,0)):
    x,y,z=(p[i]-pivot[i] for i in range(3))
    for axis,degrees in enumerate(angles):
        a=math.radians(degrees); c,s=math.cos(a),math.sin(a)
        if axis==0: y,z=y*c-z*s,y*s+z*c
        elif axis==1: x,z=x*c+z*s,-x*s+z*c
        else: x,y=x*c-y*s,x*s+y*c
    return x+pivot[0],y+pivot[1],z+pivot[2]

def transform(p,c,m):
    if m['axis']=='java_down':
        q=rotate(p,c['rotation']); q=tuple(q[i]+c['pivot'][i] for i in range(3))
        return q[0],-q[1],q[2]
    q=rotate(p,c['rotation'],c['pivot'])
    for b in c.get('chain',[]): q=rotate(q,b['rotation'],b['pivot'])
    return q

def dot(a,b): return sum(x*y for x,y in zip(a,b))
def sub(a,b): return tuple(x-y for x,y in zip(a,b))
def normalized(a):
    n=math.sqrt(dot(a,a))
    if n<=1e-10: raise ValueError('Degenerate normal')
    return tuple(x/n for x in a)
def cross(a,b): return a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]

def triangles(model):
    result=[]
    for c in model['cubes']:
        for face,r in B.face_rects(c['uv'],c['size']).items():
            corners=[]
            for u,v in ((0,0),(1,0),(1,1),(0,1)):
                q=list(B.surface(face,u,v))
                if model['axis']=='java_down': q[1]=1-q[1]
                inf=c.get('inflate',0)
                p=transform(tuple(c['origin'][i]-inf+q[i]*(c['size'][i]+2*inf) for i in range(3)),c,model)
                corners.append((p,((r[0]+u*r[2])/model['width'],(r[1]+v*r[3])/model['height'])))
            n=normalized(cross(sub(corners[1][0],corners[0][0]),sub(corners[2][0],corners[0][0])))
            center=transform(tuple(c['origin'][i]+c['size'][i]/2 for i in range(3)),c,model)
            face_center=tuple(sum(p[0][i] for p in corners)/4 for i in range(3))
            if dot(n,sub(face_center,center))<0: n=tuple(-x for x in n)
            for ids in ((0,1,2),(0,2,3)): result.append({'vertices':[corners[i] for i in ids],'normal':n,'kind':'model'})
    return result

def camera(p,yaw,pitch):
    x,y,z=p; c,s=math.cos(yaw),math.sin(yaw); x,z=x*c+z*s,-x*s+z*c
    c,s=math.cos(pitch),math.sin(pitch)
    return x,y*c+z*s,-y*s+z*c

def render(model,texture_path,size=384,yaw=-.7,pitch=.21,material='fur'):
    if type(size) is not int or not 64<=size<=512: raise ValueError('View size64..512')
    tw,th,tex=decode_png(texture_path)
    if tw*model['height']!=th*model['width']: raise ValueError('Texture/model UV aspect mismatch')
    tris=triangles(model); points=[v[0] for t in tris for v in t['vertices']]
    if not points: raise ValueError('No actual geometry')
    floor=min(p[1] for p in points)-.02
    # Shadows are projected from the actual mesh, not a painted ellipse or still background.
    key=normalized((-.5,.9,-.65)); shadows=[]
    for t in tris:
        ps=[]
        for p,uv in t['vertices']:
            height=p[1]-floor
            ps.append(((p[0]-key[0]*height/key[1],floor+.008,p[2]-key[2]*height/key[1]),(0,0)))
        shadows.append({'vertices':ps,'normal':(0,1,0),'kind':'shadow'})
    radius=max(max(p[i] for p in points)-min(p[i] for p in points) for i in range(3))*1.2
    cx=(min(p[0] for p in points)+max(p[0] for p in points))/2
    cz=(min(p[2] for p in points)+max(p[2] for p in points))/2
    fp=[((cx-radius,floor,cz-radius),(0,0)),((cx+radius,floor,cz-radius),(0,0)),((cx+radius,floor,cz+radius),(0,0)),((cx-radius,floor,cz+radius),(0,0))]
    floor_tris=[{'vertices':[fp[i] for i in ids],'normal':(0,1,0),'kind':'floor'} for ids in ((0,1,2),(0,2,3))]
    camera_points=[camera(p,yaw,pitch) for p in points]
    lo=[min(p[i] for p in camera_points) for i in (0,1)]; hi=[max(p[i] for p in camera_points) for i in (0,1)]
    middle=[(lo[i]+hi[i])/2 for i in (0,1)]; zoom=(size*.78)/max(hi[i]-lo[i] for i in (0,1))
    pix=bytearray(size*size*4); depth=[math.inf]*(size*size); kinds=bytearray(size*size)
    for y in range(size):
        color=B.mix((12,18,31),(35,42,57),y/max(1,size-1))
        for x in range(size): pix[(y*size+x)*4:(y*size+x)*4+4]=bytes((*color,255))
    fill=normalized((.8,.25,.6)); view=normalized((math.sin(yaw),.2,-math.cos(yaw)))
    for tri in floor_tris+shadows+tris:
        projected=[]
        for p,uv in tri['vertices']:
            q=camera(p,yaw,pitch); projected.append(((q[0]-middle[0])*zoom+size/2,size/2-(q[1]-middle[1])*zoom,q[2],uv[0],uv[1]))
        a,b,c=projected
        area=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(area)<1e-7: continue
        x0=max(0,math.floor(min(p[0] for p in projected))); x1=min(size-1,math.ceil(max(p[0] for p in projected)))
        y0=max(0,math.floor(min(p[1] for p in projected))); y1=min(size-1,math.ceil(max(p[1] for p in projected)))
        n=tri['normal']; illumination=.23+.68*max(0,dot(n,key))+.20*max(0,dot(n,fill))
        half=normalized(tuple(key[i]+view[i] for i in range(3)))
        shine=max(0,dot(n,half))**(42 if material=='obsidian' else 12)
        for yy in range(y0,y1+1):
            for xx in range(x0,x1+1):
                px,py=xx+.5,yy+.5
                w0=((b[1]-c[1])*(px-c[0])+(c[0]-b[0])*(py-c[1]))/area
                w1=((c[1]-a[1])*(px-c[0])+(a[0]-c[0])*(py-c[1]))/area; w2=1-w0-w1
                if min(w0,w1,w2)<-1e-8: continue
                z=w0*a[2]+w1*b[2]+w2*c[2]; at=yy*size+xx
                if z>=depth[at]-1e-8: continue
                kind=tri['kind']
                if kind=='model':
                    u=w0*a[3]+w1*b[3]+w2*c[3]; v=w0*a[4]+w1*b[4]+w2*c[4]
                    tx=min(tw-1,max(0,int(u*tw))); ty=min(th-1,max(0,int(v*th))); ti=(ty*tw+tx)*4
                    if tex[ti+3]<128: continue
                    rgb=tuple(tex[ti+i] for i in range(3)); out=[]
                    for channel in rgb:
                        linear=(channel/255)**2.2*illumination+shine*(.035 if material!='obsidian' else .075)
                        out.append(round(max(0,min(1,linear))**(1/2.2)*255))
                    col=tuple(out); flag=3
                elif kind=='shadow': col=(28,32,41); flag=2
                else: col=(52,58,66); flag=1
                pix[at*4:at*4+4]=bytes((*col,255)); depth[at]=z; kinds[at]=flag
    visible=[depth[i] for i,k in enumerate(kinds) if k==3]
    if not visible: raise ValueError('Actual model rendered0pixels')
    return bytes(pix),{'modelPixels':len(visible),'modelTriangles':len(tris),'depthMin':min(visible),'depthMax':max(visible),'viewSize':size}

def sheet(model,texture_path,out,size=384,material='fur'):
    frames=[]; rows=[]
    for name,yaw,pitch in VIEWS:
        pixels,receipt=render(model,texture_path,size,yaw,pitch,material)
        frames.append(pixels);rows.append({'view':name,**receipt})
    width=size*2; pixels=bytearray(width*width*4)
    for i,frame in enumerate(frames):
        ox=(i%2)*size; oy=(i//2)*size
        for y in range(size): pixels[((oy+y)*width+ox)*4:((oy+y)*width+ox+size)*4]=frame[y*size*4:(y+1)*size*4]
    Path(out).write_bytes(B.png_bytes(width,width,bytes(pixels)))
    return {'views':rows,'width':width,'height':width,'textOverlays':False,'renderer':'CPU actual textured triangles with depth test; static authoring views, not native screenshots'}
