"""Actual stdlib unittest definitions; tiny synthetic raw fixtures, NOT native proof."""
import json,tempfile,unittest,zlib
from pathlib import Path
from spool_verify import verify_spool
class StationarySpoolTests(unittest.TestCase):
 def fixture(self,root,mode='OFFLINE_NATIVE_ANIMATED_SUBJECT',duplicate=False,corrupt=False):
  base=Path(root)/'take';data=[bytes([1,2,3,4]),bytes([7,11,13,17])];pose=[1,2,3,0,0]
  base.with_suffix('.rgba').write_bytes(b''.join(data))
  rows=[dict(mode=mode,index=i,renderId=10 if duplicate else 10+i,offset=i*4,bytes=4,crc32=zlib.crc32(b)+(1 if corrupt else 0),pose=pose) for i,b in enumerate(data)]
  base.with_suffix('.frames.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
  return base,pose
 def test_explicit_mode_verifies_actual_bytes_and_labels(self):
  with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
   b,p=self.fixture(d);r=verify_spool(b,2,24,p,p,frame_bytes=4,expected_mode='OFFLINE_NATIVE_ANIMATED_SUBJECT')
   self.assertEqual(r['mode'],'OFFLINE_NATIVE_ANIMATED_SUBJECT');self.assertEqual(r['crcVerifiedFrames'],2)
 def test_default_translating_contract_does_not_accept_still(self):
  with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
   b,p=self.fixture(d)
   with self.assertRaises(ValueError):verify_spool(b,2,24,p,p,frame_bytes=4)
 def test_explicit_stationary_rejects_motion_and_mislabeled_spool(self):
  with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
   b,p=self.fixture(d,'OFFLINE_NATIVE_CINEMATIC')
   with self.assertRaises(ValueError):verify_spool(b,2,24,p,p,frame_bytes=4,expected_mode='OFFLINE_NATIVE_ANIMATED_SUBJECT')
   with self.assertRaises(ValueError):verify_spool(b,2,24,p,[2,2,3,0,0],frame_bytes=4,expected_mode='OFFLINE_NATIVE_ANIMATED_SUBJECT')
 def test_actual_crc_and_duplicate_identity_still_rejected(self):
  for options in ({'duplicate':True},{'corrupt':True}):
   with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
    b,p=self.fixture(d,**options)
    with self.assertRaises(ValueError):verify_spool(b,2,24,p,p,frame_bytes=4,expected_mode='OFFLINE_NATIVE_ANIMATED_SUBJECT')
if __name__=='__main__':unittest.main(verbosity=2)
