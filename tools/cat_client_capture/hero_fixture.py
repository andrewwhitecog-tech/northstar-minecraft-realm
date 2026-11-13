"""Bounded private hero fixture/camera plan. No subprocess, network or world action on import."""
PRESETS={
 'hero720':{'width':1280,'height':720,'fps':24,'maxFps':30,'status':'Requested qualification target; actual sustained cadence unproven'},
 'close800':{'width':800,'height':450,'fps':10,'maxFps':20,'status':'Existing proven resolution/rate, improved physical composition; not720p/24'},
}
CANARY='nsp_cat.instincts.canary'
PHASES=[
 {'label':'return','variant':'domestic_bengal','catX':44.5,'camera':[44.5,64.0,35.0,180,5],'cameraEnd':[33.8,64.0,35.0,180,5],'moveSeconds':2.4,'payoffTicks':72},
 {'label':'protected','variant':'fantasy_obsidian_rainbow','catX':34.5,'camera':[35.2,64.0,35.5,180,5],'cameraEnd':[35.8,64.0,35.5,180,5],'moveSeconds':2.4,'payoffTicks':72},
]
def preset(name):
 if name not in PRESETS:raise ValueError('Explicit reviewed hero720 or close800 preset required')
 return dict(PRESETS[name])
def build_habitat(cmd):
 # All coordinates belong only to the controller's fresh neutral flat test fixture.
 # Keep owner/cat/path corridor x30..46,z31..34 unobstructed; no collision or AI overrides.
 cmds=[
  'fill 24 64 28 52 64 40 minecraft:polished_blackstone',
  'fill 26 64 30 50 64 38 minecraft:chiseled_deepslate',
  'fill 30 64 31 47 64 34 minecraft:chiseled_quartz_block',
  'fill 24 65 28 52 69 28 minecraft:polished_blackstone_bricks',
  'fill 25 66 28 51 68 28 minecraft:amethyst_block',
  'fill 25 65 28 51 65 28 minecraft:gold_block',
  'fill 25 69 28 51 69 28 minecraft:gold_block',
  'fill 24 65 28 24 69 40 minecraft:polished_blackstone_bricks',
  'fill 52 65 28 52 69 40 minecraft:polished_blackstone_bricks',
  'fill 24 69 28 52 69 28 minecraft:chiseled_quartz_block',
  'setblock 38 67 28 minecraft:sea_lantern',
  'setblock 38 66 28 minecraft:gold_block',
  'setblock 38 68 28 minecraft:gold_block',
  'setblock 37 67 28 minecraft:gold_block',
  'setblock 39 67 28 minecraft:gold_block',
  'setblock 36 67 28 minecraft:cyan_glazed_terracotta',
  'setblock 40 67 28 minecraft:magenta_glazed_terracotta',
  'setblock 35 67 28 minecraft:purple_glazed_terracotta',
  'setblock 41 67 28 minecraft:blue_glazed_terracotta',
 ]
 for x in (26,30,34,38,42,46,50):
  cmds.extend(['setblock '+str(x)+' 64 30 minecraft:sea_lantern','setblock '+str(x)+' 64 38 minecraft:sea_lantern'])
 for x in (26,28,48,50):
  cmds.extend(['fill '+str(x)+' 65 28 '+str(x)+' 68 28 minecraft:chiseled_quartz_block','setblock '+str(x)+' 68 29 minecraft:amethyst_cluster[facing=south]'])
 for command in cmds:cmd(command)
 return {'scope':'Fresh private28x13 courtyard; physical black/gold/amethyst eye frieze and cyan/magenta/blue ceramic inlay','commands':cmds,'returnCorridor':{'x':[30,46],'z':[31,34],'feetY':65},'readbackStatus':'Caller must record actual live block probes','note':'Command plan is source; caller retains actual replies and must earn runtime evidence'}
def steps(phase,fps,prefix):
 # cam moves the actual spectator LocalPlayer; its y is FEET, eye lies~1.62m above.
 return [{'hud':False},{'clouds':False},{'wait':100},{'rec':phase['label'],'fps':fps},
  {'mark':prefix+'_recording'},{'await':prefix+'_recording','ticks':1200},
  {'cam':phase['camera']+phase['cameraEnd'],'seconds':phase['moveSeconds']},
  {'wait':phase['payoffTicks']},{'shot':phase['label']},{'recstop':True},
  {'mark':prefix+'_done'},{'await':prefix+'_done','ticks':1200}]
