from __future__ import annotations
import argparse, hashlib, json, math, pathlib, re, shutil, zipfile

POWDER = '*[custom_data~{nsp_chain:"black_powder"}]'
FORMAT = 121

def valid(config):
    if not isinstance(config, dict): raise ValueError('config must be an object')
    dim = config.get('dimension')
    if dim not in ('minecraft:overworld','minecraft:the_nether','minecraft:the_end','nsp:legacy'): raise ValueError('unsupported dimension')
    lo,hi=config['site']['min'],config['site']['max']
    if len(lo)!=3 or len(hi)!=3 or any(type(v) is not int for v in lo+hi): raise ValueError('integer site bounds required')
    if any(a>=b or b-a>512 for a,b in zip(lo,hi)): raise ValueError('invalid or oversized site')
    if not -64<=lo[1]<hi[1]<=319: raise ValueError('height out of range')
    guns=config['guns']
    if not 1<=len(guns)<=8: raise ValueError('1..8 cannons required')
    ids=set()
    for g in guns:
        ident=g['id']
        if not re.fullmatch('[a-z][a-z0-9_]{0,15}',ident) or ident in ids: raise ValueError('unique safe cannon id required')
        ids.add(ident)
        for key in ['pivot','breech']:
            p=g[key]
            if len(p)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in p): raise ValueError('finite position required')
            if any(not a+3<=v<=b-3 for v,a,b in zip(p,lo,hi)): raise ValueError('fixture needs three-block site margin')
        if any(type(v) is not int for v in g['breech']): raise ValueError('integer breech required')
        for key,default,cap in [('muzzle_distance',2.5,16),('muzzle_height',1.2,12)]:
            val=g.get(key,default)
            if type(val) not in (float,int) or not math.isfinite(val) or not 0<=val<=cap: raise ValueError('invalid muzzle offset')

        if type(g.get('yaw',0)) is not int or g.get('yaw',0) not in range(-180,181): raise ValueError('integer yaw -180..180 required')
        for action,p in g.get('controls',{}).items():
            if action not in ('load','left','right','elevation','fire') or len(p)!=3 or any(type(v) is not int for v in p): raise ValueError('invalid control')
            if any(not a+1<=v<=b-1 for v,a,b in zip(p,lo,hi)): raise ValueError('control outside site')
    if len({tuple(g['breech']) for g in guns})!=len(guns): raise ValueError('shared breech refused')
    if any(not -29999984<=v<=29999984 for v in [lo[0],hi[0],lo[2],hi[2]]): raise ValueError('horizontal bounds exceeded')
    return config

def build(config, output):
    config=valid(config); out=pathlib.Path(output)
    if out.exists() and any(out.iterdir()): raise ValueError('output must be absent or empty; preserve earlier passes')
    out.mkdir(parents=True,exist_ok=True)
    funcs={}; jsons={}
    def fn(name, lines):
        funcs[name]='\n'.join(lines)+'\n'
    def js(name,obj):jsons[name]=obj
    lo,hi=config['site']['min'],config['site']['max']; dim=config['dimension']
    box=','.join([f'x={lo[0]}',f'y={lo[1]}',f'z={lo[2]}',f'dx={hi[0]-lo[0]}',f'dy={hi[1]-lo[1]}',f'dz={hi[2]-lo[2]}'])
    allguns='@e[type=minecraft:marker,tag=nsp_ck.gun,'+box+']'
    shells='@e[type=minecraft:marker,tag=nsp_ck.shell,'+box+']'
    objectives=['ck_ld','ck_cd','ck_aim','ck_hi','ck_gen','ck_age','ck_x','ck_y','ck_z','ck_vx','ck_vy','ck_vz','ck_hp','ck_stat','ck_tmp','ck_role','ck_b0','ck_b1','ck_b2','ck_b3','ck_b4']
    fn('load',[f'scoreboard objectives add {n} dummy' for n in objectives]+[
        'execute unless score #epoch ck_stat matches -2147483648..2147483647 run scoreboard players set #epoch ck_stat 0',
        'scoreboard players add #epoch ck_stat 1',
        'scoreboard players set #awake ck_stat 0',
        'scoreboard players set #g ck_stat 5',
        'execute if data storage nsp_ck:config {schema:1,installed:1b} run function nsp_ck:init',
    ])
    fn('install',[
        'data merge storage nsp_ck:config {schema:1,installed:1b}',
        'function nsp_ck:init',
    ])
    init=[]
    for idx,g in enumerate(config['guns']):
        ident=g['id']; p=' '.join(str(v) for v in g['pivot'])
        selector=f'@e[type=minecraft:marker,tag=nsp_ck.g.{ident},distance=..1]'
        init.append(f'execute in {dim} positioned {p} unless entity {selector} run summon minecraft:marker ~ ~ ~ {{Tags:["nsp_ck.gun","nsp_ck.g.{ident}"]}}')
        init.append(f'execute in {dim} positioned {p} as {selector} run function nsp_ck:g/{ident}/defaults')
        fn(f'g/{ident}/defaults',[
            f'execute unless score @s {n} matches -2147483648..2147483647 run scoreboard players set @s {n} {v}'
            for n,v in [('ck_ld',0),('ck_cd',0),('ck_aim',3),('ck_hi',0)]
        ])
    fn('init',init)
    fn('tick',[
        'execute unless data storage nsp_ck:config {schema:1,installed:1b} run return 0',
        f'execute in {dim} if entity @a[{box}] run function nsp_ck:active',
        f'execute in {dim} unless entity @a[{box}] if score #awake ck_stat matches 1 run function nsp_ck:sleep',
    ])
    active=[
        'execute if score #awake ck_stat matches 0 run scoreboard players add #epoch ck_stat 1',
        'scoreboard players set #awake ck_stat 1',
        f'execute as {allguns} at @s if score @s ck_cd matches 1 run function nsp_ck:ready',
        f'execute as {allguns} if score @s ck_cd matches 2.. run scoreboard players remove @s ck_cd 1',
        f'execute as {shells} unless score @s ck_gen = #epoch ck_stat run kill @s',
        f'execute as {shells} at @s run function nsp_ck:shell/tick',
    ]
    fn('active',active)
    fn('ready',['scoreboard players set @s ck_cd 0','function #nsp_ck:on_ready'])
    fn('sleep',['scoreboard players add #epoch ck_stat 1','scoreboard players set #awake ck_stat 0',f'kill {shells}'])
    fn('api/register_target',[
        f'execute unless dimension {dim} run return 0',
        'execute unless data storage nsp_ck:config {schema:1,installed:1b} run return 0',
        f'execute unless entity @s[{box}] run return 0',
        'execute if entity @s[type=minecraft:player] run return 0',
        'execute if entity @s[type=minecraft:drowned] run return run function nsp_ck:target/register_mob',
        'execute if entity @s[type=minecraft:skeleton] run return run function nsp_ck:target/register_mob',
        'execute if entity @s[type=minecraft:marker,tag=nsp_ck.ship_anchor] run return run function nsp_ck:target/register_anchor',
        'return 0',
    ])
    fn('target/register_mob',['tag @s add nsp_ck.target','scoreboard players set @s ck_role 1'])
    fn('target/register_anchor',['tag @s add nsp_ck.target','scoreboard players set @s ck_role 2','execute unless score @s ck_hp matches 1.. run scoreboard players set @s ck_hp 40'])
    fn('api/unregister_target',['tag @s remove nsp_ck.target','scoreboard players reset @s ck_role'])
    fn('shell/tick',[
        'scoreboard players add @s ck_age 1',
        'execute if score @s ck_age matches 81.. run return run function nsp_ck:shell/end',
        'function nsp_ck:shell/step',
        'execute if entity @s run function nsp_ck:shell/step',
        'execute if entity @s run function nsp_ck:shell/step',
        'execute if entity @s run function nsp_ck:shell/step',
    ])
    solid_allow=['minecraft:air','minecraft:cave_air','minecraft:void_air','minecraft:water','minecraft:bubble_column']
    # Per-substep bounded movement; every hit path independently checks its actual entity type.
    step=[
        'scoreboard players operation @s ck_x += @s ck_vx',
        'scoreboard players operation @s ck_y += @s ck_vy',
        'scoreboard players operation @s ck_z += @s ck_vz',
        'scoreboard players operation @s ck_vy -= #g ck_stat',
        'execute store result storage nsp_ck:step x double 0.001 run scoreboard players get @s ck_x',
        'execute store result storage nsp_ck:step y double 0.001 run scoreboard players get @s ck_y',
        'execute store result storage nsp_ck:step z double 0.001 run scoreboard players get @s ck_z',
        'function nsp_ck:shell/move with storage nsp_ck:step',
        'execute at @s run function nsp_ck:shell/check',
    ]
    fn('shell/step',['execute if score @s ck_age matches 81.. run return 0']+step)
    fn('shell/move',['$tp @s $(x) $(y) $(z)'])
    checks=[f'execute unless entity @s[{box}] run return run function nsp_ck:shell/discard',
        'execute unless loaded ~ ~ ~ run return run function nsp_ck:shell/discard',
        'scoreboard players set #clear ck_tmp 0',
    ]
    checks += [f'execute if block ~ ~ ~ {block} run scoreboard players set #clear ck_tmp 1' for block in solid_allow]
    checks += ['execute if score #clear ck_tmp matches 0 run return run function nsp_ck:shell/end',
        'particle minecraft:crit ~ ~ ~ 0 0 0 0 1 force @a[distance=..96]',
        f'execute if entity @e[type=minecraft:marker,tag=nsp_ck.target,tag=nsp_ck.ship_anchor,scores={{ck_role=2}},distance=..1.1,limit=1] run return run function nsp_ck:hit/anchor',
        'execute positioned ~ ~-0.9 ~ if entity @e[type=minecraft:drowned,tag=nsp_ck.target,scores={ck_role=1},distance=..0.95,limit=1] run return run function nsp_ck:hit/drowned',
        'execute positioned ~ ~-0.9 ~ if entity @e[type=minecraft:skeleton,tag=nsp_ck.target,scores={ck_role=1},distance=..0.95,limit=1] run return run function nsp_ck:hit/skeleton',
    ]
    fn('shell/discard',['scoreboard players set @s ck_age 100000','kill @s'])
    fn('shell/check',checks)
    for typ in ['drowned','skeleton']:
        fn('hit/'+typ,[
            f'execute as @e[type=minecraft:{typ},tag=nsp_ck.target,scores={{ck_role=1}},distance=..0.95,sort=nearest,limit=1] run function nsp_ck:target/damage',
            'function nsp_ck:shell/end',
        ])
    fn('hit/anchor',[
        'execute as @e[type=minecraft:marker,tag=nsp_ck.target,tag=nsp_ck.ship_anchor,scores={ck_role=2},distance=..1.1,sort=nearest,limit=1] run function nsp_ck:target/anchor_hit',
        'function nsp_ck:shell/end',
    ])
    fn('target/damage',[
        f'execute unless dimension {dim} run return 0',
        f'execute unless entity @s[{box}] run return 0',
        'execute if entity @s[type=minecraft:player] run return 0',
        'execute unless entity @s[tag=nsp_ck.target,scores={ck_role=1}] run return 0',
        'execute unless entity @s[type=minecraft:drowned] unless entity @s[type=minecraft:skeleton] run return 0',
        'execute if entity @s[type=minecraft:drowned,tag=nsp_ck.target,scores={ck_role=1}] run damage @s 8 minecraft:magic',
        'execute if entity @s[type=minecraft:skeleton,tag=nsp_ck.target,scores={ck_role=1}] run damage @s 8 minecraft:magic',
        'scoreboard players add #hits ck_stat 1',
        'function #nsp_ck:on_hit',
    ])
    fn('target/anchor_hit',[
        f'execute unless dimension {dim} run return 0',
        f'execute unless entity @s[{box}] run return 0',
        'execute unless entity @s[type=minecraft:marker,tag=nsp_ck.target,tag=nsp_ck.ship_anchor,scores={ck_role=2}] run return 0',
        'scoreboard players remove @s ck_hp 8',
        'scoreboard players add #hits ck_stat 1',
        'function #nsp_ck:on_hit',
    ])
    fn('shell/end',[
        'scoreboard players set @s ck_age 100000',
        'particle minecraft:splash ~ ~ ~ 0.2 0.1 0.2 0.05 8 force @a[distance=..96]',
        'playsound minecraft:entity.generic.splash master @a[distance=..64] ~ ~ ~ 0.3 0.8',
        'kill @s',
    ])
    for g in config['guns']:
        ident=g['id']; bx,by,bz=g['breech']; gx,gy,gz=g['pivot']; prefix=f'g/{ident}'
        sel=f'@e[type=minecraft:marker,tag=nsp_ck.g.{ident},{box},limit=1]'
        # Entry functions retain exactly one marker context; multiple controllers fail closed.
        for action in ['load','fire','left','right','elevation']:
            fn(f'api/{ident}/{action}',[
                'execute unless data storage nsp_ck:config {schema:1,installed:1b} run return 0',
                f'execute in {dim} positioned {gx} {gy} {gz} unless entity @a[distance=..6] run return 0',
                'scoreboard players set #controllers ck_tmp 0',
                f'execute in {dim} as @e[type=minecraft:marker,tag=nsp_ck.g.{ident},{box}] run scoreboard players add #controllers ck_tmp 1',
                'execute unless score #controllers ck_tmp matches 1 run return 0',
                f'execute in {dim} as {sel} at @s run function nsp_ck:{prefix}/{action}',
            ])
        fn(prefix+'/left',['execute if score @s ck_aim matches 1.. run scoreboard players remove @s ck_aim 1','function #nsp_ck:on_aim'])
        fn(prefix+'/right',['execute if score @s ck_aim matches ..5 run scoreboard players add @s ck_aim 1','function #nsp_ck:on_aim'])
        fn(prefix+'/elevation',['scoreboard players add @s ck_hi 1','execute if score @s ck_hi matches 2.. run scoreboard players set @s ck_hi 0','function #nsp_ck:on_aim'])
        fn(prefix+'/load',[
            'execute if score @s ck_cd matches 1.. run return 0',
            'execute if score @s ck_ld matches 1.. run return 0',
            f'execute unless block {bx} {by} {bz} minecraft:barrel run return 0',
            f'execute unless items block {bx} {by} {bz} container.* {POWDER} run return 0',
            f'execute unless items block {bx} {by} {bz} container.* minecraft:iron_ingot run return 0',
            f'data modify storage nsp_ck:txn before set from block {bx} {by} {bz} Items',
            'scoreboard players set #powder ck_tmp 0',
            'scoreboard players set #iron ck_tmp 0',
            f'execute store success score #powder ck_tmp run function nsp_ck:{prefix}/consume_powder',
            f'execute if score #powder ck_tmp matches 1 store success score #iron ck_tmp run function nsp_ck:{prefix}/consume_iron',
            f'execute unless score #iron ck_tmp matches 1 run data modify block {bx} {by} {bz} Items set from storage nsp_ck:txn before',
            'data remove storage nsp_ck:txn before',
            'execute unless score #iron ck_tmp matches 1 run return 0',
            'scoreboard players set @s ck_ld 1',
            'scoreboard players add #loads ck_stat 1',
            'function #nsp_ck:on_load',
            'playsound minecraft:block.iron_trapdoor.close master @a[distance=..16] ~ ~ ~ 0.6 0.7',
        ])
        for name,predicate in [('powder',POWDER),('iron','minecraft:iron_ingot')]:
            fn(prefix+'/consume_'+name,[f'execute if items block {bx} {by} {bz} container.{slot} {predicate} run return run item modify block {bx} {by} {bz} container.{slot} nsp_ck:decrement' for slot in range(27)]+['return 0'])
        fire=[
            'execute if score @s ck_cd matches 1.. run return 0',
            'execute unless score @s ck_ld matches 1 run return 0',
            'execute unless score @s ck_aim matches 0..6 run return 0',
            'execute unless score @s ck_hi matches 0..1 run return 0',
            'scoreboard players set @s ck_ld 0',
            'scoreboard players set @s ck_cd 120',
            'scoreboard players add #shots ck_stat 1',
        ]
        for aim in range(7):
            yaw=g.get('yaw',0)+(aim-3)*15
            for high in range(2):
                name=prefix+f'/launch_{aim}_{high}'
                fire.append(f'execute if score @s ck_aim matches {aim} if score @s ck_hi matches {high} run function nsp_ck:{name}')
                rad=math.radians(yaw); vx=round(-math.sin(rad)*500);vz=round(math.cos(rad)*500)
                distance=g.get('muzzle_distance',2.5); height=g.get('muzzle_height',1.2)
                mx=gx-math.sin(rad)*distance; mz=gz+math.cos(rad)*distance
                fn(name,[
                    f'summon minecraft:marker {mx:.6f} {gy+height:.6f} {mz:.6f} {{Tags:["nsp_ck.shell","nsp_ck.new"]}}',
                    f'execute as @e[type=minecraft:marker,tag=nsp_ck.new,{box}] run function nsp_ck:{name}_state',
                ])
                fn(name+'_state',[
                    'tag @s remove nsp_ck.new',
                    'scoreboard players operation @s ck_gen = #epoch ck_stat',
                    'scoreboard players set @s ck_age 0',
                    'execute store result score @s ck_x run data get entity @s Pos[0] 1000',
                    'execute store result score @s ck_y run data get entity @s Pos[1] 1000',
                    'execute store result score @s ck_z run data get entity @s Pos[2] 1000',
                    f'scoreboard players set @s ck_vx {vx}',
                    f'scoreboard players set @s ck_vy {375 if high else 125}',
                    f'scoreboard players set @s ck_vz {vz}',
                ])
        fire += ['playsound minecraft:entity.generic.explode master @a[distance=..64] ~ ~ ~ 0.7 0.65','particle minecraft:large_smoke ~ ~1.2 ~ 0.15 0.15 0.15 0.03 12 force @a[distance=..64]','function #nsp_ck:on_fire']
        fn(prefix+'/fire',fire)

    # Optional physical inputs use a rising-edge latch; the default pack never places blocks.
    for g in config['guns']:
        ident=g['id']; controls=g.get('controls',{})
        for i,action in enumerate(['load','left','right','elevation','fire']):
            if action not in controls: continue
            x,y,z=controls[action]
            p=f'{x} {y} {z}'
            funcs[f'g/{ident}/defaults']+=f'execute unless score @s ck_b{i} matches 0..1 run scoreboard players set @s ck_b{i} 0\n'
            funcs['active']+=f'execute as @e[type=minecraft:marker,tag=nsp_ck.g.{ident},{box}] at @s if entity @a[distance=..6] run function nsp_ck:g/{ident}/poll_{action}\n'
            fn(f'g/{ident}/poll_{action}',[
                f'execute unless block {p} minecraft:stone_button[powered=true] run scoreboard players set @s ck_b{i} 0',
                f'execute if block {p} minecraft:stone_button[powered=true] if score @s ck_b{i} matches 0 run function nsp_ck:g/{ident}/edge_{action}',
            ])
            fn(f'g/{ident}/edge_{action}',[f'scoreboard players set @s ck_b{i} 1',f'function nsp_ck:g/{ident}/{action}'])
    # The explicit demo is a new-copy instrument, never an install/adoption function.
    if config.get('demo_fixture',False):
        if len(config['guns'])!=1: raise ValueError('one demo gun only')
        g=config['guns'][0]; x,y,z=[math.floor(v) for v in g['pivot']]
        demo=[f'fill {x-10} {y-1} {z-10} {x+10} {y-1} {z+18} minecraft:polished_blackstone_bricks']
        demo += [f'setblock {x+dx} {y} {z+dz} minecraft:dark_oak_log[axis=z]' for dx in [-1,1] for dz in range(-1,5)]
        demo += [f'setblock {x+dx} {y+dy} {z+dz} minecraft:cut_copper' for dz in range(0,7) for dx,dy in [(-1,1),(1,1),(0,0),(0,2)]]
        demo += [f'setblock {x+dx} {y+dy} {z+7} minecraft:gold_block' for dx,dy in [(-1,1),(1,1),(0,0),(0,2)]]
        demo += [f'setblock {x+dx} {y} {z+dz} minecraft:polished_blackstone' for dx in [-2,2] for dz in [0,4]]
        demo += [f'setblock {" ".join(str(v) for v in g["breech"])} minecraft:barrel[facing=up]']
        demo += [f'setblock {" ".join(str(v) for v in p)} minecraft:stone_button[face=floor,facing=north,powered=false]' for p in g.get('controls',{}).values()]
        demo += ['function nsp_ck:install']
        fn('demo/build',demo)

    js('pack.mcmeta',{'pack':{'description':'NorthStar cannon kernel: scoped marker shots and genuine chain powder','min_format':[FORMAT,0],'max_format':[FORMAT,0]}})
    js('data/minecraft/tags/function/load.json',{'values':['nsp_ck:load']})
    js('data/minecraft/tags/function/tick.json',{'values':['nsp_ck:tick']})
    js('data/nsp_ck/item_modifier/decrement.json',{'type':'minecraft:set_count','count':-1,'add':True})
    for hook in ['on_fire','on_hit','on_aim','on_load','on_ready']:js(f'data/nsp_ck/tags/function/{hook}.json',{'values':[]})
    for name,body in funcs.items():
        p=out/'data/nsp_ck/function'/f'{name}.mcfunction';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(body,encoding='utf-8',newline='\n')
    for name,obj in jsons.items():
        p=out/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    manifest={'schema':1,'config':config,'functions':len(funcs),'files':{str(p.relative_to(out)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob('*')) if p.is_file()},'native_verified':False,'live_installed':False,'ammo_predicate':POWDER,'source_zip_sha256':'37aa12cc197259a9e3563f306a480a0f2cbf5152bd0b9aa4686832ef92306bda'}
    return manifest

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);ap.add_argument('--output',required=True);ap.add_argument('--receipt',required=True);a=ap.parse_args()
    result=build(json.loads(pathlib.Path(a.config).read_text(encoding='utf-8')),a.output)
    pathlib.Path(a.receipt).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'functions':result['functions'],'files':len(result['files']),'native_verified':False,'live_installed':False}))
