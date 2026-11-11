"""Source-only EGL preparation helpers. Native/network work is restricted to approved hosted Linux."""
from __future__ import annotations
import ctypes as C
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import time
import urllib.request
import graphics_environment as graphics
from real_glx_probe import require

MESA_VERSION = '25.2.8-0ubuntu0.24.04.4'
GLVND_VERSION = '1.7.0-1build1'
PINS = (
    {'name': 'libegl1', 'version': GLVND_VERSION,
     'url': 'https://archive.ubuntu.com/ubuntu/pool/main/libg/libglvnd/libegl1_1.7.0-1build1_amd64.deb',
     'bytes': 28670, 'sha256': 'e549f7776216f7bd3b1c216729fb40a97a562e2eb7c563cde632b4931f9a4e57',
     'member': './usr/lib/x86_64-linux-gnu/libEGL.so.1.1.0', 'elf_bytes': 72312,
     'elf_sha256': '875ecbb2a07d60e32216c9f102965abc1e9cc1da7789558e2e9b8b9c107e231d'},
    {'name': 'libegl-mesa0', 'version': MESA_VERSION,
     'url': 'https://archive.ubuntu.com/ubuntu/pool/main/m/mesa/libegl-mesa0_25.2.8-0ubuntu0.24.04.4_amd64.deb',
     'bytes': 117224, 'sha256': '2b8363cb29868603c827cb569a19373a45bebb29bdca5cd34de42dce2f3c9419',
     'member': './usr/lib/x86_64-linux-gnu/libEGL_mesa.so.0.0.0', 'elf_bytes': 345528,
     'elf_sha256': '1633e58ed806e1dbffd85d87338b60f7f44bfaf80aa326c2c2e147c4eb1f78f0'},
)
CLOSURE = {'libglvnd0': GLVND_VERSION, 'libgbm1': MESA_VERSION, 'libglx-mesa0': MESA_VERSION,
           'libgl1-mesa-dri': MESA_VERSION, 'mesa-libgallium': MESA_VERSION}
MAX_DEB = 200_000
MAX_TAR = 2_000_000
MAX_STDERR = 16_384


class EglRuntimeError(RuntimeError):
    def __init__(self, message, provenance):
        self.provenance = provenance
        super().__init__(message + ': ' + json.dumps(provenance, separators=(',', ':')))


def validate_root(root, workspace):
    root, workspace = Path(root), Path(workspace)
    require(root.is_absolute() and workspace.is_absolute() and '..' not in root.parts,
            'ABSOLUTE_LEXICAL_EGL_ROOT_REQUIRED')
    require(root != workspace and root.is_relative_to(workspace), 'EGL_ROOT_OUTSIDE_WORKSPACE')
    for candidate in (root, *root.parents):
        require(not candidate.is_symlink() and not getattr(candidate, 'is_junction', lambda: False)(),
                'LINKED_EGL_ROOT_REFUSED')
    require(root.is_dir() and workspace.is_dir(), 'EXISTING_OWNED_RUN_ROOT_REQUIRED')
    require(root.resolve(strict=True).is_relative_to(workspace.resolve(strict=True)), 'EGL_ROOT_ESCAPE')
    return root.resolve(strict=True)


def verify_archive(raw, pin):
    require(0 < pin['bytes'] <= MAX_DEB and len(raw) == pin['bytes'], 'EGL_ARCHIVE_SIZE_MISMATCH')
    require(hashlib.sha256(raw).hexdigest() == pin['sha256'], 'EGL_ARCHIVE_SHA256_MISMATCH')


def download_archive(home, pin):
    graphics.hosted_guard()  # Never network from Windows, WSL, or an unapproved host.
    require(pin in PINS, 'UNREVIEWED_EGL_PACKAGE_PIN')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), graphics.NoRedirect())
    deadline = time.monotonic() + 30
    pieces, size = [], 0
    with opener.open(urllib.request.Request(pin['url'], headers={'User-Agent': 'NorthStar-hosted-EGL/1'}), timeout=10) as response:
        require(response.geturl() == pin['url'], 'EGL_ARCHIVE_URL_DRIFT')
        length = response.headers.get('Content-Length')
        require(length is None or length == str(pin['bytes']), 'EGL_ARCHIVE_CONTENT_LENGTH_MISMATCH')
        while True:
            require(time.monotonic() < deadline, 'EGL_ARCHIVE_DOWNLOAD_TIMEOUT')
            block = response.read(min(65536, pin['bytes'] + 1 - size))
            if not block:
                break
            size += len(block)
            require(size <= pin['bytes'] and size <= MAX_DEB, 'EGL_ARCHIVE_SIZE_CAP')
            pieces.append(block)
    raw = b''.join(pieces)
    verify_archive(raw, pin)
    archive = home / (pin['name'] + '.deb')
    with archive.open('xb') as handle:
        handle.write(raw)
    return archive


def read_owned_binary(path, cap):
    with path.open('rb') as handle:
        raw = handle.read(cap + 1)
    require(len(raw) <= cap, 'OWNED_COMMAND_OUTPUT_CAP')
    return raw


def bounded_command(args, home, label, max_output):
    graphics.hosted_guard()  # Before every native child, including dpkg-query/dpkg-deb.
    stdout_path, stderr_path = home / (label + '.stdout'), home / (label + '.stderr')
    env = graphics.child_env()
    # Do not inherit or introduce library search path changes for package inspection.
    env.pop('LD_LIBRARY_PATH', None)
    with stdout_path.open('xb') as stdout, stderr_path.open('xb') as stderr:
        process = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                   cwd=home, env=env, start_new_session=True)
        reason = None
        try:
            deadline = time.monotonic() + 15
            while process.poll() is None:
                if time.monotonic() >= deadline:
                    reason = 'COMMAND_TIMEOUT'
                    break
                if stdout_path.stat().st_size > max_output or stderr_path.stat().st_size > MAX_STDERR:
                    reason = 'COMMAND_OUTPUT_CAP'
                    break
                time.sleep(.025)
        finally:
            cleanup = graphics.stop_owned(process)
    raw = read_owned_binary(stdout_path, max_output)
    stderr_raw = read_owned_binary(stderr_path, MAX_STDERR)
    actual = {'command': args, 'exit': cleanup['final_exit'], 'reason': reason,
              'stderr': stderr_raw.decode('utf8', 'replace'), 'stdout_bytes': len(raw), 'cleanup': cleanup}
    require(reason is None and actual['exit'] == 0,
            'EGL_PACKAGE_COMMAND_FAILED:' + json.dumps(actual, separators=(',', ':')))
    return raw, actual


def parse_closure(raw):
    rows = {}
    for line in raw.decode('utf8', 'strict').splitlines():
        fields = line.split('\t')
        require(len(fields) == 4, 'EGL_INSTALLED_PACKAGE_ROW_SHAPE')
        name, version, status, architecture = fields
        require(name in CLOSURE and name not in rows, 'EGL_INSTALLED_PACKAGE_IDENTITY')
        require(version == CLOSURE[name] and status == 'installed' and architecture == 'amd64',
                'EGL_INSTALLED_ABI_CLOSURE_MISMATCH:' + json.dumps({
                    'name': name, 'expected_version': CLOSURE[name], 'observed_version': version,
                    'observed_status': status, 'observed_architecture': architecture}, separators=(',', ':')))
        rows[name] = {'version': version, 'status': status, 'architecture': architecture}
    require(set(rows) == set(CLOSURE), 'EGL_INSTALLED_ABI_CLOSURE_INCOMPLETE')
    return rows


def installed_closure(home):
    fmt = '-f=' + chr(36) + '{Package}\t' + chr(36) + '{Version}\t' + chr(36) + '{db:Status-Status}\t' + chr(36) + '{Architecture}\n'
    raw, actual = bounded_command(['/usr/bin/dpkg-query', '-W', fmt, *CLOSURE], home, 'installed-closure', 16384)
    actual.update(stdout=raw.decode('utf8', 'strict'), observed=parse_closure(raw))
    return actual


def exact_elf(raw_tar, pin):
    """Read one exact regular file. Never extract a tar path, symlink, script, or package tree."""
    require(len(raw_tar) <= MAX_TAR, 'EGL_TAR_SIZE_CAP')
    selected = []
    with tarfile.open(fileobj=io.BytesIO(raw_tar), mode='r:') as archive:
        for count, member in enumerate(archive, 1):
            require(count <= 128, 'EGL_TAR_MEMBER_COUNT_CAP')
            name = member.name
            require(not name.startswith('/') and '\\' not in name and '\0' not in name and
                    '..' not in PurePosixPath(name).parts, 'EGL_TAR_PATH_ESCAPE')
            if name != pin['member']:
                continue
            require(member.isfile() and not member.issym() and not member.islnk() and
                    not member.linkname and member.size == pin['elf_bytes'], 'EXACT_REGULAR_EGL_ELF_REQUIRED')
            handle = archive.extractfile(member)
            require(handle is not None, 'EGL_MEMBER_DATA_ABSENT')
            with handle:
                raw = handle.read(pin['elf_bytes'] + 1)
            require(len(raw) == pin['elf_bytes'], 'EGL_ELF_SIZE_MISMATCH')
            require(raw[:7] == b'\x7fELF\x02\x01\x01' and raw[16:20] == b'\x03\x00\x3e\x00',
                    'AMD64_SHARED_ELF_REQUIRED')
            require(hashlib.sha256(raw).hexdigest() == pin['elf_sha256'], 'EGL_ELF_SHA256_MISMATCH')
            selected.append(raw)
    require(len(selected) == 1, 'EXACT_UNIQUE_EGL_MEMBER_REQUIRED')
    return selected[0]


def prepare_member(home, pin):
    archive = download_archive(home, pin)
    raw_tar, actual = bounded_command(['/usr/bin/dpkg-deb', '--fsys-tarfile', str(archive)], home,
                                      pin['name'] + '-fsys', MAX_TAR)
    raw = exact_elf(raw_tar, pin)
    library = home / PurePosixPath(pin['member']).name
    with library.open('xb') as handle:
        handle.write(raw)
    require(hashlib.sha256(library.read_bytes()).hexdigest() == pin['elf_sha256'], 'WRITTEN_EGL_ELF_DRIFT')
    return library, {'package': dict(pin), 'archive_path': str(archive), 'library_path': str(library),
                     'library_sha256': pin['elf_sha256'], 'fsys_tarfile': actual}


def check_library(library, symbol):
    graphics.hosted_guard()  # Before CDLL, even when called independently.
    actual = {'path': str(library), 'symbol': symbol, 'loaded': False, 'symbol_available': False}
    try:
        loaded = C.CDLL(str(library))
        actual['loaded'] = True
        actual['symbol_available'] = hasattr(loaded, symbol)
    except OSError as error:
        actual.update(error_type=type(error).__name__, raw_loader_error=str(error))
    return actual


def prepare_egl(root):
    workspace = graphics.hosted_guard()  # First action, before any CDLL, network or child.
    root = validate_root(root, workspace)
    require(not os.environ.get('__EGL_VENDOR_LIBRARY_FILENAMES') and not os.environ.get('__EGL_VENDOR_LIBRARY_DIRS'),
            'PREEXISTING_EGL_VENDOR_OVERRIDE_REFUSED')
    system = graphics.egl_loader()
    provenance = {'schema': 'northstar.isolated-egl-runtime.v1', 'minecraft_client_acceptance': False,
                  'holdClearance': False, 'system_egl': system, 'global_install': False,
                  'library_search_path_changed': False, 'package_sources': [
                      'https://packages.ubuntu.com/noble/libegl1',
                      'https://packages.ubuntu.com/noble-updates/libegl-mesa0']}
    if system.get('loaded') is True and system.get('eglChooseConfig') is True:
        provenance['status'] = 'EXISTING_SYSTEM_EGL_SYMBOL_OBSERVED'
        return {'env': {}, 'provenance': provenance}
    home = root / 'egl-runtime'
    home.mkdir(exist_ok=False)
    provenance['owned_directory'] = str(home)
    try:
        provenance['installed_abi_closure'] = installed_closure(home)
        libraries = []
        provenance['packages'] = []
        for pin in PINS:
            library, receipt = prepare_member(home, pin)
            libraries.append(library)
            provenance['packages'].append(receipt)
        egl, mesa = libraries
        vendor_path = home / '50_mesa.owned.json'
        vendor = {'file_format_version': '1.0.0', 'ICD': {'library_path': str(mesa)}}
        with vendor_path.open('x', encoding='utf8') as handle:
            json.dump(vendor, handle, sort_keys=True)
            handle.write('\n')
        provenance['vendor_json'] = {'path': str(vendor_path), 'content': vendor,
                                      'sha256': hashlib.sha256(vendor_path.read_bytes()).hexdigest()}
        provenance['library_checks'] = [check_library(egl, 'eglChooseConfig'), check_library(mesa, '__egl_Main')]
        require(all(item['loaded'] and item['symbol_available'] for item in provenance['library_checks']),
                'ISOLATED_EGL_LIBRARY_OR_DEPENDENCY_UNAVAILABLE')
        provenance['status'] = 'ISOLATED_PINNED_EGL_SYMBOLS_OBSERVED'
        env = {'SDL_EGL_LIBRARY': str(egl), '__EGL_VENDOR_LIBRARY_FILENAMES': str(vendor_path)}
        return {'env': env, 'provenance': provenance}
    except Exception as error:
        provenance.update(status='ISOLATED_EGL_PREPARATION_FAILED', error_type=type(error).__name__, reason=str(error))
        raise EglRuntimeError('ISOLATED_EGL_PREPARATION_FAILED', provenance) from error
    finally:
        with (home / 'EGL_PROVENANCE.json').open('x', encoding='utf8') as handle:
            json.dump(provenance, handle, sort_keys=True)
            handle.write('\n')


def main():
    print(json.dumps({'schema': 'northstar.isolated-egl-runtime.v1', 'status': 'SOURCE_ONLY_EGL_NOT_RUN',
                      'minecraft_client_acceptance': False, 'holdClearance': False,
                      'pinned_packages': PINS}, separators=(',', ':')))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
