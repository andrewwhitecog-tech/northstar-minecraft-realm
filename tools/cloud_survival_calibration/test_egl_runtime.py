"""Pure unit/negative controls. No EGL/native library, package command or network executes."""
import ast
import contextlib
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import Mock, patch
import egl_runtime as p


class EglRuntimeTests(unittest.TestCase):
    def forbidden(self):
        stack = contextlib.ExitStack()
        for target in ('egl_runtime.C.CDLL', 'egl_runtime.subprocess.Popen',
                       'egl_runtime.urllib.request.OpenerDirector.open'):
            stack.enter_context(patch(target, side_effect=AssertionError('native/process/network forbidden')))
        return stack

    def fixture(self):
        raw = b'\x7fELF\x02\x01\x01' + b'\0' * 9 + b'\x03\x00\x3e\x00' + b'unit-fixture-only'
        pin = {'member': './usr/lib/x86_64-linux-gnu/unit-fixture.so', 'elf_bytes': len(raw),
               'elf_sha256': hashlib.sha256(raw).hexdigest()}
        return raw, pin

    def tar(self, entries):
        out = io.BytesIO()
        with tarfile.open(fileobj=out, mode='w') as archive:
            for name, raw, kind in entries:
                member = tarfile.TarInfo(name)
                member.type = kind
                if kind == tarfile.REGTYPE:
                    member.size = len(raw)
                    archive.addfile(member, io.BytesIO(raw))
                else:
                    member.linkname = '/untrusted/target'
                    archive.addfile(member)
        return out.getvalue()

    def closure(self):
        return ''.join(name + '\t' + version + '\tinstalled\tamd64\n' for name, version in p.CLOSURE.items()).encode()

    def response(self, raw, length=None):
        response = io.BytesIO(raw)
        response.geturl = lambda: p.PINS[0]['url']
        response.headers = {} if length is None else {'Content-Length': str(length)}
        return response

    def test_sources_parse(self):
        for name in ('egl_runtime.py', 'test_egl_runtime.py'):
            ast.parse((Path(p.__file__).parent / name).read_text(encoding='utf8'))

    def test_import_and_main_are_source_only(self):
        with self.forbidden(), contextlib.redirect_stdout(io.StringIO()) as output:
            importlib.reload(p)
            self.assertEqual(p.main(), 0)
        observed = json.loads(output.getvalue())
        self.assertEqual(observed['status'], 'SOURCE_ONLY_EGL_NOT_RUN')
        self.assertIs(observed['minecraft_client_acceptance'], False)
        self.assertIs(observed['holdClearance'], False)

    def test_actual_windows_refusal_before_root_library_network_or_spawn(self):
        if os.name != 'nt':
            self.skipTest('actual Windows negative control requires Windows')
        with self.forbidden(), self.assertRaisesRegex(Exception, 'HOSTED_LINUX_X64_ONLY'):
            p.prepare_egl(Path('unused'))

    def test_each_native_entry_guard_precedes_effects(self):
        with patch.object(p.graphics, 'hosted_guard', side_effect=RuntimeError('HOST_REFUSED')), self.forbidden():
            actions = (lambda: p.prepare_egl(Path('unused')),
                       lambda: p.check_library('/unused.so', 'eglChooseConfig'),
                       lambda: p.download_archive(Path('unused'), p.PINS[0]),
                       lambda: p.bounded_command([], Path('unused'), 'unused', 1))
            for action in actions:
                with self.assertRaisesRegex(RuntimeError, 'HOST_REFUSED'):
                    action()

    def test_root_requires_owned_existing_workspace_descendant(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / 'run'
            root.mkdir()
            self.assertEqual(p.validate_root(root, workspace), root.resolve())
            for bad in (workspace, Path('relative'), workspace / 'absent', workspace / 'run/../run'):
                with self.subTest(root=bad), self.assertRaises(Exception):
                    p.validate_root(bad, workspace)
            with patch.object(Path, 'is_symlink', return_value=True), self.assertRaisesRegex(Exception, 'LINKED'):
                p.validate_root(root, workspace)

    def test_system_observation_fixture_reuses_without_package_work(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / 'run'
            root.mkdir()
            with patch.object(p.graphics, 'hosted_guard', return_value=workspace), \
                 patch.object(p.graphics, 'egl_loader', return_value={'loaded': True, 'eglChooseConfig': True}), \
                 patch.dict(os.environ, {}, clear=True), self.forbidden():
                actual = p.prepare_egl(root)
            self.assertEqual(actual['env'], {})
            self.assertEqual(actual['provenance']['status'], 'EXISTING_SYSTEM_EGL_SYMBOL_OBSERVED')
            self.assertEqual(list(root.iterdir()), [])

    def test_missing_symbol_does_not_count_as_healthy_system(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / 'run'
            root.mkdir()
            with patch.object(p.graphics, 'hosted_guard', return_value=workspace), \
                 patch.object(p.graphics, 'egl_loader', return_value={'loaded': True, 'eglChooseConfig': False}), \
                 patch.object(p, 'installed_closure', side_effect=RuntimeError('ABI_REFUSED')), \
                 patch.dict(os.environ, {}, clear=True), self.forbidden():
                with self.assertRaisesRegex(p.EglRuntimeError, 'ABI_REFUSED'):
                    p.prepare_egl(root)
            receipt = json.loads((root / 'egl-runtime/EGL_PROVENANCE.json').read_text(encoding='utf8'))
            self.assertEqual(receipt['status'], 'ISOLATED_EGL_PREPARATION_FAILED')
            self.assertIs(receipt['holdClearance'], False)
            self.assertEqual(sorted(x.name for x in (root / 'egl-runtime').iterdir()), ['EGL_PROVENANCE.json'])

    def test_preexisting_vendor_override_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / 'run'
            root.mkdir()
            with patch.object(p.graphics, 'hosted_guard', return_value=workspace), \
                 patch.dict(os.environ, {'__EGL_VENDOR_LIBRARY_FILENAMES': '/unreviewed.json'}, clear=True), \
                 self.forbidden(), self.assertRaisesRegex(Exception, 'PREEXISTING_EGL_VENDOR_OVERRIDE_REFUSED'):
                p.prepare_egl(root)

    def test_exact_installed_abi_closure(self):
        actual = p.parse_closure(self.closure())
        self.assertEqual(set(actual), set(p.CLOSURE))
        self.assertEqual(actual['mesa-libgallium']['version'], '25.2.8-0ubuntu0.24.04.4')

    def test_installed_abi_mismatch_missing_duplicate_and_architecture_refused(self):
        raw = self.closure()
        for bad in (raw.replace(b'25.2.8-', b'25.2.7-', 1), b'\n'.join(raw.splitlines()[1:]),
                    raw + raw.splitlines()[0] + b'\n', raw.replace(b'amd64', b'arm64', 1),
                    raw.replace(b'installed', b'config-files', 1), b'unrelated\t1\tinstalled\tamd64\n'):
            with self.subTest(raw=bad), self.assertRaises(Exception):
                p.parse_closure(bad)

    def test_archive_pin_size_and_sha256_fail_closed(self):
        raw = b'pure unit bytes'
        pin = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        p.verify_archive(raw, pin)
        for bad in (dict(pin, bytes=len(raw) + 1), dict(pin, bytes=p.MAX_DEB + 1), dict(pin, sha256='0' * 64)):
            with self.subTest(pin=bad), self.assertRaises(Exception):
                p.verify_archive(raw, bad)

    def test_download_hash_failure_never_writes_deb(self):
        opener = Mock()
        opener.open.return_value = self.response(b'x' * p.PINS[0]['bytes'])
        with tempfile.TemporaryDirectory() as temporary, patch.object(p.graphics, 'hosted_guard'), \
             patch.object(p.urllib.request, 'build_opener', return_value=opener):
            root = Path(temporary)
            with self.assertRaisesRegex(Exception, 'EGL_ARCHIVE_SHA256_MISMATCH'):
                p.download_archive(root, p.PINS[0])
            self.assertEqual(list(root.iterdir()), [])

    def test_download_streaming_cap_before_write(self):
        opener = Mock()
        opener.open.return_value = self.response(b'x' * (p.PINS[0]['bytes'] + 1))
        with tempfile.TemporaryDirectory() as temporary, patch.object(p.graphics, 'hosted_guard'), \
             patch.object(p.urllib.request, 'build_opener', return_value=opener):
            root = Path(temporary)
            with self.assertRaisesRegex(Exception, 'EGL_ARCHIVE_SIZE_CAP'):
                p.download_archive(root, p.PINS[0])
            self.assertEqual(list(root.iterdir()), [])

    def test_unreviewed_url_or_package_pin_refused_before_network(self):
        with patch.object(p.graphics, 'hosted_guard'), self.forbidden(), \
             self.assertRaisesRegex(Exception, 'UNREVIEWED_EGL_PACKAGE_PIN'):
            p.download_archive(Path('unused'), dict(p.PINS[0], url='https://unreviewed.invalid/'))

    def test_exact_regular_elf_fixture(self):
        raw, pin = self.fixture()
        archive = self.tar([(pin['member'], raw, tarfile.REGTYPE)])
        self.assertEqual(p.exact_elf(archive, pin), raw)

    def test_symlink_and_hardlink_exact_member_refused(self):
        raw, pin = self.fixture()
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE):
            with self.subTest(kind=kind), self.assertRaisesRegex(Exception, 'EXACT_REGULAR_EGL_ELF_REQUIRED'):
                p.exact_elf(self.tar([(pin['member'], raw, kind)]), pin)

    def test_wrong_or_duplicate_member_refused(self):
        raw, pin = self.fixture()
        archives = [self.tar([('./wrong.so', raw, tarfile.REGTYPE)]),
                    self.tar([(pin['member'], raw, tarfile.REGTYPE)] * 2)]
        for archive in archives:
            with self.assertRaisesRegex(Exception, 'EXACT_UNIQUE_EGL_MEMBER_REQUIRED'):
                p.exact_elf(archive, pin)

    def test_tar_escaping_absolute_or_backslash_paths_refused(self):
        raw, pin = self.fixture()
        for name in ('../evil', '/absolute/evil', './usr/../../evil', 'usr\\evil'):
            archive = self.tar([(name, b'not used', tarfile.REGTYPE), (pin['member'], raw, tarfile.REGTYPE)])
            with self.subTest(name=name), self.assertRaisesRegex(Exception, 'EGL_TAR_PATH_ESCAPE'):
                p.exact_elf(archive, pin)

    def test_elf_header_size_and_digest_refused(self):
        raw, pin = self.fixture()
        for data, bad_pin, reason in ((raw[:-1], pin, 'EXACT_REGULAR_EGL_ELF_REQUIRED'),
                                      (b'BROKEN!' + raw[7:], pin, 'AMD64_SHARED_ELF_REQUIRED'),
                                      (raw, dict(pin, elf_sha256='0' * 64), 'EGL_ELF_SHA256_MISMATCH')):
            with self.subTest(reason=reason), self.assertRaisesRegex(Exception, reason):
                p.exact_elf(self.tar([(pin['member'], data, tarfile.REGTYPE)]), bad_pin)

    def test_tar_and_binary_output_caps(self):
        raw, pin = self.fixture()
        with self.assertRaisesRegex(Exception, 'EGL_TAR_SIZE_CAP'):
            p.exact_elf(b'x' * (p.MAX_TAR + 1), pin)
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / 'bounded'
            target.write_bytes(b'12345')
            with self.assertRaisesRegex(Exception, 'OWNED_COMMAND_OUTPUT_CAP'):
                p.read_owned_binary(target, 4)

    def test_source_no_global_install_search_path_mutation_or_context_change(self):
        source = Path(p.__file__).read_text(encoding='utf8')
        for forbidden in ('apt-get', 'sudo', 'pip install', 'extractall(', '.extract(', 'SDL_GL_SetAttribute',
                          'os.environ[', 'os.environ.update', 'MESA_GL_VERSION_OVERRIDE'):
            self.assertNotIn(forbidden, source)
        self.assertIn("'--fsys-tarfile'", source)
        self.assertIn("'__EGL_VENDOR_LIBRARY_FILENAMES': str(vendor_path)", source)
        self.assertIn("'SDL_EGL_LIBRARY': str(egl)", source)
        self.assertEqual(len(p.PINS), 2)
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Dict):
                for key, value in zip(node.keys, node.values):
                    if isinstance(key, ast.Constant) and key.value in ('minecraft_client_acceptance', 'holdClearance'):
                        self.assertIsInstance(value, ast.Constant)
                        self.assertIs(value.value, False)


if __name__ == '__main__':
    unittest.main()
