"""Source/negative-control unittest only: never execute a native library or graphics process."""
import ast
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import graphics_environment as p


class GraphicsEnvironmentTests(unittest.TestCase):
    def effects_forbidden(self):
        stack = contextlib.ExitStack()
        for target in ('graphics_environment.C.CDLL', 'graphics_environment.subprocess.Popen',
                       'graphics_environment.urllib.request.OpenerDirector.open'):
            stack.enter_context(patch(target, side_effect=AssertionError('native/process/network forbidden')))
        return stack

    def test_sources_parse(self):
        for name in ('graphics_environment.py', 'test_graphics_environment.py'):
            ast.parse((p.HOME / name).read_text(encoding='utf8'))

    def test_source_default_real_payload_validation_no_native_or_network(self):
        with self.effects_forbidden(), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(p.main([]), 0)
        actual = json.loads(output.getvalue())
        self.assertEqual(actual['status'], 'SOURCE_ONLY_GRAPHICS_NOT_RUN')
        self.assertIs(actual['minecraft_client_acceptance'], False)
        self.assertIs(actual['holdClearance'], False)

    def test_actual_windows_host_cannot_execute(self):
        if os.name != 'nt':
            self.skipTest('actual Windows negative control runs only on Windows')
        with self.effects_forbidden(), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(p.main(['--execute', '--reviewed-payload-sha256', 'a' * 64]), 1)
        self.assertEqual(json.loads(output.getvalue())['reason'], 'HOSTED_LINUX_X64_ONLY')

    def test_platform_refusal_precedes_all_side_effects(self):
        with patch.object(p.platform, 'system', return_value='Windows'), self.effects_forbidden():
            for action in (lambda: p.execute('a' * 64), p.egl_loader,
                           lambda: p.download_sdl(Path('unused')),
                           lambda: p.capture([], Path('unused'), 'unused', {})):
                with self.assertRaisesRegex(Exception, 'HOSTED_LINUX_X64_ONLY'):
                    action()

    def test_wsl_refused_by_reused_native_gate(self):
        with patch.object(p.platform, 'system', return_value='Linux'), \
             patch.object(p.platform, 'machine', return_value='x86_64'), \
             patch.dict(os.environ, {'WSL_INTEROP': 'present'}, clear=True), self.effects_forbidden():
            with self.assertRaisesRegex(RuntimeError, 'No WSL'):
                p.hosted_guard()

    def test_nonapproved_host_refused_by_reused_gate(self):
        with patch.object(p.platform, 'system', return_value='Linux'), \
             patch.object(p.platform, 'machine', return_value='x86_64'), \
             patch.dict(os.environ, {}, clear=True), self.effects_forbidden():
            with self.assertRaises(RuntimeError):
                p.hosted_guard()

    def test_exact_dispatch_main_actor_and_image_required(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            home = root / 'tools'
            home.mkdir()
            env = dict(p.HOST_FIELDS, GITHUB_WORKSPACE=str(root), GITHUB_RUN_ID='12345')
            with patch.object(p.calibration, 'hosted_gate'), \
                 patch.object(p.platform, 'system', return_value='Linux'), \
                 patch.object(p.platform, 'machine', return_value='x86_64'), patch.object(p, 'HOME', home), \
                 patch.dict(os.environ, env, clear=True), self.effects_forbidden():
                self.assertEqual(p.hosted_guard(), root.resolve())
                for key in p.HOST_FIELDS:
                    with self.subTest(field=key), patch.dict(os.environ, {key: 'unapproved'}):
                        with self.assertRaisesRegex(Exception, 'HOST_CONTEXT_' + key):
                            p.hosted_guard()
                for key in ('MESA_GL_VERSION_OVERRIDE', 'MESA_GLSL_VERSION_OVERRIDE', 'LD_PRELOAD', 'LD_AUDIT'):
                    with self.subTest(override=key), patch.dict(os.environ, {key: 'unapproved'}):
                        with self.assertRaisesRegex(Exception, 'LOADER_OR_VERSION_OVERRIDE_REFUSED'):
                            p.hosted_guard()

    def test_missing_reviewed_hash_refused_before_payload_or_effects(self):
        with patch.object(p, 'hosted_guard', return_value=p.HOME), \
             patch.object(p.calibration, 'validate_payload', side_effect=AssertionError('validation reached')) as validate, \
             self.effects_forbidden():
            for value in (None, '', 'a' * 63, 'A' * 64, '../payload'):
                with self.subTest(value=value), self.assertRaisesRegex(Exception, 'REVIEWED_PAYLOAD_SHA256_REQUIRED'):
                    p.execute(value)
            validate.assert_not_called()

    def test_payload_drift_refused_before_native_effects(self):
        with patch.object(p, 'hosted_guard', return_value=p.HOME), \
             patch.object(p.calibration, 'validate_payload', side_effect=RuntimeError('Reviewed source payload drift')), \
             self.effects_forbidden():
            with self.assertRaisesRegex(RuntimeError, 'Reviewed source payload drift'):
                p.execute('a' * 64)

    def test_official_archive_pin_matches_authentic_metadata(self):
        self.assertEqual(p.pinned_archive_metadata(), p.ARCHIVE)
        self.assertEqual(p.ARCHIVE['size'], 1665811)
        self.assertLessEqual(p.ARCHIVE['size'], 2_000_000)
        self.assertEqual(p.SDL_SIZE, 4104744)
        self.assertEqual(p.MEMBER, 'linux/x64/org/lwjgl/sdl/libSDL3.so')

    def test_wrong_archive_metadata_refused_without_network(self):
        data = {'libraries': [{'name': 'org.lwjgl:lwjgl-sdl:3.4.3:natives-linux',
                              'downloads': {'artifact': dict(p.ARCHIVE, sha1='0' * 40)}}]}
        with patch.object(Path, 'read_text', return_value=json.dumps(data)), self.effects_forbidden():
            with self.assertRaisesRegex(Exception, 'PINNED_SDL_ARCHIVE_DRIFT'):
                p.pinned_archive_metadata()

    def test_redirect_never_follows_unreviewed_url(self):
        with self.assertRaisesRegex(RuntimeError, 'OFFICIAL_ARCHIVE_REDIRECT_REFUSED'):
            p.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://other.invalid/')

    def test_oversized_download_rejected_before_any_archive_write(self):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.geturl.return_value = p.ARCHIVE['url']
        response.headers = {'Content-Length': str(p.ARCHIVE['size'] + 1)}
        opener = Mock()
        opener.open.return_value = response
        with patch.object(p, 'hosted_guard'), patch.object(p.urllib.request, 'build_opener', return_value=opener), \
             tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(Exception, 'SDL_ARCHIVE_CONTENT_LENGTH_DRIFT'):
                p.download_sdl(root)
            self.assertEqual(list(root.iterdir()), [])
            response.read.assert_not_called()

    def test_hash_mismatch_never_extracts_library(self):
        response = io.BytesIO(b'not-an-archive')
        response.geturl = lambda: p.ARCHIVE['url']
        response.headers = {}
        opener = Mock()
        opener.open.return_value = response
        with patch.object(p, 'hosted_guard'), patch.object(p.urllib.request, 'build_opener', return_value=opener), \
             tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(Exception, 'SDL_ARCHIVE_SIZE_OR_SHA1_MISMATCH'):
                p.download_sdl(root)
            self.assertEqual(list(root.iterdir()), [])

    def test_environment_only_allowlist_and_exact_safe_values(self):
        result = p.environment_values({'GITHUB_TOKEN': 'never-output', 'HOME': 'private'})
        self.assertEqual(set(result), set(p.ENV_NAMES))
        self.assertNotIn('never-output', json.dumps(result))
        for key, value in (('SDL_EGL_LIBRARY', '/tmp/evil.so'), ('SDL_OPENGL_LIBRARY', 'evil'),
                           ('LD_LIBRARY_PATH', '/tmp/private-secret'), ('SDL_VIDEO_DRIVER', 'wayland'),
                           ('GALLIUM_DRIVER', 'zink')):
            with self.subTest(key=key), self.assertRaisesRegex(Exception, 'UNREVIEWED_GRAPHICS_ENV_'):
                p.environment_values({key: value})
        self.assertEqual(p.environment_values({'LD_LIBRARY_PATH': '/usr/lib/x86_64-linux-gnu:/lib64'})[
            'LD_LIBRARY_PATH'], '/usr/lib/x86_64-linux-gnu:/lib64')

    def test_probe_children_receive_no_tokens_or_loader_overrides(self):
        with patch.dict(os.environ, {'GITHUB_WORKSPACE': '/home/runner/work/repo/repo', 'GITHUB_RUN_ID': '123',
                                     'GITHUB_TOKEN': 'secret', 'PYTHONPATH': '/evil', 'SDL_VIDEO_FORCE_EGL': '0'}, clear=True):
            env = p.child_env(':31')
        for forbidden in ('GITHUB_TOKEN', 'PYTHONPATH', 'LD_PRELOAD', 'SDL_EGL_LIBRARY', 'SDL_OPENGL_LIBRARY'):
            self.assertNotIn(forbidden, env)
        self.assertEqual(env['DISPLAY'], ':31')
        self.assertEqual(env['LIBGL_ALWAYS_SOFTWARE'], '1')
        self.assertEqual(env['GALLIUM_DRIVER'], 'llvmpipe')
        self.assertEqual(env['SDL_VIDEO_DRIVER'], 'x11')
        self.assertNotIn('secret', json.dumps(env))

    def test_stop_only_owned_handle_terminate_and_kill_fallback(self):
        process = Mock(pid=1234)
        process.poll.side_effect = [None, -9]
        process.wait.side_effect = [p.subprocess.TimeoutExpired('owned', 5), -9]
        actual = p.stop_owned(process)
        process.terminate.assert_called_once_with()
        process.kill.assert_called_once_with()
        self.assertEqual(actual['final_exit'], -9)
        self.assertTrue(actual['kill_sent'])

    def test_already_exited_process_is_never_signalled(self):
        process = Mock(pid=1234)
        process.poll.return_value = 0
        actual = p.stop_owned(process)
        process.terminate.assert_not_called()
        process.kill.assert_not_called()
        self.assertEqual(actual['final_exit'], 0)

    def test_owned_cleanup_requires_observed_exit(self):
        process = Mock(pid=1234)
        process.poll.return_value = None
        with self.assertRaisesRegex(Exception, 'OWNED_PROCESS_EXIT_NOT_OBSERVED'):
            p.stop_owned(process)

    def test_no_install_runtime_or_context_downgrade_and_no_acceptance(self):
        source = (p.HOME / 'graphics_environment.py').read_text(encoding='utf8')
        for forbidden in ('apt-get', 'pip install', 'prepare(', 'extractall(', 'killpg(', 'os.kill(', 'SDL_GL_SetAttribute'):
            self.assertNotIn(forbidden, source)
        self.assertIn("str(HOME / 'real_sdl_probe.py')", source)
        self.assertIn("'800x450x24'", source)
        self.assertIn("'-displayfd'", source)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                for key, value in zip(node.keys, node.values):
                    if isinstance(key, ast.Constant) and key.value in ('minecraft_client_acceptance', 'holdClearance'):
                        self.assertIsInstance(value, ast.Constant)
                        self.assertIs(value.value, False)


    def test_isolated_egl_env_is_accepted_only_when_explicitly_approved(self):
        approved={'SDL_EGL_LIBRARY':'/home/runner/work/repo/repo/run/egl-runtime/libEGL.so.1.1.0','__EGL_VENDOR_LIBRARY_FILENAMES':'/home/runner/work/repo/repo/run/egl-runtime/50_mesa.owned.json'}
        with self.effects_forbidden():
            with self.assertRaises(p.ProbeError):p.environment_values(approved)
            observed=p.environment_values(approved,approved)
            self.assertEqual(observed['SDL_EGL_LIBRARY'],approved['SDL_EGL_LIBRARY'])
            self.assertEqual(observed['__EGL_VENDOR_LIBRARY_FILENAMES'],approved['__EGL_VENDOR_LIBRARY_FILENAMES'])
            with self.assertRaises(p.ProbeError):p.environment_values(dict(approved,SDL_EGL_LIBRARY='/unapproved/library'),approved)
            with self.assertRaises(p.ProbeError):p.environment_values(approved,dict(approved,LD_PRELOAD='/forbidden'))


if __name__ == '__main__':
    unittest.main()
