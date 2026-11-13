"""Real unittest checks using synthetic test-only61-coat baseline and actual8 COMPAT bytes.
No painter/render/native/world operations. Every generated test tree is below this owned home.
"""
import copy
import json
from pathlib import Path
import shutil
import struct
import tempfile
import unittest
import zlib
import adapt_representatives as A


def png(w,h,seed=1):
    def chunk(kind,raw):return struct.pack('>I',len(raw))+kind+raw+struct.pack('>I',zlib.crc32(kind+raw)&0xffffffff)
    scan=b''.join(b'\0'+bytes((seed%256,23,47,255))*w for _ in range(h))
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(scan))+chunk(b'IEND',b'')


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='adapter_test_',dir=A.HOME)
        self.root=Path(self.temp.name);self.addCleanup(self.temp.cleanup)
        self.pins=json.loads(A.read(A.HOME,'INPUT_PINS.json'));self.c=A.compiler(self.pins)
        roster=json.loads(A.read(A.HOME,'dependencies/roster_public.json'))
        selected=[r['id']for r in roster['entries']if not r['reuseVanilla']]
        assets=self.root/'assets';assets.mkdir()
        for number,rid in enumerate(selected,1):
            folder=assets/rid.split(':')[1];folder.mkdir()
            (folder/'adult.png').write_bytes(png(64,32,number))
            (folder/'baby.png').write_bytes(png(32,32,number))
        self.original=self.root/'original';self.c.compile_coats(assets,selected,self.original)
        self.pins['originalBuildSha256']=A.digest((self.original/'BUILD_ACTUAL.json').read_bytes())
        self.reps=self.root/'representatives';shutil.copytree(A.HOME/'inputs/representatives',self.reps)
    def output(self,name='out'):return self.root/name
    def repin_test_png(self,rel,data):
        # Test-only malicious reviewed input: hashes agree, so real PNG validation must reject.
        (self.reps/rel).write_bytes(data)
        receipt=json.loads((self.reps/'REPRESENTATIVE_ACTUAL.json').read_text())
        for row in receipt['files']:
            if row['path']==rel:row.update(bytes=len(data),sha256=A.digest(data))
        raw=(json.dumps(receipt,indent=2)+'\n').encode();(self.reps/'REPRESENTATIVE_ACTUAL.json').write_bytes(raw)
        self.pins['representativeReceiptSha256']=A.digest(raw)
        for row in self.pins['compatInputs']:
            if row['path']==rel:row.update(bytes=len(data),sha256=A.digest(data))
    def test_new_pack_exact_eight_changes_preserves_all_registries_and57coats(self):
        before={p:A.read(self.original,p)for p in A.inventory(self.original)}
        result=A.emit(self.original,self.reps,self.output(),self.pins)
        self.assertEqual(result['schema'],'northstar.cat-representative-native-build.v1')
        old=json.loads(before['BUILD_ACTUAL.json']);self.assertEqual(result['selectedIDs'],old['selectedIDs'])
        self.assertEqual(len(result['selectedIDs']),61);self.assertEqual(result['unchangedCoats'],57)
        self.assertEqual(result['unchangedPayloadFiles'],177)
        self.assertEqual(set(result['changedFiles']),set(A.TARGETS))
        self.assertEqual(A.inventory(self.output()),set(old['files'])|{'BUILD_ACTUAL.json'})
        for rel in old['files']:
            expected=A.read(self.reps,A.TARGETS[rel]) if rel in A.TARGETS else before[rel]
            self.assertEqual(A.read(self.output(),rel),expected,rel)
        self.assertEqual({p:A.read(self.original,p)for p in A.inventory(self.original)},before)
        self.assertEqual(self.c.validate_compiled_coats(self.output())['validatedVariants'],61)
        self.assertFalse(result['nativeVerified']);self.assertFalse(result['humanVisualAccepted']);self.assertFalse(result['liveInstalled'])
    def test_crc_and_hd_rejected_even_with_consistent_reviewer_hashes(self):
        rel=A.TARGETS[next(iter(A.TARGETS))]
        bad=bytearray(A.read(self.reps,rel));bad[-5]^=1
        self.repin_test_png(rel,bytes(bad))
        with self.assertRaisesRegex(ValueError,'CRC'):A.emit(self.original,self.reps,self.output('bad_crc'),self.pins)
        self.assertFalse(self.output('bad_crc').exists())
        self.repin_test_png(rel,png(256,128))
        with self.assertRaisesRegex(ValueError,'dimensions'):A.emit(self.original,self.reps,self.output('bad_hd'),self.pins)
        self.assertFalse(self.output('bad_hd').exists())
    def test_unlisted_original_and_payload_hash_drift_fail_before_output(self):
        extra=self.original/'unlisted.txt';extra.write_text('unexpected')
        with self.assertRaises(ValueError):A.emit(self.original,self.reps,self.output('extra'),self.pins)
        self.assertFalse(self.output('extra').exists());extra.unlink()
        target=self.original/next(iter(A.TARGETS));target.write_bytes(png(64,32,250))
        with self.assertRaises(ValueError):A.emit(self.original,self.reps,self.output('drift'),self.pins)
        self.assertFalse(self.output('drift').exists())
    def test_existing_outside_and_path_escape_refused_without_overwrite(self):
        existing=self.output();existing.mkdir();sentinel=existing/'keep.txt';sentinel.write_text('original')
        with self.assertRaises(ValueError):A.emit(self.original,self.reps,existing,self.pins)
        self.assertEqual(sentinel.read_text(),'original')
        with self.assertRaises(ValueError):A.emit(self.original,self.reps,A.HOME.parent/'not_owned',self.pins)
        for rel in ('../escape','/escape','compat/../../escape','compat\\escape','C:/escape'):
            with self.subTest(rel=rel):
                with self.assertRaises(ValueError):A.member(self.root,rel)
    def test_wrong_receipt_or_compat_allowlist_fails_closed(self):
        bad=copy.deepcopy(self.pins);bad['representativeReceiptSha256']='0'*64
        with self.assertRaisesRegex(ValueError,'producer receipt|Producer receipt|Representative producer receipt'):A.emit(self.original,self.reps,self.output('receipt'),bad)
        bad=copy.deepcopy(self.pins);bad['compatInputs'][0]['path']=bad['compatInputs'][0]['path'].replace('compat/','detail/')
        with self.assertRaisesRegex(ValueError,'eight COMPAT'):A.emit(self.original,self.reps,self.output('detail'),bad)
        self.assertFalse(self.output('receipt').exists());self.assertFalse(self.output('detail').exists())


if __name__=='__main__':unittest.main()
