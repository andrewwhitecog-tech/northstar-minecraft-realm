"""Pure source/guard tests. No GLX/X11 libraries or native renderer called."""
import ast,contextlib,io,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
import real_glx_probe as p
ROOT=Path(__file__).resolve().parent
class SourceTests(unittest.TestCase):
 def env(self):return {'CI':'true','GITHUB_ACTIONS':'true','RUNNER_ENVIRONMENT':'github-hosted','RUNNER_OS':'Linux','ImageOS':'ubuntu24','GITHUB_EVENT_NAME':'workflow_dispatch','GITHUB_REF':'refs/heads/main','GITHUB_REPOSITORY':'andrewwhitecog-tech/northstar-minecraft-realm','NSP_ALLOW_CLOUD_SURVIVAL_CALIBRATION':'1','DISPLAY':':99','LIBGL_ALWAYS_SOFTWARE':'1','GALLIUM_DRIVER':'llvmpipe'}
 def test_python_source_ast(self):
  for name in ('real_glx_probe.py','native_calibration.py'):ast.parse((ROOT/name).read_text())
 def test_default_no_native_calls(self):
  with patch.object(sys,'argv',['real_glx_probe.py']),patch.object(p.C,'CDLL',side_effect=AssertionError('native forbidden')),contextlib.redirect_stdout(io.StringIO()) as output:self.assertEqual(p.main(),0)
  self.assertEqual(json.loads(output.getvalue())['status'],'SOURCE_ONLY_GLX_NOT_RUN')
 def test_windows_execution_rejected_before_library_load(self):
  with patch.object(p.platform,'system',return_value='Windows'),patch.object(p.C,'CDLL',side_effect=AssertionError('native forbidden')):
   with self.assertRaisesRegex(p.ProbeError,'HOSTED_LINUX_ONLY'):p.probe()
 def test_host_context_accepts_only_explicit_hosted_env(self):
  env=self.env();p.hosted_guard(env,'Linux','kernel')
  for key,value in [('RUNNER_ENVIRONMENT','self-hosted'),('GITHUB_EVENT_NAME','pull_request'),('DISPLAY','remote:0'),('GALLIUM_DRIVER','zink')]:
   with self.subTest(key=key):
    bad=dict(env);bad[key]=value
    with self.assertRaises(p.ProbeError):p.hosted_guard(bad,'Linux','kernel')
  with self.assertRaises(p.ProbeError):p.hosted_guard(env,'Linux','microsoft')
 def test_no_version_override_or_package_install(self):
  source=(ROOT/'real_glx_probe.py').read_text();workflow=(ROOT/'workflow.template.yml').read_text();self.assertNotIn('VERSION_OVERRIDE',source);self.assertNotIn('apt-get',workflow);self.assertNotIn('NSP_APT_PACKAGES',workflow);self.assertIn('CDLL(\'libX11.so.6\')',source);self.assertIn('CDLL(\'libGL.so.1\')',source)
 def test_native_judge_helpers_preserved(self):
  before=ast.parse((ROOT/'fixtures/native_judge_before_noapt.txt').read_text());after=ast.parse((ROOT/'native_calibration.py').read_text())
  for name in ('route','parse_score','parse_pos','tool','identity','convergence','settle','persisted'):
   b=next(n for n in ast.walk(before) if isinstance(n,ast.FunctionDef) and n.name==name);a=next(n for n in ast.walk(after) if isinstance(n,ast.FunctionDef) and n.name==name);self.assertEqual(ast.dump(b),ast.dump(a),name)
 def test_driver_requires_observed_probe_not_stdout_label(self):
  source=(ROOT/'native_calibration.py').read_text();self.assertIn("glx.get('gl_clear_error')==0",source);self.assertIn("'llvmpipe' in glx.get('renderer','').lower()",source);self.assertIn("g.returncode==0",source);self.assertNotIn("shutil.which('glxinfo')",source)
if __name__=='__main__':unittest.main()
