"""Small strict readers for the OWN generated calibration world, not a world writer."""
import gzip, io, math, struct, zlib
from pathlib import Path

class Nbt:
    def __init__(self,data):self.f=io.BytesIO(data)
    def read(self,n):
        b=self.f.read(n)
        if len(b)!=n:raise ValueError('Truncated NBT')
        return b
    def number(self,fmt):return struct.unpack('>'+fmt,self.read(struct.calcsize('>'+fmt)))[0]
    def text(self):return self.read(self.number('H')).decode('utf-8')
    def size(self):
        n=self.number('i')
        if not 0<=n<=10000000:raise ValueError('NBT collection bound')
        return n
    def payload(self,t):
        if t in (1,2,3,4,5,6):return self.number({1:'b',2:'h',3:'i',4:'q',5:'f',6:'d'}[t])
        if t==7:return self.read(self.size())
        if t==8:return self.text()
        if t==9:
            child=self.number('B');return [self.payload(child) for _ in range(self.size())]
        if t==10:
            result={}
            while True:
                child=self.number('B')
                if child==0:return result
                name=self.text()
                if name in result:raise ValueError('Duplicate NBT key')
                result[name]=self.payload(child)
        if t in (11,12):return [self.number('i' if t==11 else 'q') for _ in range(self.size())]
        raise ValueError('Unsupported NBT tag '+str(t))
    def root(self):
        if self.number('B')!=10:raise ValueError('NBT root is not compound')
        self.text();return self.payload(10)

def read_dat(path):
    raw=Path(path).read_bytes()
    if raw[:2]==b'\x1f\x8b':raw=gzip.decompress(raw)
    return Nbt(raw).root()

def block_state(world,x,y,z):
    folder=Path(world)/'dimensions/minecraft/overworld/region'
    p=folder/f'r.{x//512}.{z//512}.mca'
    with p.open('rb') as f:
        index=(x//16%32)+(z//16%32)*32;f.seek(index*4);entry=f.read(4)
        if len(entry)!=4:raise ValueError('Missing region header')
        offset=int.from_bytes(entry[:3],'big')
        if offset<2 or entry[3]==0:raise ValueError('Missing saved fixture chunk')
        f.seek(offset*4096);size=struct.unpack('>I',f.read(4))[0]
        if not 1<size<=entry[3]*4096-4:raise ValueError('Saved chunk size invalid')
        compression=f.read(1)[0];raw=f.read(size-1)
    if compression&128:raise ValueError('External MCA chunk unsupported in tiny flat fixture')
    if compression==1:raw=gzip.decompress(raw)
    elif compression==2:raw=zlib.decompress(raw)
    elif compression!=3:raise ValueError('Unsupported actual MCA compression '+str(compression))
    root=Nbt(raw).root()
    for section in root.get('sections',[]):
        if section['Y']!=y//16:continue
        states=section.get('block_states')
        if states is None:raise ValueError('No saved block state palette')
        palette=states['palette']
        if len(palette)==1:return palette[0]
        bits=max(4,(len(palette)-1).bit_length());per_long=64//bits;at=(y%16)*256+(z%16)*16+(x%16)
        value=states['data'][at//per_long]&((1<<64)-1);pi=(value>>((at%per_long)*bits))&((1<<bits)-1)
        if pi>=len(palette):raise ValueError('Saved palette index invalid')
        return palette[pi]
    raise ValueError('Saved fixture section absent')

def fresh_servers_dat(path,address):
    def text(s):
        b=s.encode();return struct.pack('>H',len(b))+b
    def field(t,n,payload):return bytes([t])+text(n)+payload
    server=field(8,'name',text('Owned cloud calibration'))+field(8,'ip',text(address))+field(1,'acceptTextures',b'\0')+b'\0'
    raw=b'\x0a\0\0'+field(9,'servers',b'\x0a'+struct.pack('>i',1)+server)+b'\0'
    # ServerList.load uses NbtIo.read(Path): servers.dat is uncompressed NBT.
    Path(path).write_bytes(raw)
