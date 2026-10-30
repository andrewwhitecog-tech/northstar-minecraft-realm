import unittest,json,re,time
import nbtlib
rc=None
ROOT=None
DP=None
def data(sel,path=''):
 out=rc('data get entity '+sel+(' '+path if path else ''));m=re.search(r'has the following entity data: ([^\r\n]+)',out);assert m,out;return nbtlib.parse_nbt(m[1])
def count(sel):
 rc('scoreboard players set #count nspm_stat 0');rc('execute as '+sel+' run scoreboard players add #count nspm_stat 1');out=rc('scoreboard players get #count nspm_stat');return int(re.search(r'has (-?\d+)',out)[1])
def advance(n):
 before=int(re.search(r'(?:time is|is) (\d+)',rc('time query gametime'))[1]);rc('tick step '+str(n));end=time.monotonic()+15
 while time.monotonic()<end:
  now=int(re.search(r'(?:time is|is) (\d+)',rc('time query gametime'))[1])
  if now>=before+n:return
  time.sleep(.05)
 raise TimeoutError('Game tick advancement deadline')
def spawn(name):
 out=rc('execute positioned 560 200 64 run function nsp_mobs:summon/'+name)
 assert not any(x in out for x in ['Unknown function','Failed to instantiate','Missing argument']),out
 return '@e[tag=nsp_mob.'+name+',tag=nsp_mob.carrier,limit=1]'
class EngineV3(unittest.TestCase):
 def setUp(self):
  rc('function nsp_mob:clear');rc('kill @e[type=minecraft:item]')
 def test_all28_summons_loot_actual_item_entities_and_no_carrier_loot(self):
  names=sorted(n.split('/')[-1][:-11] for n in DP if n.startswith('data/nsp_mobs/function/summon/'))
  self.assertEqual(len(names),28)
  for name in names:
   rc('function nsp_mob:clear');rc('kill @e[type=minecraft:item]');sel=spawn(name);self.assertEqual(str(data(sel,'DeathLootTable')),'nsp_mobs:entities/'+name)
   result=rc('loot spawn 560 200 64 kill '+sel);self.assertNotIn('Unknown',result);self.assertGreater(count('@e[type=minecraft:item]'),0,result)
   self.assertEqual(count('@e[type=minecraft:item,nbt={Item:{id:"minecraft:rotten_flesh"}}]'),0)
   
   if name.startswith(('goliath_tusk_elephant','crowned_giraffe_strider_v2','paradise_sunburst_toucan')):self.assertEqual(int(data(sel).get('NoAI',0)),0)
   item=data('@e[type=minecraft:item,limit=1]','Item');self.assertIn('nsp_material',item['components']['minecraft:custom_data'])
 def test_glow15_normal12_survive_actual_damage_and_hurt_recovery(self):
  for name,level in [('savanna_lion_monarch_glow',15),('savanna_lion_monarch_iridescent',12)]:
   rc('function nsp_mob:clear');sel=spawn(name);visual='@e[tag=nsp_mob.'+name+'.visual,limit=1]';self.assertEqual(int(data(visual,'brightness')['block']),level)
   rc('damage '+sel+' 1 minecraft:generic');advance(2);self.assertEqual(int(data(visual).get('Glowing',0)),1);advance(20)
   self.assertEqual(int(data(visual,'brightness')['block']),level);self.assertEqual(int(data(visual).get('Glowing',0)),0)
 def test_baby_animal_and_baby_zombie_do_not_drop(self):
  for name,nbt in [('goliath_tusk_elephant','{Age:-24000}'),('savanna_lion_monarch','{IsBaby:1b}')]:
   rc('function nsp_mob:clear');rc('kill @e[type=minecraft:item]');sel=spawn(name);rc('data merge entity '+sel+' '+nbt);rc('loot spawn 560 200 64 kill '+sel);self.assertEqual(count('@e[type=minecraft:item]'),0)
 def test_raw_summon_has_custom_loot_and_brightness(self):
  old=spawn('coconut_carapace_crab_glow');rc('tag '+old+' add fixture_old');rc('execute as '+old+' on passengers run tag @s add fixture_old_visual');rc('scoreboard players set @e[tag=fixture_old_visual] nspm_light 7')
  rc('execute positioned 560 200 64 run function nsp_mobs:summon_raw/coconut_carapace_crab_glow');self.assertEqual(int(re.search(r'has (-?\d+)',rc('scoreboard players get @e[tag=fixture_old_visual,limit=1] nspm_light'))[1]),7);sel='@e[tag=nsp_mob.coconut_carapace_crab_glow,tag=nsp_mob.carrier,limit=1]'
  self.assertEqual(str(data(sel,'DeathLootTable')),'nsp_mobs:entities/coconut_carapace_crab_glow');self.assertEqual(int(data('@e[tag=nsp_mob.coconut_carapace_crab_glow.visual,limit=1]','brightness')['block']),15)
 def test_all_loot_tables_registered_in_actual_engine(self):
  tables=[n[5:-5].replace('/loot_table/','/').replace('/',':',1)for n in DP if '/loot_table/entities/'in n and n.endswith('.json')]
  self.assertGreaterEqual(len(tables),146)
  for name in tables:
   out=rc('loot spawn 560 200 64 loot '+name)
   self.assertFalse(any(s in out for s in ['Unknown loot table','Unknown element','Failed to parse']),out)
 def test_silent_carrier_has_zero_gear_drop_chances(self):
  sel=spawn('savanna_lion_monarch');doc=data(sel);self.assertEqual(int(doc['Silent']),1);self.assertEqual([float(v)for v in doc['HandDropChances']],[0.,0.]);self.assertEqual([float(v)for v in doc['ArmorDropChances']],[0.,0.,0.,0.])
