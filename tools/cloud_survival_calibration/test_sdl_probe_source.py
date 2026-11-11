"""Pure SDL3 source and guard checks. No SDL, GL, or native libraries execute."""
import ast,contextlib,copy,io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import real_sdl_probe as p
ROOT=Path(__file__).resolve().parent
class SDLSourceTests(unittest.TestCase):
 def good(self):
  return {'schema':p.SCHEMA,'status':'REAL_SDL_CONTEXT_QUERIED','minecraft_client_acceptance':False,'mode':'glx','video_force_egl':'0','driver':'x11','renderer':'llvmpipe (LLVM)','vendor':'Mesa','version':'4.5 core Mesa','gl_clear_error':0,'requested_attributes':[list(x)for x in p.ATTRS],'requested_window_flags':8226,'attributes':{'17':4,'18':5,'20':1,'19':2,'22':1},'gl_context':{'major':4,'minor':5,'profile_mask':1,'flags':1},'window_flags':8226,'sdl_version':[3,2,8],'cleanup_errors':[],'hint_priority':2,'hint_set_result':True,'opengl_library':'libGL.so.1','opengl_library_loaded':True}
 def test_sources_parse(self):
  for name in('real_sdl_probe.py','test_sdl_probe_source.py'):ast.parse((ROOT/name).read_text(encoding='utf8'))
 def test_source_only_default_never_loads_library(self):
  with patch.object(p.C,'CDLL',side_effect=AssertionError('native forbidden')),contextlib.redirect_stdout(io.StringIO())as output:self.assertEqual(p.main([]),0)
  self.assertEqual(json.loads(output.getvalue())['status'],'SOURCE_ONLY_SDL_NOT_RUN')
 def test_actual_host_guard_rejects_windows_before_cdll(self):
  with patch('real_glx_probe.platform.system',return_value='Windows'),patch.object(p.C,'CDLL',side_effect=AssertionError('native forbidden'))as load:
   result=p.probe(None,'glx')
  load.assert_not_called();self.assertEqual(result['stage'],'hosted_guard');self.assertEqual(result['reason'],'HOSTED_LINUX_ONLY');self.assertFalse(p.observation_ok(result))
 def test_host_gate_failure_cannot_reach_path_or_native_load(self):
  with patch.object(p,'hosted_guard',side_effect=p.ProbeError('HOST_CONTEXT_CI')),patch.object(p,'native_library',side_effect=AssertionError('path reached'))as paths,patch.object(p.C,'CDLL',side_effect=AssertionError('native forbidden'))as load:result=p.probe(None,'egl')
  paths.assert_not_called();load.assert_not_called();self.assertEqual(result['reason'],'HOST_CONTEXT_CI')
 def test_guard_precedes_cdll_and_hint_precedes_init(self):
  tree=ast.parse((ROOT/'real_sdl_probe.py').read_text(encoding='utf8'));probe=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='probe')
  calls=[n for n in ast.walk(probe)if isinstance(n,ast.Call)]
  guard=next(n.lineno for n in calls if isinstance(n.func,ast.Name)and n.func.id=='hosted_guard');load=next(n.lineno for n in calls if isinstance(n.func,ast.Attribute)and n.func.attr=='CDLL')
  hint=next(n.lineno for n in calls if isinstance(n.func,ast.Attribute)and n.func.attr=='SDL_SetHintWithPriority');init=next(n.lineno for n in calls if isinstance(n.func,ast.Attribute)and n.func.attr=='SDL_Init')
  self.assertLess(guard,load);self.assertLess(hint,init)
  gl_load=next(n.lineno for n in calls if isinstance(n.func,ast.Attribute)and n.func.attr=='SDL_GL_LoadLibrary');attrs=next(n.lineno for n in calls if isinstance(n.func,ast.Attribute)and n.func.attr=='SDL_GL_SetAttribute');window=next(n.lineno for n in calls if isinstance(n.func,ast.Attribute)and n.func.attr=='SDL_CreateWindow')
  self.assertLess(init,gl_load);self.assertLess(gl_load,attrs);self.assertLess(gl_load,window)
 def test_explicit_gl_reference_released_after_window_before_video(self):
  source=(ROOT/'real_sdl_probe.py').read_text(encoding='utf8')
  cleanup=source[source.index('finally:'):]
  self.assertLess(cleanup.index("('destroy_context'"),cleanup.index("('unload_gl_library'"));self.assertLess(cleanup.index("('destroy_window'"),cleanup.index("('unload_gl_library'"));self.assertLess(cleanup.index("('unload_gl_library'"),cleanup.index("('quit_video'"))
  self.assertIn("sdl.SDL_SetHintWithPriority(b'SDL_VIDEO_FORCE_EGL',hint,2)",source);self.assertIn("sdl.SDL_GL_LoadLibrary(b'libGL.so.1')",source)
 def test_exact_library_and_containment(self):
  with tempfile.TemporaryDirectory()as tmp:
   root=Path(tmp);home=root/'runtime/natives';(home/'java').mkdir(parents=True);library=home/'java/libSDL3.so';library.write_bytes(b'fixture-not-loaded');env={'GITHUB_WORKSPACE':str(root)}
   self.assertEqual(p.native_library(home,'glx',env),library);self.assertEqual(p.native_library(home,'egl',env),library)
   for path,mode,e in[(root,'glx',env),(home,'bad',env),(home,'glx',{}),(Path('relative'),'glx',env),(root/'runtime/../runtime/natives','glx',env)]:
    with self.subTest(path=path,mode=mode),self.assertRaises((p.ProbeError,FileNotFoundError)):p.native_library(path,mode,e)
   library.unlink()
   with self.assertRaises((p.ProbeError,FileNotFoundError)):p.native_library(home,'glx',env)
 def test_linked_component_refused(self):
  with tempfile.TemporaryDirectory()as tmp:
   root=Path(tmp);home=root/'native';(home/'java').mkdir(parents=True);(home/'java/libSDL3.so').write_bytes(b'not-loaded')
   with patch.object(Path,'is_symlink',return_value=True),self.assertRaisesRegex(p.ProbeError,'LINKED'):p.native_library(home,'glx',{'GITHUB_WORKSPACE':str(root)})
 def test_good_observations_are_accepted_for_both_modes(self):
  for mode in('glx','egl'):
   report=self.good();report.update(mode=mode,video_force_egl='1'if mode=='egl'else'0');self.assertTrue(p.observation_ok(report))
 def test_missing_wrong_or_claim_only_observations_fail_closed(self):
  good=self.good()
  for key in good:
   bad=copy.deepcopy(good);del bad[key]
   with self.subTest(missing=key):self.assertFalse(p.observation_ok(bad))
  for key,value in [('status','PASS'),('minecraft_client_acceptance',True),('gl_clear_error',True),('gl_clear_error',1280),('driver','wayland'),('renderer','zink'),('mode','other'),('video_force_egl','1'),('sdl_version',[2,32,0]),('window_flags',2),('cleanup_errors',[{'reason':'failed'}]),('hint_priority',1),('hint_set_result',False),('opengl_library','libGLESv2.so.2'),('opengl_library_loaded',False)]:
   bad=copy.deepcopy(good);bad[key]=value
   with self.subTest(key=key,value=value):self.assertFalse(p.observation_ok(bad))
 def test_mandatory_context_attributes_cannot_be_lowered(self):
  good=self.good()
  for key,value in [('17',2),('18',True),('20',2),('19',0),('22',0)]:
   bad=copy.deepcopy(good);bad['attributes'][key]=value
   with self.subTest(key=key):self.assertFalse(p.observation_ok(bad))
  for key,value in [('major',2),('profile_mask',2),('flags',0)]:
   bad=copy.deepcopy(good);bad['gl_context'][key]=value
   with self.subTest(key=key):self.assertFalse(p.observation_ok(bad))
 def test_no_installs_or_context_downgrade(self):
  source=(ROOT/'real_sdl_probe.py').read_text(encoding='utf8');self.assertNotIn('apt-get',source);self.assertNotIn('pip install',source);self.assertEqual(p.ATTRS,((17,3),(18,3),(20,1),(19,2),(22,1)));self.assertEqual(p.WINDOW_FLAGS,8226)
 def test_invalid_mode_cli_rejected_without_native_load(self):
  with patch.object(p.C,'CDLL',side_effect=AssertionError('native forbidden')),contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):p.main(['--execute','--mode','bad'])
if __name__=='__main__':unittest.main()
