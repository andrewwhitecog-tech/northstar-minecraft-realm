"""Real source/parser/unit checks only; never a fabricated Minecraft outcome."""
import gzip, hashlib, importlib, io, json, os, struct, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import native_calibration as cal
import download_runtime as runtime
from nbt_region import Nbt, fresh_servers_dat, read_dat

class SourceTests(unittest.TestCase):
    def test_graphics_failure_requires_both_backends(self):
        with tempfile.TemporaryDirectory(dir=cal.HOME) as tmp:
            p=Path(tmp)/'client.log'
            self.assertIsNone(cal.client_graphics_failure(p))
            p.write_text('Failed to create backend OpenGL\nVulkan initialized')
            self.assertIsNone(cal.client_graphics_failure(p))
            p.write_text('Failed to create backend OpenGL\nFailed to create backend Vulkan')
            self.assertIn('both graphics backends',cal.client_graphics_failure(p))
    def test_graphics_failure_reads_a_bounded_tail(self):
        with tempfile.TemporaryDirectory(dir=cal.HOME) as tmp:
            p=Path(tmp)/'client.log'
            p.write_bytes(b'x'*100000+b'Failed to create backend OpenGL\nFailed to create backend Vulkan\n')
            self.assertIsNotNone(cal.client_graphics_failure(p))
            p.write_bytes(b'Failed to create backend OpenGL\nFailed to create backend Vulkan\n'+b'x'*100000)
            self.assertIsNone(cal.client_graphics_failure(p))
    def test_public_hosted_gate_rejects_local_or_missing_context(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaises(RuntimeError):cal.hosted_gate()
    def test_hosted_gate_rejects_each_wsl_environment_indicator(self):
        for key in ('WSL_DISTRO_NAME','WSL_INTEROP'):
            with self.subTest(key=key),patch.dict(os.environ,{key:''},clear=True):
                with self.assertRaisesRegex(RuntimeError,'WSL/Microsoft-kernel'):cal.hosted_gate()
    def test_hosted_gate_rejects_microsoft_kernel(self):
        with patch.dict(os.environ,{},clear=True),patch.object(cal.platform,'release',return_value='6.6.87.2-microsoft-standard-WSL2'):
            with self.assertRaisesRegex(RuntimeError,'WSL/Microsoft-kernel'):cal.hosted_gate()
    def _valid_alias_payload(self,root,relative):
        harness=cal.HOME/'harness/nsp-route-walk-heldproof-v02.jar'
        (root/'owned-harness.jar').write_bytes(harness.read_bytes())
        (root/'LOCK.json').write_text(json.dumps({'harness':{'path':'owned-harness.jar','sha256':runtime.file_hash(harness)}}))
        (root/'PAYLOAD.json').write_text(json.dumps({'nativeExecution':'NOT_RUN','files':{relative:runtime.file_hash(root/relative)}}))
    def test_payload_rejects_parent_alias_before_resolving(self):
        with tempfile.TemporaryDirectory(dir=cal.HOME) as tmp:
            root=Path(tmp);real=root/'real';real.mkdir();(real/'leaf.txt').write_text('owned fixture')
            alias=root/'alias'
            if os.name=='nt':
                import _winapi
                _winapi.CreateJunction(str(real),str(alias))
            else:alias.symlink_to(real,target_is_directory=True)
            try:
                self._valid_alias_payload(root,'alias/leaf.txt')
                with patch.object(cal,'HOME',root):
                    with self.assertRaisesRegex(RuntimeError,'Payload alias/escape'):cal.validate_payload()
            finally:
                if os.name=='nt':alias.rmdir()
                else:alias.unlink()
    def test_payload_rejects_file_symlink_before_resolving(self):
        with tempfile.TemporaryDirectory(dir=cal.HOME) as tmp:
            root=Path(tmp);(root/'real.txt').write_text('owned fixture');alias=root/'alias.txt'
            try:alias.symlink_to(root/'real.txt')
            except OSError as exc:
                if os.name=='nt' and exc.winerror==1314:self.skipTest('Windows token cannot create file symlinks; actual parent junction case still runs')
                raise
            self._valid_alias_payload(root,'alias.txt')
            with patch.object(cal,'HOME',root):
                with self.assertRaisesRegex(RuntimeError,'Payload alias/escape'):cal.validate_payload()
    def test_official_jvm_path_uses_existing_native_java_subdirectory(self):
        meta=json.loads((cal.HOME/'metadata/minecraft-26.3.json').read_text())
        values={'natives_directory':'OWN_NATIVE_ROOT','launcher_name':'test','launcher_version':'1','classpath':'OWN_CLASSPATH'}
        args=runtime.arguments(meta['arguments']['jvm'],values,{})
        self.assertIn('-Djava.library.path=OWN_NATIVE_ROOT/java',args)

    def test_actual_compiled_harness_pin_and_identity(self):
        import zipfile
        lock=json.loads((cal.HOME/'LOCK.json').read_text());p=cal.HOME/lock['harness']['path']
        self.assertEqual(runtime.file_hash(p),'b19fefcfee9980099dbf3ebd8426fe8da1f13346c37c347723b6ebc4cc99b532')
        with zipfile.ZipFile(p) as z:
            mod=json.loads(z.read('fabric.mod.json'));self.assertEqual(mod['id'],'nsp_route_walk');self.assertEqual(mod['environment'],'client')
            self.assertFalse(any('fabricmc' in n for n in z.namelist()))
    def test_actual_pinned_metadata_is_26_3_java25_and_official_knot(self):
        lock=json.loads((cal.HOME/'LOCK.json').read_text())
        for name,pin in lock['metadata'].items():self.assertEqual(runtime.file_hash(cal.HOME/'metadata'/name),pin['sha256'])
        meta=json.loads((cal.HOME/'metadata/minecraft-26.3.json').read_text())
        self.assertEqual(meta['id'],'26.3');self.assertEqual(meta['javaVersion']['majorVersion'],25)
        self.assertEqual(json.loads((cal.HOME/'metadata/fabric-client-0.20.1.json').read_text())['mainClass'],'net.fabricmc.loader.impl.launch.knot.KnotClient')
    def test_linux_rule_order_and_features_are_used(self):
        self.assertTrue(runtime.rules_allow({'rules':[{'action':'allow','os':{'name':'linux'}}]}))
        self.assertFalse(runtime.rules_allow({'rules':[{'action':'allow','os':{'name':'windows'}}]}))
        self.assertFalse(runtime.rules_allow({'rules':[{'action':'allow'},{'action':'disallow','os':{'name':'linux'}}]}))
        self.assertFalse(runtime.rules_allow({'rules':[{'action':'allow','features':{'is_demo_user':True}}]},{}))
    def test_official_game_arguments_resolve_with_local_offline_identity(self):
        meta=json.loads((cal.HOME/'metadata/minecraft-26.3.json').read_text())
        names=['auth_player_name','version_name','game_directory','assets_root','assets_index_name','auth_uuid','auth_access_token','clientid','auth_xuid','version_type','resolution_width','resolution_height','quickPlayPath','quickPlayMultiplayer']
        values={n:'SYNTHETIC_VALUE' for n in names};values['quickPlayMultiplayer']='127.0.0.1:27091'
        args=runtime.arguments(meta['arguments']['game'],values,{'has_custom_resolution':True,'has_quick_plays_support':True,'is_quick_play_multiplayer':True})
        self.assertIn('--quickPlayMultiplayer',args);self.assertIn('127.0.0.1:27091',args)
        self.assertNotIn('--demo',args)
        with self.assertRaises(RuntimeError):runtime.arguments(['UNKNOWN_'+chr(36)+'{unexpected}'],{}, {})
    def test_native_score_responses_have_no_default_or_wrong_name_acceptance(self):
        self.assertEqual(cal.parse_score('#tick has 12 [nspcal]','#tick'),12)
        for value in ('not loaded','#other has 12 [nspcal]','#tick has 12 [different]'):
            with self.assertRaises(RuntimeError):cal.parse_score(value,'#tick')
    def test_real_native_position_response_format_and_invalid_values(self):
        self.assertEqual(cal.parse_pos('Synthetic has the following entity data: [4.5d, 65.0d, 26.5d]'),[4.5,65.0,26.5])
        with self.assertRaises(RuntimeError):cal.parse_pos('Unknown player')
        with self.assertRaises(RuntimeError):cal.parse_pos('contents: [NaN, 1, 2]')
    def test_same_material_three_legs_and_held_await_resync_contract(self):
        limits={'awaitTicks':1200,'holdTicks':240}
        self.assertEqual([p for _,_,p in cal.TARGETS],[False,True,False])
        for label,target,protected in cal.TARGETS:
            steps=cal.route('synthetic',label,target,protected,limits)
            digs=[s for s in steps if 'dighold' in s]
            self.assertEqual(digs[0],{'dighold':list(target),'face':'SOUTH','ticks':240})
            self.assertEqual(len(digs),2 if protected else 1)
            if protected:self.assertEqual(digs[1]['ticks'],3)
            self.assertTrue(all(s['ticks']==1200 for s in steps if 'await' in s))
    def test_fresh_servers_file_is_actual_compressed_nbt_not_private_profile_copy(self):
        with tempfile.TemporaryDirectory(dir=cal.HOME) as tmp:
            p=Path(tmp)/'servers.dat';fresh_servers_dat(p,'127.0.0.1:27091')
            data=read_dat(p);self.assertEqual(data['servers'][0]['ip'],'127.0.0.1:27091');self.assertEqual(len(data['servers']),1)
    def test_nbt_reader_refuses_truncation_instead_of_fake_air(self):
        with self.assertRaises(ValueError):Nbt(b'\x0a\0\0\x03\0\x01x').root()
    def test_public_download_path_cannot_escape_owned_root(self):
        with self.assertRaises(RuntimeError):runtime.safe_child(cal.HOME,'../foreign')


    def test_saved_region_palette_reader_decodes_padded_long_data(self):
        from nbt_region import block_state
        import zlib
        def text(s):
            b=s.encode();return struct.pack('>H',len(b))+b
        def named(t,n,b):return bytes([t])+text(n)+b
        air=named(8,'Name',text('minecraft:air'))+b'\0'
        props=named(8,'axis',text('y'))+b'\0'
        bone=named(8,'Name',text('minecraft:bone_block'))+named(10,'Properties',props)+b'\0'
        packed=[0]*256;at=(65%16)*256+(24%16)*16+(24%16);packed[at//16]=1<<((at%16)*4)
        states=named(9,'palette',b'\x0a'+struct.pack('>i',2)+air+bone)+named(12,'data',struct.pack('>i',len(packed))+b''.join(struct.pack('>q',v) for v in packed))+b'\0'
        section=named(1,'Y',b'\x04')+named(10,'block_states',states)+b'\0'
        root=b'\x0a\0\0'+named(9,'sections',b'\x0a'+struct.pack('>i',1)+section)+b'\0'
        raw=zlib.compress(root);entry=struct.pack('>I',len(raw)+1)+b'\x02'+raw
        header=bytearray(8192);index=1+32;header[index*4:index*4+4]=b'\0\0\x02\x01'
        with tempfile.TemporaryDirectory(dir=cal.HOME) as tmp:
            world=Path(tmp);folder=world/'dimensions/minecraft/overworld/region';folder.mkdir(parents=True)
            (folder/'r.0.0.mca').write_bytes(bytes(header)+entry+b'\0'*(4096-len(entry)))
            self.assertEqual(block_state(world,24,65,24),cal.EXPECTED_BONE)
            self.assertEqual(block_state(world,25,65,24),{'Name':'minecraft:air'})


    def test_all_runtime_source_global_names_are_bound_including_native_only_paths(self):
        import builtins, symtable
        import nbt_region
        for module in (cal,runtime,nbt_region):
            table=symtable.symtable(Path(module.__file__).read_text(),module.__file__,'exec')
            allowed=set(vars(module))|set(vars(builtins));missing=set()
            def inspect(t):
                for symbol in t.get_symbols():
                    if symbol.is_referenced() and symbol.is_global() and symbol.get_name() not in allowed:missing.add(symbol.get_name())
                for child in t.get_children():inspect(child)
            inspect(table);self.assertEqual(missing,set(),module.__name__)
    def test_actual_public_runtime_dependency_graph_is_pinned_for_linux(self):
        from urllib.parse import urlparse
        meta=json.loads((cal.HOME/'metadata/minecraft-26.3.json').read_text());selected=[x for x in meta['libraries'] if runtime.rules_allow(x)]
        self.assertGreater(len(selected),30)
        for lib in selected:
            self.assertNotIn('classifiers',lib.get('downloads',{}))
            a=lib['downloads']['artifact'];self.assertEqual(len(a['sha1']),40)
            self.assertIn(urlparse(a['url']).hostname,runtime.ALLOWED_HOSTS)
        known={}
        for file in ('fabric-client-0.20.1.json','fabric-server-0.20.1.json'):
            profile=json.loads((cal.HOME/'metadata'/file).read_text())
            for lib in profile['libraries']:
                if lib['name'] in known:self.assertEqual(known[lib['name']],lib)
                known[lib['name']]=lib

if __name__=='__main__':unittest.main(verbosity=2)
