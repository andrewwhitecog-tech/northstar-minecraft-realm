"""Pinned public runtime preparation. No download runs at import time."""
from __future__ import annotations
import concurrent.futures, hashlib, json, os, platform, re, shutil, threading, time, urllib.parse, urllib.request, zipfile
from pathlib import Path
HOME=Path(__file__).resolve().parent
ALLOWED_HOSTS={'piston-data.mojang.com','piston-meta.mojang.com','libraries.minecraft.net','resources.download.minecraft.net','maven.fabricmc.net','cdn.modrinth.com'}

def require(ok,why):
    if not ok:raise RuntimeError(why)

def file_hash(path,algorithm='sha256'):
    h=hashlib.new(algorithm)
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def safe_child(root,relative):
    p=Path(relative)
    require(not p.is_absolute() and '..' not in p.parts,'Unsafe public artifact path')
    out=(root/p).resolve();require(out.is_relative_to(root.resolve()),'Public artifact escaped runtime root');return out

def rules_allow(row,features=None):
    rules=row.get('rules');features=features or {}
    if not rules:return True
    allow=False
    for rule in rules:
        spec=rule.get('os',{});match=True
        if spec.get('name') and spec['name']!='linux':match=False
        if spec.get('arch') and re.search(spec['arch'],'x86_64') is None:match=False
        if spec.get('version') and re.search(spec['version'],platform.release()) is None:match=False
        if any(features.get(k,False)!=v for k,v in rule.get('features',{}).items()):match=False
        if match:allow=rule['action']=='allow'
    return allow

def arguments(rows,values,features):
    out=[]
    for row in rows:
        if isinstance(row,dict):
            if not rules_allow(row,features):continue
            row=row['value']
        for item in row if isinstance(row,list) else [row]:
            for k,v in values.items():item=item.replace(chr(36)+'{'+k+'}',str(v))
            require(chr(36)+'{' not in item,'Unknown official launch placeholder: '+item)
            out.append(item)
    return out

class Downloader:
    def __init__(self,root,limits):self.root=root;self.deadline=time.monotonic()+limits['downloadSeconds'];self.maximum=limits['maxDownloadedBytes'];self.total=0;self.mutex=threading.Lock()
    def get(self,url,path,hashes,expected_size=None):
        u=urllib.parse.urlparse(url);require(u.scheme=='https' and u.hostname in ALLOWED_HOSTS and not u.username and not u.password,'Non-approved public origin')
        path=Path(path);require(path.resolve().is_relative_to(self.root.resolve()),'Download escaped owned runtime');path.parent.mkdir(parents=True,exist_ok=True)
        require(not path.exists(),'Runtime must be fresh; no paid/shared cache reuse')
        require(time.monotonic()<self.deadline,'Public download deadline expired')
        count=0;hs={a:hashlib.new(a) for a in hashes};temporary=path.with_suffix(path.suffix+'.part')
        request=urllib.request.Request(url,headers={'User-Agent':'NorthStar-public-held-dig-calibration/1'})
        with urllib.request.urlopen(request,timeout=30) as response,temporary.open('xb') as out:
            final=urllib.parse.urlparse(response.geturl());require(final.scheme=='https' and final.hostname in ALLOWED_HOSTS,'Unapproved download redirect')
            while True:
                require(time.monotonic()<self.deadline,'Public download deadline expired')
                block=response.read(1024*1024)
                if not block:break
                count+=len(block);require(count<=80*1024*1024,'Per-file download bound')
                with self.mutex:self.total+=len(block);require(self.total<=self.maximum,'Aggregate download bound')
                for h in hs.values():h.update(block)
                out.write(block)
        if expected_size is not None:require(count==expected_size,'Public artifact size mismatch')
        require(all(hs[a].hexdigest().lower()==v.lower() for a,v in hashes.items()),'Public artifact hash mismatch')
        temporary.replace(path);return path

def gav_path(name):
    bits=name.split(':');require(3<=len(bits)<=4,'Unsupported official Maven coordinate')
    group,artifact,version=bits[:3];suffix='-'+bits[3] if len(bits)==4 else ''
    require(all(re.fullmatch(r'[A-Za-z0-9_.+\-]+',b) for b in bits),'Unsafe Maven coordinate')
    return group.replace('.','/')+'/'+artifact+'/'+version+'/'+artifact+'-'+version+suffix+'.jar'

def prepare(stage,lock):
    stage.mkdir(parents=True,exist_ok=False)
    for n,pin in lock['metadata'].items():require(file_hash(HOME/'metadata'/n)==pin['sha256'],'Pinned public metadata drift: '+n)
    meta=json.loads((HOME/'metadata/minecraft-26.3.json').read_text())
    client_profile=json.loads((HOME/'metadata/fabric-client-0.20.1.json').read_text())
    server_profile=json.loads((HOME/'metadata/fabric-server-0.20.1.json').read_text())
    require(meta['id']=='26.3' and meta['javaVersion']['majorVersion']==25,'Wrong vanilla runtime')
    require(client_profile['mainClass']=='net.fabricmc.loader.impl.launch.knot.KnotClient','Unexpected official Fabric client entrypoint')
    require(server_profile['mainClass']=='net.fabricmc.loader.impl.launch.knot.KnotServer','Unexpected official Fabric server entrypoint')
    d=Downloader(stage,lock['limits']);client_libraries=[];fabric_libraries=[]
    for lib in meta['libraries']:
        if not rules_allow(lib):continue
        require('classifiers' not in lib.get('downloads',{}),'Legacy native-classifier metadata requires explicit review')
        a=lib['downloads']['artifact'];target=safe_child(stage/'libraries',a['path'])
        d.get(a['url'],target,{'sha1':a['sha1']},a['size']);client_libraries.append(str(target))
    by_name={}
    for profile in (client_profile,server_profile):
        for lib in profile['libraries']:
            if lib['name'] in by_name:require(by_name[lib['name']]==lib,'Conflicting official Fabric dependency')
            by_name[lib['name']]=lib
    for name,lib in by_name.items():
        relative=gav_path(name);hashes={'sha256':lib.get('sha256') or lock['loaderSha256']}
        require(lib.get('sha256') or name=='net.fabricmc:fabric-loader:0.20.1','Unpinned Fabric library')
        target=safe_child(stage/'fabric-libraries',relative)
        d.get(lib['url'].rstrip('/')+'/'+relative,target,hashes,lib.get('size'));fabric_libraries.append(str(target))
    client=meta['downloads']['client'];client_jar=d.get(client['url'],stage/'client.jar',{'sha1':client['sha1']},client['size'])
    transport=json.loads((HOME/'metadata/server-transport.json').read_text())
    require(transport['outer']['sha1']==meta['downloads']['server']['sha1'],'Server bundle differs from exact client version')
    outer=transport['outer'];bundle=d.get(outer['url'],stage/'server-bundle.jar',{'sha1':outer['sha1'],'sha256':outer['sha256']},outer['size']);server_libraries=[]
    with zipfile.ZipFile(bundle) as z:
        require(len(z.namelist())==len(set(z.namelist())),'Duplicate server ZIP entry')
        for row in transport['classpath_members']:
            target=safe_child(stage/'server-libraries',row['relative']);info=z.getinfo(row['member'])
            require(info.file_size==row['bytes'],'Server member size drift');target.parent.mkdir(parents=True,exist_ok=True)
            with z.open(info) as src,target.open('xb') as out:shutil.copyfileobj(src,out,1024*1024)
            require(file_hash(target)==row['sha256'],'Server member hash drift');server_libraries.append(str(target))
    mods={}
    for mod in lock['mods']:
        p=d.get(mod['url'],stage/'mods'/mod['filename'],mod['hashes'],mod['size']);mods[mod['version']]=str(p)
    assets=stage/'assets';(assets/'indexes').mkdir(parents=True)
    index=HOME/'metadata/assets-34.json';require(file_hash(index,'sha1')==meta['assetIndex']['sha1'],'Official asset index hash drift')
    shutil.copyfile(index,assets/'indexes/34.json');objects=json.loads(index.read_text())['objects'];require(len(objects)<=lock['limits']['maxAssetObjects'],'Asset object bound')
    unique={x['hash']:x['size'] for x in objects.values()}
    def get_asset(pair):
        h,size=pair;require(re.fullmatch('[0-9a-f]{40}',h) is not None,'Unsafe asset hash')
        return d.get('https://resources.download.minecraft.net/'+h[:2]+'/'+h,assets/'objects'/h[:2]/h,{'sha1':h},size)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:list(pool.map(get_asset,unique.items()))
    natives=stage/'natives';(natives/'java').mkdir(parents=True)
    for p in client_libraries:
        if 'natives-linux' not in p:continue
        with zipfile.ZipFile(p) as z:
            for info in z.infolist():
                if '.so' not in info.filename or info.is_dir():continue
                target=safe_child(natives/'java',Path(info.filename).name);data=z.read(info)
                if target.exists():require(target.read_bytes()==data,'Conflicting native library')
                else:target.write_bytes(data)
    return {'client_classpath':os.pathsep.join([*fabric_libraries,*client_libraries,str(client_jar)]),
            'server_classpath':os.pathsep.join([*fabric_libraries,*server_libraries]),'client_profile':client_profile,
            'server_profile':server_profile,'meta':meta,'assets':str(assets),'natives':str(natives),'mods':mods,'downloaded_bytes':d.total,'asset_objects':len(unique)}
