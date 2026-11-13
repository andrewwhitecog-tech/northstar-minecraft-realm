"""Bounded source constraints. Does not export or render the model."""
import importlib.util,math,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('boss',ROOT/'build_boss_v04.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class BossCraftTests(unittest.TestCase):
 def test_only_requested_boss(self):self.assertEqual([a.name for a in m.all_assets()],['mutant_rabbit_boss'])
 def test_native_coordinate_limits_and_bone_budget(self):
  a=m.boss_v04();self.assertLessEqual(len(a.bones),32);bad=[]
  for c in a.cubes:
   p=a.bones[c['bone']]['pivot'];lo=[c['min'][i]-p[i]+8 for i in range(3)];hi=[lo[i]+c['size'][i] for i in range(3)]
   if not all(-16<=v<=32 for v in lo+hi):bad.append((c['bone'],lo,hi))
  self.assertEqual(bad,[])
 def test_no_old_large_rectangular_body_or_muzzle(self):
  a=m.boss_v04();self.assertGreater(len(a.cubes),900);self.assertLess(len(a.cubes),5000)
  self.assertFalse(any(all(s>=8 for s in c['size']) for c in a.cubes))
  self.assertTrue({'muzzle','jaw','left_eye','right_eye','left_ear_base','left_ear_tip','right_ear_base','right_ear_tip'}<=set(a.bones))
 def test_hindfeet_and_rear_mass_outweigh_forepaws(self):
  a=m.boss_v04();cs=lambda bn:[c for c in a.cubes if c['bone']==bn]
  volume=lambda bn:sum(math.prod(c['size']) for c in cs(bn))
  extent=lambda bn,k:max(c['min'][k]+c['size'][k] for c in cs(bn))-min(c['min'][k] for c in cs(bn))
  self.assertGreater(volume('left_thigh'),volume('left_forepaw')*5)
  self.assertGreater(extent('left_foot',2),extent('left_forepaw',2)*2)
  self.assertGreater(extent('left_ear_base',0),8)
  self.assertGreater((max(c['min'][1]+c['size'][1] for c in a.cubes)-min(c['min'][1] for c in a.cubes))/16,8)
 def test_prism_is_localized_not_fur_wallpaper(self):
  a=m.boss_v04();prism={'cyan','magenta','emerald','violet','gem_dark'}
  allowed={'spine_crystal_0','spine_crystal_1','spine_crystal_2','head','chest'}
  self.assertTrue(all(c['bone'] in allowed for c in a.cubes if c['material'] in prism))
  self.assertTrue(any(c['material']=='eye' for c in a.cubes));self.assertTrue(any(c['material']=='eye_purple' for c in a.cubes))
 def test_rig_graph_and_actual_motion_channels(self):
  a=m.boss_v04()
  for bn,b in a.bones.items():
   seen=set();cur=bn
   while cur is not None:self.assertNotIn(cur,seen);seen.add(cur);self.assertIn(cur,a.bones);cur=a.bones[cur]['parent']
  for channels in a.clips.values():
   for bn,(axis,amp,phase) in channels.items():self.assertIn(bn,a.bones);self.assertIn(axis,[0,1,2]);self.assertTrue(math.isfinite(amp+phase))
 def test_native_texture_atlas_capacity(self):self.assertLessEqual(len(m.COLORS),64)
if __name__=='__main__':unittest.main(verbosity=2)
