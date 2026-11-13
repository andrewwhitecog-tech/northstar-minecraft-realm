"""Offline generator regressions. These tests never start Minecraft or prove gameplay."""
from __future__ import annotations
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
import unittest
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
GENERATOR = Path(os.environ.get('NSP_CANNON_GENERATOR', str(HERE / 'build_cannon.py')))
CONFIG = Path(os.environ.get('NSP_CANNON_CONFIG', str(HERE / 'demo_config.json')))
spec = importlib.util.spec_from_file_location('cannon_generator_under_test', GENERATOR)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.cfg = json.loads(CONFIG.read_text(encoding='utf-8'))

    def invalid(self, mutate):
        cfg = copy.deepcopy(self.cfg)
        mutate(cfg)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'must_not_be_created'
            with self.assertRaises((ValueError, TypeError, KeyError)):
                module.build(cfg, output)
            self.assertFalse(output.exists(), 'Invalid input wrote output before rejection')

    def test_demo_build_reports_source_only_and_real_file_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'pack'
            manifest = module.build(self.cfg, output)
            self.assertIs(manifest['native_verified'], False)
            self.assertIs(manifest['live_installed'], False)
            actual = {p.relative_to(output).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in output.rglob('*') if p.is_file()}
            self.assertEqual(manifest['files'], actual)
            self.assertGreater(len(actual), 0)

    def test_unsupported_or_injected_dimension_rejected_before_write(self):
        for value in ['overworld', 'minecraft:overworld\nkill @a', '../minecraft:overworld', None, True]:
            with self.subTest(value=value):
                self.invalid(lambda c: c.__setitem__('dimension', value))

    def test_cannon_ids_cannot_escape_output_or_inject_commands(self):
        for value in ['../escape', '/absolute', 'a/b', r'a\b', 'a:bad', 'a\nkill @a', 'a"}]', '', '9gun', 'A', 'x'*17]:
            with self.subTest(value=value):
                self.invalid(lambda c: c['guns'][0].__setitem__('id', value))

    def test_duplicate_ids_rejected(self):
        self.invalid(lambda c: c['guns'].append(copy.deepcopy(c['guns'][0])))

    def test_no_guns_rejected(self):
        self.invalid(lambda c: c.__setitem__('guns', []))

    def test_nine_guns_rejected(self):
        def change(c):
            c['guns'] = [dict(copy.deepcopy(c['guns'][0]), id='gun'+str(i)) for i in range(9)]
        self.invalid(change)

    def test_integer_yaw_extremes_accepted(self):
        for value in [-180, 0, 180]:
            with self.subTest(value=value):
                cfg = copy.deepcopy(self.cfg); cfg['guns'][0]['yaw'] = value
                module.valid(cfg)

    def test_yaw_rejects_bool_even_though_bool_is_int_subclass(self):
        for value in [True, False]:
            with self.subTest(value=value):
                self.invalid(lambda c: c['guns'][0].__setitem__('yaw', value))

    def test_yaw_rejects_float_even_when_numerically_integral(self):
        for value in [0.0, 1.0, -180.0, 2.5, float('inf'), float('nan')]:
            with self.subTest(value=value):
                self.invalid(lambda c: c['guns'][0].__setitem__('yaw', value))

    def test_yaw_outside_range_or_command_text_rejected(self):
        for value in [-181, 181, '0\nkill @a', None]:
            with self.subTest(value=value):
                self.invalid(lambda c: c['guns'][0].__setitem__('yaw', value))

    def test_site_bounds_must_be_three_real_integers(self):
        for value in [[0,40], [0,40,0,0], [False,40,0], [0.0,40,0], ['0',40,0]]:
            with self.subTest(value=value):
                self.invalid(lambda c: c['site'].__setitem__('min', value))

    def test_reversed_degenerate_or_oversized_site_rejected(self):
        for value in [[0,127,127], [-1,127,127], [513,127,127]]:
            with self.subTest(value=value):
                self.invalid(lambda c: c['site'].__setitem__('max', value))

    def test_overworld_height_bounds_rejected_outside_supported_range(self):
        for key,value in [('min',[0,-65,0]), ('max',[127,320,127])]:
            with self.subTest(key=key,value=value):
                self.invalid(lambda c: c['site'].__setitem__(key,value))

    def test_nonfinite_or_non_numeric_pivot_rejected(self):
        for value in [float('nan'), float('inf'), float('-inf'), True, '65\nkill @a']:
            with self.subTest(value=value):
                def change(c): c['guns'][0]['pivot'][1] = value
                self.invalid(change)

    def test_fractional_or_bool_breech_rejected(self):
        for value in [65.5, 65.0, True, '65']:
            with self.subTest(value=value):
                def change(c): c['guns'][0]['breech'][1] = value
                self.invalid(change)

    def test_site_margin_is_not_merely_center_in_bounds(self):
        for key in ['pivot','breech']:
            for value in [2, 125]:
                with self.subTest(key=key,value=value):
                    def change(c): c['guns'][0][key][0] = value
                    self.invalid(change)

    def test_empty_and_wrong_config_shapes_reject_without_writes(self):
        for value in [None, [], {}, {'dimension':'minecraft:overworld'}]:
            with self.subTest(value=value):
                with tempfile.TemporaryDirectory() as tmp:
                    output = Path(tmp)/'pack'
                    with self.assertRaises((ValueError, TypeError, KeyError)):
                        module.build(value, output)
                    self.assertFalse(output.exists())

    def test_existing_nonempty_output_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)/'previous'; output.mkdir()
            sentinel = output/'keeper.bin'; sentinel.write_bytes(b'KEEP EXACTLY\x00\xff')
            before = sentinel.read_bytes()
            with self.assertRaises(ValueError): module.build(self.cfg, output)
            self.assertEqual(sentinel.read_bytes(), before)
            self.assertEqual([p.name for p in output.iterdir()], ['keeper.bin'])

    def test_existing_file_as_output_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)/'keeper'; output.write_bytes(b'keeper')
            with self.assertRaises((ValueError, OSError)): module.build(self.cfg, output)
            self.assertEqual(output.read_bytes(), b'keeper')

    def test_control_names_cannot_inject_paths_or_commands(self):
        for name in ['../escape','fire\nkill @a','bogus']:
            with self.subTest(name=name):
                self.invalid(lambda c: c['guns'][0].__setitem__('controls',{name:[32,65,25]}))

    def test_control_coordinates_are_integer_and_inside_site(self):
        for position in [[False,65,25],[32.5,65,25],[32,65],['32',65,25],[0,65,25],[127,65,25]]:
            with self.subTest(position=position):
                self.invalid(lambda c: c['guns'][0].__setitem__('controls',{'fire':position}))

    def test_muzzle_offsets_reject_nonfinite_bool_or_outside_caps(self):
        for key,values in [('muzzle_distance',[True,-1,16.1,float('nan')]),('muzzle_height',[True,-1,12.1,float('inf')])]:
            for value in values:
                with self.subTest(key=key,value=value):
                    self.invalid(lambda c: c['guns'][0].__setitem__(key,value))

class GeneratedPackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.output = Path(self.tmp.name)/'pack'
        cfg = json.loads(CONFIG.read_text(encoding='utf-8'))
        module.build(cfg, self.output)
        self.functions = {p.relative_to(self.output/'data/nsp_ck/function').with_suffix('').as_posix():p.read_text(encoding='utf-8')
                          for p in (self.output/'data/nsp_ck/function').rglob('*.mcfunction')}

    def test_every_function_and_function_tag_reference_resolves(self):
        refs = set()
        for body in self.functions.values():
            refs.update(re.findall(r'(?:^|\s)function\s+(#?[a-z0-9_.-]+:[a-z0-9_./-]+)', body, re.M))
        self.assertGreater(len(refs),0)
        for ref in sorted(refs):
            with self.subTest(reference=ref):
                tag = ref.startswith('#'); ns,name = ref.lstrip('#').split(':',1)
                target = self.output/'data'/ns/('tags/function' if tag else 'function')/(name+('.json' if tag else '.mcfunction'))
                self.assertTrue(target.is_file(), 'Dangling generated reference: '+ref)
        for path in self.output.glob('data/*/tags/function/*.json'):
            obj = json.loads(path.read_text(encoding='utf-8'))
            for value in obj['values']:
                ref = value if isinstance(value,str) else value['id']
                ns,name = ref.split(':',1)
                self.assertTrue((self.output/'data'/ns/'function'/(name+'.mcfunction')).is_file(), str(path)+' -> '+ref)

    def test_referenced_item_modifiers_exist(self):
        refs=set()
        for body in self.functions.values():
            refs.update(re.findall(r'\bitem modify block [^\n]*?\s([a-z0-9_.-]+:[a-z0-9_./-]+)\s*$',body,re.M))
        self.assertGreater(len(refs),0)
        for ref in refs:
            ns,name=ref.split(':',1)
            self.assertTrue((self.output/'data'/ns/'item_modifier'/(name+'.json')).is_file(),ref)

    def test_no_real_projectile_or_explosive_entities_are_spawned(self):
        spawned=[]
        for name,body in self.functions.items():
            for line in body.splitlines():
                match=re.search(r'(?:^|\s)summon\s+([^\s]+)',line)
                if match: spawned.append((name,match.group(1)))
        self.assertTrue(spawned)
        for name,entity in spawned:
            with self.subTest(function=name,entity=entity):
                self.assertIn(entity, {'minecraft:marker','minecraft:interaction','minecraft:block_display','minecraft:item_display'})

    def test_damage_cannot_target_players_or_unregistered_types(self):
        damaging=[]
        for name,body in self.functions.items():
            for line in body.splitlines():
                if re.search(r'(?:^|\s)damage\s',line): damaging.append((name,line))
        self.assertTrue(damaging)
        for name,line in damaging:
            with self.subTest(function=name,line=line):
                self.assertRegex(line,r'^execute if entity @s\[type=minecraft:(?:drowned|skeleton),tag=nsp_ck\.target,scores=\{ck_role=1\}\] run damage @s [0-9]+ minecraft:magic$')
        register=self.functions['api/register_target']
        self.assertIn('execute if entity @s[type=minecraft:player] run return 0',register)
        self.assertLess(register.index('type=minecraft:player'),register.index('function nsp_ck:target/register_mob'))

    def test_actual_chain_powder_predicate_not_vanilla_gunpowder(self):
        loads='\n'.join(v for k,v in self.functions.items() if k.endswith('/load') or k.endswith('/consume_powder'))
        self.assertIn('custom_data~{nsp_chain:"black_powder"}', loads)
        self.assertNotRegex(loads,r'container\.\S*\s+minecraft:gunpowder(?:\s|$)')

    def test_pack_does_not_install_itself_from_load(self):
        self.assertNotIn('installed:1b}',self.functions['load'].split('execute if data storage')[0])
        self.assertIn('execute unless data storage nsp_ck:config {schema:1,installed:1b} run return 0',self.functions['tick'])

class RecordingResult(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs); self.rows=[]; self.started={}
    def startTest(self,test): self.started[test.id()]=time.monotonic(); super().startTest(test)
    def record(self,test,status,detail=''):
        self.rows.append({'name':test.id(),'status':status,'seconds':max(0.0,time.monotonic()-self.started.get(test.id(),time.monotonic())),'detail':detail})
    def addSuccess(self,test): super().addSuccess(test); self.record(test,'passed')
    def addFailure(self,test,err): super().addFailure(test,err); self.record(test,'failure',self._exc_info_to_string(err,test))
    def addError(self,test,err): super().addError(test,err); self.record(test,'error',self._exc_info_to_string(err,test))
    def addSkip(self,test,reason): super().addSkip(test,reason); self.record(test,'skipped',reason)
    def addSubTest(self,test,subtest,err):
        super().addSubTest(test,subtest,err)
        if err is not None: self.record(subtest,'failure' if issubclass(err[0],test.failureException) else 'error',self._exc_info_to_string(err,test))

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--xml',required=True); parser.add_argument('--json',required=True)
    args=parser.parse_args()
    suite=unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result=unittest.TextTestRunner(verbosity=2,resultclass=RecordingResult).run(suite)
    report={'testsRun':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'successful':result.wasSuccessful(),'scope':'offline source/generated pack only; Minecraft NOT run','cases':result.rows}
    Path(args.json).write_text(json.dumps(report,indent=2),encoding='utf-8')
    root=ET.Element('testsuite',name='cannon_offline',tests=str(result.testsRun),failures=str(len(result.failures)),errors=str(len(result.errors)),skipped=str(len(result.skipped)))
    for row in result.rows:
        case=ET.SubElement(root,'testcase',name=row['name'],time=f"{row['seconds']:.6f}")
        if row['status']!='passed': ET.SubElement(case,row['status'] if row['status']!='skipped' else 'skipped').text=row['detail']
    ET.ElementTree(root).write(args.xml,encoding='utf-8',xml_declaration=True)
    return 0 if result.wasSuccessful() else 1
if __name__=='__main__': raise SystemExit(main())
