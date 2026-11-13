"""Actual source safety/rig tests. Hosted workflow executes; never fake recorded results."""
import importlib.util,math,re,unittest
from pathlib import Path
from validate_fauna_exports import BASE,EXPANSION
ROOT=Path(__file__).resolve().parent
def module(name):
 spec=importlib.util.spec_from_file_location(name,ROOT/(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
base=module('build_original_fauna');expansion=module('build_fauna_expansion')
class SourceTests(unittest.TestCase):
 def test_exact_requested_coverage_without_reexporting_six(self):
  self.assertEqual({a.name for a in base.all_assets()},BASE)
  self.assertEqual({a.name for a in expansion.all_assets()},EXPANSION)
  self.assertFalse(BASE&EXPANSION)
 def test_bone_topology_and_positive_finite_geometry(self):
  for m in [base,expansion]:
   for a in m.all_assets():
    self.assertLess(len(a.bones),64)
    for name,b in a.bones.items():
     seen=set();cur=name
     while cur is not None:self.assertNotIn(cur,seen);seen.add(cur);self.assertIn(cur,a.bones);cur=a.bones[cur]['parent']
    for c in a.cubes:self.assertGreater(min(c['size']),0);self.assertTrue(all(math.isfinite(x) for x in c['min']+c['size']))
 def test_native_java_item_coordinate_limits_before_export(self):
  for a in base.all_assets()+expansion.all_assets():
   for c in a.cubes:
    pivot=a.bones[c['bone']]['pivot'];lo=[c['min'][k]-pivot[k]+8 for k in range(3)];hi=[lo[k]+c['size'][k] for k in range(3)]
    self.assertTrue(all(-16<=v<=32 for v in lo+hi),(a.name,c))
 def test_fish_shark_vertical_tail_and_dolphin_horizontal_flukes(self):
  assets={a.name:a for a in base.all_assets()}
  for name in ['ossuary_shark','reef_shark','jewel_dolphin']:
   c=[c for c in assets[name].cubes if c['bone']=='tail_fin'];lo=[min(x['min'][k] for x in c) for k in range(3)];hi=[max(x['min'][k]+x['size'][k] for x in c) for k in range(3)]
   self.assertGreater(hi[0]-lo[0],hi[1]-lo[1]) if name=='jewel_dolphin' else self.assertGreater(hi[1]-lo[1],hi[0]-lo[0])
 def test_mutant_boss_is_separate_and_really_large_model(self):
  assets={a.name:a for a in expansion.all_assets()};boss=assets['mutant_rabbit_boss'];king=assets['crowned_rat']
  extent=lambda a:max(c['min'][1]+c['size'][1] for c in a.cubes)-min(c['min'][1] for c in a.cubes)
  self.assertGreater(extent(boss)/16,7);self.assertGreater(extent(boss),extent(king)*8);self.assertNotIn('crown',boss.bones)
 def test_actual_rodent_geometry_on_rabbit_carriers_without_global_reskin(self):
  names=['rat','mouse','neon_rat','neon_mouse','crowned_rat','crowned_mouse'];assets={a.name:a for a in expansion.all_assets()}
  for name in names:self.assertEqual(assets[name].carrier,'minecraft:rabbit');self.assertIn('tail_tip',assets[name].bones);self.assertIn('jaw',assets[name].bones)
  self.assertNotEqual(assets['rat'].cubes,assets['mouse'].cubes)
 def test_clam_oyster_are_distinct_hinged_assets(self):
  assets={a.name:a for a in expansion.all_assets()};c,o=assets['wet_sand_clam'],assets['tidal_oyster']
  self.assertNotEqual(c.cubes,o.cubes)
  for a in [c,o]:self.assertIn('upper_shell',a.bones);self.assertIn('filter',a.clips);self.assertGreater(abs(a.clips['filter']['upper_shell'][1]),0)
 def test_all_requested_actor_families_have_real_articulated_motion(self):
  for a in base.all_assets()+expansion.all_assets():
   self.assertTrue(any(channels for channels in a.clips.values()),a.name)
   self.assertTrue(any(abs(amp)>0 for channels in a.clips.values() for axis,amp,phase in channels.values()),a.name)
 def test_portable_exporter_sources_contain_no_private_absolute_paths(self):
  for name in ['build_original_fauna.py','build_fauna_expansion.py']:
   text=(ROOT/name).read_text();self.assertIsNone(re.search(r'[A-Za-z]:[/\\]',text),'Absolute drive path in portable exporter')
if __name__=='__main__':unittest.main(verbosity=2)
