"""Bounded source/rig checks only; no export, model render or native launch."""
import importlib.util,math,re,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('rabbits',ROOT/'build_rabbits_v03.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class RabbitSourceTests(unittest.TestCase):
 def test_exact_four_replacements_only(self):
  self.assertEqual({a.name for a in m.all_assets()},{'mutant_rabbit_boss','velvet_hare_duelist','porcelain_rabbit_watchkeeper','stitched_hare_herald'})
 def test_native_bone_budget_and_element_limits(self):
  for a in m.all_assets():
   self.assertLessEqual(len(a.bones),32)
   for c in a.cubes:
    p=a.bones[c['bone']]['pivot'];lo=[c['min'][i]-p[i]+8 for i in range(3)];hi=[lo[i]+c['size'][i] for i in range(3)]
    self.assertTrue(all(-16<=v<=32 for v in lo+hi),(a.name,c['bone'],lo,hi))
 def test_rig_parent_graph_and_motion_channels(self):
  for a in m.all_assets():
   for bn,b in a.bones.items():
    seen=set();cur=bn
    while cur is not None:self.assertNotIn(cur,seen);seen.add(cur);self.assertIn(cur,a.bones);cur=a.bones[cur]['parent']
   for channels in a.clips.values():
    for bn,(axis,amp,phase) in channels.items():self.assertIn(bn,a.bones);self.assertIn(axis,[0,1,2]);self.assertTrue(all(math.isfinite(v) for v in [amp,phase]))
 def test_separate_muzzle_jaw_and_articulated_ears(self):
  for a in m.all_assets():
   self.assertTrue({'muzzle','jaw','left_ear_base','left_ear_tip','right_ear_base','right_ear_tip','left_eye','right_eye'}<=set(a.bones))
   self.assertNotEqual(a.bones['left_ear_tip']['pivot'][1],a.bones['right_ear_tip']['pivot'][1])
 def test_boss_quadruped_proportions_and_separate_identity(self):
  a=m.boss_v03();volume=lambda bn:sum(math.prod(c['size']) for c in a.cubes if c['bone']==bn)
  self.assertGreater(volume('left_thigh'),volume('left_forepaw')*4)
  self.assertIn('left_hock',a.bones);self.assertIn('left_foreleg',a.bones);self.assertNotIn('crown',a.bones)
  self.assertGreater((max(c['min'][1]+c['size'][1] for c in a.cubes)-min(c['min'][1] for c in a.cubes))/16,7)
 def test_original_painted_atlas_has_actual_detail(self):
  im=m.texture_atlas();self.assertEqual(im.size,(128,128));self.assertGreater(len(im.getcolors(16384) or []),100)
 def test_source_has_no_absolute_drive_paths(self):
  self.assertIsNone(re.search(r'[A-Za-z]:[/\\]',(ROOT/'build_rabbits_v03.py').read_text()))
if __name__=='__main__':unittest.main(verbosity=2)
