"""Source/transport tests only. Never substitute these for actual Minecraft execution."""
import json, struct, unittest, unittest.mock
from pathlib import Path
import ci_runner as runner

class FakeWire:
    def __init__(self,raw):self.raw=bytearray(raw);self.sent=[]
    def recv(self,n):
        n=min(n,3);out=bytes(self.raw[:n]);del self.raw[:n];return out
    def sendall(self,b):self.sent.append(b)
    def close(self):pass

def packet(i,t,body):
    b=struct.pack('<ii',i,t)+body.encode()+b'\0\0'
    return struct.pack('<i',len(b))+b

class PreparationTests(unittest.TestCase):
    def test_fixture_builds_seventeen_real_native_item_entries(self):
        text=runner.fixture_command({'x':725,'y':73,'z':153,'item':'coal'})
        self.assertTrue(text.startswith('setblock 725 73 153 minecraft:barrel{Items:['))
        self.assertEqual(text.count('count:64'),17)
        self.assertIn('{Slot:16b,id:"minecraft:coal",count:64}',text)
    def test_original_literal_source_grammar_is_narrow(self):
        self.assertEqual(runner.parse_literal('{x:725,y:73,z:153,item:"coal"}')['x'],725)
        for bad in ['{x:"725",y:73,z:153,item:"coal"}','{x:725,y:73,z:153,item:"coal",extra:1}']:
            with self.assertRaises(RuntimeError):runner.parse_literal(bad)
    def test_wrapper_calls_real_public_function_and_continues_parent(self):
        c={'function':'nsp_crafter_refill:trim','arguments_snbt':'{x:725,y:73,z:153,item:"coal"}'}
        lines=runner.wrapper_commands(c)
        expected='execute store result score #result nspmg store success score #success nspmg run function nsp_crafter_refill:trim '+c['arguments_snbt']
        self.assertEqual(lines.count(expected),1)
        call_at=lines.index(expected)
        self.assertLess(lines.index('scoreboard players reset #result nspmg'),call_at)
        self.assertLess(lines.index('scoreboard players reset #success nspmg'),call_at)
        self.assertEqual(lines[-1],'scoreboard players add #after nspmg 1')
        self.assertLess(call_at,len(lines)-1)
    def test_observed_native_score_and_unset_are_distinct_without_default_zero(self):
        # Actual responses retained from native run43031332423. No Minecraft outcome is simulated.
        self.assertEqual(runner.parse_native_score_response('#probe has 1 [nspmg]','#probe'),1)
        raw="Can't get value of nspmg for #original_result; none is set"
        self.assertIsNone(runner.parse_native_score_response(raw,'#original_result',True))
        with self.assertRaises(RuntimeError):runner.parse_native_score_response(raw,'#original_result')
        with self.assertRaises(RuntimeError):runner.parse_native_score_response('Running function nsp_mg_proof:original_trim','#original_result',True)
    def test_multiline_commands_and_unsupported_public_functions_are_refused(self):
        for c in [{'function':'nsp_crafter_refill:trim','arguments_snbt':'{}\nstop'},{'function':'nsp_owner_flight:check','arguments_snbt':'{}'}]:
            with self.assertRaises(RuntimeError):runner.wrapper_commands(c)
    def test_output_cannot_escape_owned_home(self):
        self.assertEqual(runner.confined(runner.HOME/'runs'),runner.HOME/'runs')
        with self.assertRaises(RuntimeError):runner.confined(runner.HOME.parent/'foreign')
    def test_function_path_rejects_traversal(self):
        with self.assertRaises(RuntimeError):runner.function_path(runner.HOME,'ns:../escape')
    def test_real_rcon_packet_parser_handles_fragmented_transport(self):
        r=object.__new__(runner.Rcon);r.s=FakeWire(packet(7,0,'native response'))
        self.assertEqual(r.receive(),(7,0,'native response'))
    def test_rcon_bad_lengths_and_terminators_fail_closed(self):
        r=object.__new__(runner.Rcon);r.s=FakeWire(struct.pack('<i',9))
        with self.assertRaises(RuntimeError):r.receive()
        bad=bytearray(packet(1,0,'x'));bad[-1]=1;r.s=FakeWire(bad)
        with self.assertRaises(RuntimeError):r.receive()
    def test_rcon_response_cannot_be_from_another_command(self):
        r=object.__new__(runner.Rcon);r.i=1;r.s=FakeWire(packet(999,0,'not ours'))
        with self.assertRaises(RuntimeError):r.cmd('list')
    def test_case_selection_does_not_claim_full_fifty_six(self):
        config=json.loads(runner.CONFIG.read_text(encoding='utf8'))
        plan=json.loads((runner.HOME/'cases.json').read_text(encoding='utf8'))
        chosen={c['label']for c in plan['cases']} & set(runner.SMOKE_LABELS)
        self.assertEqual(len(chosen),len(runner.SMOKE_LABELS))
        self.assertEqual(len(plan['cases'])-len(chosen),56-len(runner.SMOKE_LABELS))
    def test_denied_native_admission_cannot_disappear_two_unrun_cases(self):
        plan={'cases':[{'label':'a'},{'label':'b'},{'label':'c'}]}
        self.assertEqual(runner.remaining_labels(plan,[]),['a','b','c'])
        self.assertEqual(runner.remaining_labels(plan,['a']),['b','c'])



class HostedGateTests(unittest.TestCase):
    def test_native_gate_rejects_local_or_missing_hosted_context(self):
        with unittest.mock.patch.dict(runner.os.environ,{},clear=True):
            with self.assertRaises(RuntimeError):runner.require_hosted_ci()
    def test_native_source_globals_are_bound_before_any_server_boot(self):
        runner.assert_global_bindings()
        saved=runner.__dict__.pop('secrets')
        try:
            with self.assertRaisesRegex(RuntimeError,'secrets'):runner.assert_global_bindings()
        finally:runner.secrets=saved
    def test_manifest_verification_reads_real_bytes_and_rejects_unknown_files(self):
        import tempfile
        with tempfile.TemporaryDirectory(dir=runner.HOME) as folder:
            root=Path(folder);target=root/'source.txt';target.write_bytes(b'actual source')
            rows={'source.txt':runner.hash_file(target)}
            runner.validate_file_bindings(root,rows)
            target.write_bytes(b'changed source')
            with self.assertRaisesRegex(RuntimeError,'drift'):runner.validate_file_bindings(root,rows)
            target.write_bytes(b'actual source');(root/'unlisted.txt').write_bytes(b'not approved')
            with self.assertRaisesRegex(RuntimeError,'allowlist'):runner.validate_file_bindings(root,rows)
            with self.assertRaises(RuntimeError):runner.validate_file_bindings(root,{'../foreign':'0'*64})
    def test_proof_pack_rejects_unlisted_load_hook_and_nested_runtime_name(self):
        import tempfile
        with tempfile.TemporaryDirectory(dir=runner.HOME) as folder:
            root=Path(folder);proof=root/'proof_pack';proof.mkdir()
            p=proof/'pack.mcmeta';p.write_bytes(b'{}');rows={'proof_pack/pack.mcmeta':runner.hash_file(p)}
            runner.validate_file_bindings(root,rows)
            hook=proof/'data/minecraft/tags/function/load.json';hook.parent.mkdir(parents=True);hook.write_bytes(b'{"values":[]}')
            with self.assertRaisesRegex(RuntimeError,'allowlist'):runner.validate_file_bindings(root,rows)
            hook.unlink();hidden=proof/'data/test/function/runs/hidden.mcfunction';hidden.parent.mkdir(parents=True);hidden.write_text('say unlisted')
            with self.assertRaisesRegex(RuntimeError,'allowlist'):runner.validate_file_bindings(root,rows)
    def test_symlinked_proof_source_is_refused(self):
        import tempfile
        with tempfile.TemporaryDirectory(dir=runner.HOME) as folder:
            root=Path(folder);target=root/'real';target.write_bytes(b'actual')
            try:(root/'alias').symlink_to(target)
            except OSError:self.skipTest('OS symlink privilege unavailable; hostedLinuxmustexecute')
            with self.assertRaisesRegex(RuntimeError,'alias'):runner.validate_file_bindings(root,{'real':runner.hash_file(target),'alias':runner.hash_file(target)})


class ExtendedObservationTests(unittest.TestCase):
    def test_observation_requires_exact_unset_return_and_storage_equality(self):
        from trim_extension import assert_same_observation
        a={'items':'actual Items response','storage':'actual first response','result':None,'success':None}
        assert_same_observation(a,dict(a))
        for key,value in [('result',0),('success',0),('storage','different first response'),('items','different Items response')]:
            with self.subTest(key=key):
                b=dict(a);b[key]=value
                with self.assertRaises(RuntimeError):assert_same_observation(a,b)
    def test_unknown_native_refusal_evidence_fails_instead_of_guessing(self):
        from trim_extension import rejection_kind
        with self.assertRaises(RuntimeError):rejection_kind('Running function nsp_crafter_refill:trim',False,True)
        with self.assertRaises(RuntimeError):rejection_kind('Expected integer',False,False)
        self.assertEqual(rejection_kind('Expected integer',False,True),'NATIVE_PARSER_REFUSAL')
        self.assertEqual(rejection_kind('Failed to instantiate macro: missing argument z',False,True),'NATIVE_INSTANTIATION_REFUSAL')
        self.assertEqual(rejection_kind('Running function nsp_crafter_refill:trim',True,False),'GUARD_REJECTION')
    def test_all_differential_wrappers_compare_same_arguments_in_both_frames(self):
        plan=json.loads((runner.HOME/'cases.json').read_text())
        for c in plan['cases']:
            if c.get('native_mode')!='DIFFERENTIAL_LITERAL':continue
            guarded=(runner.HOME/'proof_pack/data/nsp_mg_proof/function'/ (c['label']+'.mcfunction')).read_text()
            original=(runner.HOME/'proof_pack/data/nsp_mg_proof/function'/ ('original_'+c['label']+'.mcfunction')).read_text()
            self.assertIn('run function nsp_crafter_refill:trim '+c['arguments_snbt'],guarded)
            self.assertIn('run function nsp_mg_proof:original_trim '+c['arguments_snbt'],original)
            self.assertIn('scoreboard players add #original_after nspmg 1',original)
    def test_only_concrete_public_trim_cases_are_dispatched(self):
        plan=json.loads((runner.HOME/'cases.json').read_text());cases={c['label']:c for c in plan['cases']}
        for label in runner.SMOKE_LABELS:
            c=cases[label];self.assertEqual(c['function'],'nsp_crafter_refill:trim')
            self.assertNotIn('owner_flight',c['arguments_snbt']);self.assertIn('arguments_snbt',c)
        for label in ('trim_signed_int_boundaries','trim_x_long','trim_spelling_hex_literal','trim_item_newline','trim_item_close_command_root'):
            self.assertNotIn(label,runner.SMOKE_LABELS)


if __name__=='__main__':unittest.main(verbosity=2)
