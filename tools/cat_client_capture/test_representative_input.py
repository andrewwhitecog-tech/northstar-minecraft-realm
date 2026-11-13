"""Portable unittest fixtures, not native/runtime/visual evidence.

Reuse the actual adapter's AdapterTests synthetic61 baseline and real retained8
COMPAT bytes, exclusively in a copied and explicitly repinned UNIT fixture.
Run only under the owning admission/hosted workflow. No network or world input.
"""
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

import representative_input as V

DEFAULT_ADAPTER=Path(__file__).resolve().parents[1]/'cat_native_representatives'

class RepresentativeInputTests(unittest.TestCase):
    def setUp(self):
        origin=Path(os.environ.get('NSP_REPRESENTATIVE_ADAPTER_HOME',str(DEFAULT_ADAPTER))).absolute()
        if not origin.is_dir(): raise RuntimeError('Actual reviewed adapter source is required; set NSP_REPRESENTATIVE_ADAPTER_HOME')
        temp=tempfile.TemporaryDirectory(prefix='representative_input_UNIT_')
        self.addCleanup(temp.cleanup);self.unit_root=Path(temp.name);self.home=self.unit_root/'fixture_adapter';self.home.mkdir()
        source_raw=V.regular(origin/'PUBLIC_ADAPTER_SOURCE.json');packet=V.parsed(source_raw)
        # Only the frozen source graph is copied, not original build outputs or any worlds.
        for rel,pin in packet['files'].items():
            data=V.regular(V.member(origin,rel));self.assertEqual(V.digest(data),pin['sha256'])
            dst=V.member(self.home,rel);dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(data)
        (self.home/'PUBLIC_ADAPTER_SOURCE.json').write_bytes(source_raw)
        self.original_packet=packet
        spec=importlib.util.spec_from_file_location('UNIT_fixture_adapter',self.home/'adapt_representatives.py')
        self.A=importlib.util.module_from_spec(spec)
        with V.no_bytecode(): spec.loader.exec_module(self.A)
        # Reuse the reviewed, actual adapter's synthetic baseline fixture builder.
        previous=sys.modules.get('adapt_representatives');sys.modules['adapt_representatives']=self.A
        try:
            spec=importlib.util.spec_from_file_location('UNIT_fixture_adapter_tests',self.home/'test_adapter.py')
            module=importlib.util.module_from_spec(spec)
            with V.no_bytecode(): spec.loader.exec_module(module)
        finally:
            if previous is None: sys.modules.pop('adapt_representatives',None)
            else: sys.modules['adapt_representatives']=previous
        self.inner=module.AdapterTests('test_new_pack_exact_eight_changes_preserves_all_registries_and57coats')
        self.addCleanup(self.inner.doCleanups)
        with V.no_bytecode(): self.inner.setUp()
        self.base=self.inner.original;self.candidate=self.inner.output('UNIT_adapted_candidate')
        # Explicit UNIT-only source/input repin binds this synthetic build receipt.
        (self.home/'INPUT_PINS.json').write_text(json.dumps(self.inner.pins,indent=2)+'\n',encoding='utf-8')
        self.repin_fixture_source()
        self.receipt=self.A.emit(self.base,self.inner.reps,self.candidate,self.inner.pins)

    def repin_fixture_source(self):
        packet=copy.deepcopy(self.original_packet)
        for rel in packet['files']:
            data=V.regular(V.member(self.home,rel));packet['files'][rel]={'bytes':len(data),'sha256':V.digest(data)}
        raw=(json.dumps(packet,indent=2)+'\n').encode();(self.home/'PUBLIC_ADAPTER_SOURCE.json').write_bytes(raw)
        self.reviewed=V.digest(raw)

    def validate(self,base=None,candidate=None,reviewed=None):
        return V.validate_adapted_input(base or self.base/'BUILD_ACTUAL.json',candidate or self.candidate/'BUILD_ACTUAL.json',self.home,reviewed or self.reviewed)

    def write_receipt(self,receipt):
        (self.candidate/'BUILD_ACTUAL.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')

    def snapshot(self):
        return {p.relative_to(self.home).as_posix():p.read_bytes() for p in self.home.rglob('*') if p.is_file()}

    def test_exact_adapter_result_is_accepted_without_any_file_changes(self):
        before=self.snapshot();root,receipt=self.validate()
        self.assertEqual(root,self.candidate);self.assertEqual(receipt,self.receipt)
        self.assertEqual(receipt['unchangedPayloadFiles'],177);self.assertEqual(receipt['unchangedCoats'],57)
        self.assertEqual(set(receipt['changedFiles']),set(V.TARGETS));self.assertEqual(len(receipt['selectedIDs']),61)
        self.assertFalse(receipt['nativeVerified']);self.assertFalse(receipt['humanVisualAccepted']);self.assertFalse(receipt['liveInstalled'])
        self.assertEqual(self.snapshot(),before,'Read-only validator modified its fixture')

    def test_source_guard_precedes_any_candidate_or_base_read(self):
        with self.assertRaisesRegex(ValueError,'Reviewed adapter packet'):
            self.validate(base=self.unit_root/'absent_base/BUILD_ACTUAL.json',candidate=self.unit_root/'absent_candidate/BUILD_ACTUAL.json',reviewed='0'*64)
        with (self.home/'adapt_representatives.py').open('a') as f:f.write('\n# UNIT source drift\n')
        with self.assertRaisesRegex(ValueError,'Adapter source/input drift'):
            self.validate(candidate=self.unit_root/'absent_candidate/BUILD_ACTUAL.json')

    def test_repinned_UNIT_adapter_cannot_change_exact_target_map(self):
        with (self.home/'adapt_representatives.py').open('a') as f:
            f.write('\nTARGETS["'+next(iter(V.TARGETS))+'"]="compat/wrong/adult.png"\n')
        self.repin_fixture_source()
        with self.assertRaisesRegex(ValueError,'eight-target adapter mapping'):self.validate()

    def test_altered_receipt_provenance_counts_ids_or_acceptance_are_refused(self):
        variants=[]
        for field,value in [('nativeVerified',True),('humanVisualAccepted',True),('liveInstalled',True),('success',1),('unchangedPayloadFiles',176),('unchangedCoats',56),('rosterEntries',0)]:
            item=copy.deepcopy(self.receipt);item[field]=value;variants.append((field,item))
        item=copy.deepcopy(self.receipt);item['provenance']['representativeReceiptSha256']='0'*64;variants.append(('provenance',item))
        item=copy.deepcopy(self.receipt);item['selectedIDs'][0]='nsp_cat_coats:unreviewed';variants.append(('registry_ids',item))
        item=copy.deepcopy(self.receipt);item['files']['../escaped.txt']={'bytes':1,'sha256':'0'*64};variants.append(('escaped_member',item))
        for label,receipt in variants:
            with self.subTest(label=label):
                self.write_receipt(receipt)
                with self.assertRaisesRegex(ValueError,'Candidate receipt differs'):self.validate()
        self.write_receipt(self.receipt)
        path=self.candidate/'BUILD_ACTUAL.json';raw=path.read_text();path.write_text(raw.replace('{','{"success":false,',1))
        with self.assertRaisesRegex(ValueError,'Duplicate JSON'):self.validate()

    def test_mutated_texture_or_unchanged_member_refused_even_when_receipt_repinned(self):
        target=next(iter(V.TARGETS));other='java_datapack/pack.mcmeta'
        for rel in (target,other):
            with self.subTest(rel=rel):
                path=self.candidate/rel;before=path.read_bytes()
                altered=(self.base/rel).read_bytes() if rel==target else before+b'\n'
                self.assertNotEqual(altered,before);path.write_bytes(altered)
                with self.assertRaises(ValueError):self.validate()
                forged=copy.deepcopy(self.receipt);forged['files'][rel]={'bytes':len(altered),'sha256':V.digest(altered)};self.write_receipt(forged)
                with self.assertRaisesRegex(ValueError,'Candidate receipt differs'):self.validate()
                path.write_bytes(before);self.write_receipt(self.receipt)

    def test_extra_missing_registry_and_outside_or_overlapping_trees_refused(self):
        extra=self.candidate/'unlisted.txt';extra.write_text('UNIT unexpected')
        with self.assertRaisesRegex(ValueError,'extra or missing'):self.validate()
        extra.unlink();rel='java_datapack/data/nsp_cat_coats/cat_variant/domestic_bengal.json';p=self.candidate/rel;raw=p.read_bytes();p.unlink()
        with self.assertRaisesRegex(ValueError,'extra or missing'):self.validate()
        p.write_bytes(raw)
        with self.assertRaisesRegex(ValueError,'below reviewed adapter home'):
            self.validate(candidate=self.unit_root/'outside/BUILD_ACTUAL.json')
        with self.assertRaisesRegex(ValueError,'must be disjoint'):
            self.validate(candidate=self.base/'BUILD_ACTUAL.json')

    def test_hardlinked_candidate_file_refused(self):
        p=self.candidate/next(iter(V.TARGETS));data=p.read_bytes();p.unlink()
        other=self.unit_root/'UNIT_link_source.png';other.write_bytes(data)
        try:os.link(other,p)
        except (OSError,NotImplementedError) as error:
            p.write_bytes(data);self.skipTest('Platform cannot create UNIT hard-link fixture: '+type(error).__name__)
        with self.assertRaisesRegex(ValueError,'Hard-linked file refused'):self.validate()

if __name__=='__main__':unittest.main()
