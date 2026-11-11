"""Source-only by default. Bounded public-hosted SDL loader diagnostic, never Minecraft acceptance."""
from __future__ import annotations
import argparse
import ctypes as C
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import re
import secrets
import select
import subprocess
import sys
import time
import urllib.request
import zipfile
import native_calibration as calibration
from real_glx_probe import ProbeError, require

HOME = Path(__file__).resolve().parent
SCHEMA = 'northstar.graphics-environment.v1'
ARCHIVE = {
    'url': 'https://libraries.minecraft.net/org/lwjgl/lwjgl-sdl/3.4.3/lwjgl-sdl-3.4.3-natives-linux.jar',
    'sha1': '6ed1b80b7c211a491612c70e43f27ba1f42cccd0',
    'size': 1665811,
}
MEMBER = 'linux/x64/org/lwjgl/sdl/libSDL3.so'
SDL_SHA256 = '77950e8b5e6228902dcecf73cec21b9154205c5f2c46fecc8a6ecd090f78d10c'
SDL_SIZE = 4104744
MAX_ARCHIVE = 2_000_000
MAX_OUTPUT = 262144
ENV_NAMES = ('SDL_EGL_LIBRARY', 'SDL_OPENGL_LIBRARY', 'SDL_VIDEO_FORCE_EGL',
             'SDL_VIDEO_DRIVER', 'LIBGL_ALWAYS_SOFTWARE', 'GALLIUM_DRIVER', 'LD_LIBRARY_PATH', '__EGL_VENDOR_LIBRARY_FILENAMES')
PACKAGES = ('libegl1', 'libegl-mesa0', 'libglvnd0', 'libgbm1', 'libglx-mesa0', 'libgl1-mesa-dri')
HOST_FIELDS = {
    'CI': 'true', 'GITHUB_ACTIONS': 'true', 'RUNNER_ENVIRONMENT': 'github-hosted',
    'RUNNER_OS': 'Linux', 'ImageOS': 'ubuntu24', 'GITHUB_EVENT_NAME': 'workflow_dispatch',
    'GITHUB_REF': 'refs/heads/main', 'GITHUB_REPOSITORY': 'andrewwhitecog-tech/northstar-minecraft-realm',
    'GITHUB_ACTOR': 'andrewwhitecog-tech', 'GITHUB_TRIGGERING_ACTOR': 'andrewwhitecog-tech',
    'NSP_PUBLIC_REPOSITORY': 'true', 'NSP_ALLOW_CLOUD_SURVIVAL_CALIBRATION': '1',
}


def environment_values(env, approved_egl=None):
    """Log only these names and their explicitly allowed values; never dump the environment."""
    values = {name: env.get(name) for name in ENV_NAMES}
    approved_egl = {} if approved_egl is None else approved_egl
    require(isinstance(approved_egl, dict) and set(approved_egl) in (set(), {'SDL_EGL_LIBRARY', '__EGL_VENDOR_LIBRARY_FILENAMES'}), 'EXACT_APPROVED_EGL_ENV_REQUIRED')
    choices = {'SDL_EGL_LIBRARY': (None, '', approved_egl.get('SDL_EGL_LIBRARY')), 'SDL_OPENGL_LIBRARY': (None, ''),
               'SDL_VIDEO_FORCE_EGL': (None, '', '0', '1'), 'SDL_VIDEO_DRIVER': (None, '', 'x11'),
               'LIBGL_ALWAYS_SOFTWARE': (None, '', '1'), 'GALLIUM_DRIVER': (None, '', 'llvmpipe')}
    for name, allowed in choices.items():
        require(values[name] in allowed, 'UNREVIEWED_GRAPHICS_ENV_' + name)
    require(values['__EGL_VENDOR_LIBRARY_FILENAMES'] in (None, '', approved_egl.get('__EGL_VENDOR_LIBRARY_FILENAMES')), 'UNREVIEWED_GRAPHICS_ENV_EGL_VENDOR')
    ldpath = values['LD_LIBRARY_PATH']
    require(ldpath in (None, '') or (len(ldpath) <= 1024 and all(
        re.fullmatch(r'/(?:usr/)?lib(?:64)?(?:/[A-Za-z0-9_.+-]+)*', p) and '..' not in p.split('/')
        for p in ldpath.split(':'))), 'UNREVIEWED_GRAPHICS_ENV_LD_LIBRARY_PATH')
    return values


def hosted_guard():
    """Must run before networking, subprocesses, or CDLL; workstation/WSL always rejected."""
    require(platform.system() == 'Linux' and platform.machine() == 'x86_64', 'HOSTED_LINUX_X64_ONLY')
    calibration.hosted_gate()
    for name, value in HOST_FIELDS.items():
        require(os.environ.get(name) == value, 'HOST_CONTEXT_' + name)
    require(not any(os.environ.get(k) for k in ('MESA_GL_VERSION_OVERRIDE', 'MESA_GLSL_VERSION_OVERRIDE',
                                                'LD_PRELOAD', 'LD_AUDIT')), 'LOADER_OR_VERSION_OVERRIDE_REFUSED')
    environment_values(os.environ)
    workspace = Path(os.environ['GITHUB_WORKSPACE'])
    require(workspace.is_absolute() and '..' not in workspace.parts, 'LEXICAL_WORKSPACE_ESCAPE')
    require(HOME.is_relative_to(workspace), 'SOURCE_OUTSIDE_HOSTED_WORKSPACE')
    for candidate in (workspace, *workspace.parents, HOME, *HOME.parents):
        require(not candidate.is_symlink(), 'LINKED_WORKSPACE_OR_SOURCE_REFUSED')
    return workspace.resolve(strict=True)


def pinned_archive_metadata():
    metadata = json.loads((HOME / 'metadata/minecraft-26.3.json').read_text(encoding='utf8'))
    matches = [item['downloads']['artifact'] for item in metadata['libraries']
               if item['name'] == 'org.lwjgl:lwjgl-sdl:3.4.3:natives-linux']
    require(len(matches) == 1, 'EXACT_SDL_ARCHIVE_METADATA_REQUIRED')
    actual = {key: matches[0][key] for key in ARCHIVE}
    require(actual == ARCHIVE and actual['size'] <= MAX_ARCHIVE, 'PINNED_SDL_ARCHIVE_DRIFT')
    return dict(actual)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError('OFFICIAL_ARCHIVE_REDIRECT_REFUSED')


def download_sdl(root):
    hosted_guard()
    metadata = pinned_archive_metadata()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    request = urllib.request.Request(metadata['url'], headers={'User-Agent': 'NorthStar-hosted-graphics-diagnostic/1'})
    deadline = time.monotonic() + 35
    chunks = []
    size = 0
    with opener.open(request, timeout=15) as response:
        require(response.geturl() == metadata['url'], 'OFFICIAL_ARCHIVE_URL_DRIFT')
        length = response.headers.get('Content-Length')
        require(length is None or length == str(metadata['size']), 'SDL_ARCHIVE_CONTENT_LENGTH_DRIFT')
        while True:
            require(time.monotonic() < deadline, 'SDL_ARCHIVE_DOWNLOAD_TIMEOUT')
            block = response.read(min(65536, metadata['size'] + 1 - size))
            if not block:
                break
            size += len(block)
            require(size <= metadata['size'] and size <= MAX_ARCHIVE, 'SDL_ARCHIVE_SIZE_CAP')
            chunks.append(block)
    raw = b''.join(chunks)
    require(len(raw) == metadata['size'] and hashlib.sha1(raw).hexdigest() == metadata['sha1'],
            'SDL_ARCHIVE_SIZE_OR_SHA1_MISMATCH')
    archive = root / 'lwjgl-sdl-3.4.3-natives-linux.jar'
    with archive.open('xb') as handle:
        handle.write(raw)
    with zipfile.ZipFile(io.BytesIO(raw)) as package:
        entries = [item for item in package.infolist() if item.filename == MEMBER]
        require(len(entries) == 1 and entries[0].file_size == SDL_SIZE, 'EXACT_SDL_MEMBER_REQUIRED')
        library_raw = package.read(entries[0])
    require(hashlib.sha256(library_raw).hexdigest() == SDL_SHA256, 'BUNDLED_SDL_SHA256_MISMATCH')
    native_home = root / 'runtime/natives'
    (native_home / 'java').mkdir(parents=True, exist_ok=False)
    library = native_home / 'java/libSDL3.so'
    with library.open('xb') as handle:
        handle.write(library_raw)
    provenance = {'archive': metadata, 'member': MEMBER, 'library': str(library),
                  'library_bytes': len(library_raw), 'library_sha256': SDL_SHA256}
    (root / 'SDL_PROVENANCE.json').write_text(json.dumps(provenance, sort_keys=True) + '\n', encoding='utf8')
    return native_home, provenance


def child_env(display=None):
    # Deliberately exclude tokens, Python startup hooks, shell startup hooks and unrelated settings.
    env = dict(HOST_FIELDS, GITHUB_WORKSPACE=os.environ['GITHUB_WORKSPACE'],
               GITHUB_RUN_ID=os.environ['GITHUB_RUN_ID'], PATH='/usr/local/bin:/usr/bin:/bin',
               LANG='C.UTF-8', LC_ALL='C.UTF-8', PYTHONUTF8='1', PYTHONIOENCODING='utf-8',
               LIBGL_ALWAYS_SOFTWARE='1', GALLIUM_DRIVER='llvmpipe', SDL_VIDEO_DRIVER='x11', LP_NUM_THREADS='2')
    ldpath = environment_values(os.environ)['LD_LIBRARY_PATH']
    if ldpath:
        env['LD_LIBRARY_PATH'] = ldpath
    if display is not None:
        require(re.fullmatch(r':[0-9]{1,3}', display), 'OWN_DISPLAY_FORMAT')
        env['DISPLAY'] = display
    return env


def stop_owned(process):
    """Only the exact Popen handle owned by this invocation, with real final exit recorded."""
    record = {'pid': process.pid, 'before_exit': process.poll(), 'terminate_sent': False, 'kill_sent': False}
    if record['before_exit'] is None:
        try:
            process.terminate()
            record['terminate_sent'] = True
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                process.kill()
                record['kill_sent'] = True
            except ProcessLookupError:
                pass
            process.wait(timeout=5)
    record['final_exit'] = process.poll()
    require(record['final_exit'] is not None, 'OWNED_PROCESS_EXIT_NOT_OBSERVED')
    return record


def capture(args, root, label, env, timeout=20):
    """Fixed reviewed commands, bounded execution/output; raw bytes retained in this fresh run only."""
    hosted_guard()
    outpath, errpath = root / (label + '.stdout'), root / (label + '.stderr')
    cleanup = None
    with outpath.open('xb') as stdout, errpath.open('xb') as stderr:
        process = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                   cwd=root, env=env, start_new_session=True)
        reason = None
        try:
            deadline = time.monotonic() + timeout
            while process.poll() is None:
                if time.monotonic() >= deadline:
                    reason = 'COMMAND_TIMEOUT'
                    break
                if outpath.stat().st_size > MAX_OUTPUT or errpath.stat().st_size > MAX_OUTPUT:
                    reason = 'COMMAND_OUTPUT_CAP'
                    break
                time.sleep(.05)
        finally:
            cleanup = stop_owned(process)
    def read(path):
        with path.open('rb') as handle:
            return handle.read(MAX_OUTPUT).decode('utf8', 'replace')
    return {'command': args, 'exit': cleanup['final_exit'], 'reason': reason,
            'stdout': read(outpath), 'stderr': read(errpath),
            'stdout_truncated': outpath.stat().st_size > MAX_OUTPUT,
            'stderr_truncated': errpath.stat().st_size > MAX_OUTPUT, 'cleanup': cleanup}


def egl_loader():
    hosted_guard()
    result = {'requested_library': 'libEGL.so.1', 'loaded': False, 'eglChooseConfig': False}
    try:
        library = C.CDLL('libEGL.so.1')
        result['loaded'] = True
        result['eglChooseConfig'] = hasattr(library, 'eglChooseConfig')
    except OSError as error:
        result['error_type'] = type(error).__name__
        result['raw_loader_error'] = str(error)
    maps = Path('/proc/self/maps')
    with maps.open('rb') as handle:
        raw = handle.read(1_048_577)
    require(len(raw) <= 1_048_576, 'PROCESS_MAPS_SIZE_CAP')
    resolved = sorted({line.split(None, 5)[5] for line in raw.decode('utf8', 'replace').splitlines()
                       if len(line.split(None, 5)) == 6 and re.fullmatch(
                           r'/[^\n]+/libEGL\.so(?:\.[0-9]+)*', line.split(None, 5)[5])})
    result['mapped_egl_libraries'] = []
    for name in resolved:
        target = Path(name).resolve(strict=True)
        require(target.stat().st_size <= 16_777_216, 'EGL_LIBRARY_HASH_SIZE_CAP')
        result['mapped_egl_libraries'].append({'path': name, 'resolved_path': str(target),
                                              'sha256': hashlib.sha256(target.read_bytes()).hexdigest()})
    return result


def execute(reviewed, prepare_egl_runtime=False):
    workspace = hosted_guard()  # Before CDLL, native subprocesses, or networking.
    require(isinstance(reviewed, str) and re.fullmatch(r'[0-9a-f]{64}', reviewed), 'REVIEWED_PAYLOAD_SHA256_REQUIRED')
    calibration.validate_payload(reviewed)
    os.nice(19)
    runs = HOME / 'runs'
    require(not runs.is_symlink(), 'LINKED_RUNS_REFUSED')
    runs.mkdir(exist_ok=True)
    require(runs.resolve().is_relative_to(workspace), 'RUN_OUTSIDE_WORKSPACE')
    root = runs / ('graphics-' + secrets.token_hex(8))
    root.mkdir(exist_ok=False)
    result = {'schema': SCHEMA, 'status': 'DIAGNOSTIC_INCOMPLETE', 'minecraft_client_acceptance': False,
              'holdClearance': False, 'native_mining_legs_executed': 0, 'reviewed_payload_sha256': reviewed,
              'run_directory': str(root), 'graphics_environment': environment_values(os.environ), 'errors': []}
    xvfb = None
    xvfb_log = None
    read_fd = write_fd = None
    try:
        native_home, result['sdl_provenance'] = download_sdl(root)
        env = child_env()
        dpkg_format = '-f=' + chr(36) + '{binary:Package}\t' + chr(36) + '{Version}\t' + chr(36) + '{db:Status-Status}\n'
        result['package_versions'] = capture(['/usr/bin/dpkg-query', '-W', dpkg_format, *PACKAGES], root, 'dpkg', env, 10)
        cache = capture(['/sbin/ldconfig', '-p'], root, 'ldconfig', env, 10)
        # Only relevant graphics cache entries appear in the JSON job log.
        cache['stdout'] = '\n'.join(line for line in cache['stdout'].splitlines() if re.search(
            r'\b(?:libEGL|libGLX|libGL|libOpenGL|libgbm)\.so', line))
        result['loader_cache'] = cache
        result['egl_loader'] = egl_loader()
        approved_egl = {}
        if prepare_egl_runtime:
            from egl_runtime import prepare_egl
            prepared = prepare_egl(root)
            result['isolated_egl_runtime'] = prepared['provenance']
            approved_egl = prepared['env']
        read_fd, write_fd = os.pipe()
        xvfb_log = (root / 'xvfb.actual.log').open('xb')
        xvfb = subprocess.Popen(['/usr/bin/Xvfb', '-displayfd', str(write_fd), '-screen', '0', '800x450x24',
                                 '-nolisten', 'tcp', '+extension', 'GLX', '+render', '-noreset'],
                                stdin=subprocess.DEVNULL, stdout=xvfb_log, stderr=subprocess.STDOUT,
                                pass_fds=(write_fd,), cwd=root, env=env, start_new_session=True)
        os.close(write_fd)
        write_fd = None
        require(select.select([read_fd], [], [], 10)[0], 'OWN_XVFB_DISPLAY_TIMEOUT')
        display_raw = os.read(read_fd, 16).decode('ascii')
        require(re.fullmatch(r'[0-9]{1,3}\n', display_raw) and xvfb.poll() is None, 'OWN_XVFB_DISPLAY_FAILED')
        display = ':' + display_raw.strip()
        result['xvfb'] = {'pid': xvfb.pid, 'display': display, 'screen': '800x450x24', 'displayfd_owned': True}
        result['sdl_probes'] = []
        for mode in ('glx', 'egl'):
            probe_env = child_env(display)
            probe_env.update(approved_egl)
            probe_env['SDL_VIDEO_FORCE_EGL'] = '1' if mode == 'egl' else '0'
            actual = capture([sys.executable, '-X', 'utf8', '-S', '-B', str(HOME / 'real_sdl_probe.py'),
                              '--execute', '--native-home', str(native_home), '--mode', mode], root,
                             'sdl-' + mode, probe_env)
            actual.update(mode=mode, graphics_environment=environment_values(probe_env, approved_egl))
            result['sdl_probes'].append(actual)
            try:
                observed = json.loads(actual['stdout'])
                require(observed.get('schema') == 'northstar.actual-sdl-probe.v1' and
                        observed.get('mode') == mode and observed.get('minecraft_client_acceptance') is False and
                        observed.get('status') in ('REAL_SDL_CONTEXT_QUERIED', 'SDL_FAILED_OR_UNAVAILABLE'),
                        'SDL_PROBE_OUTPUT_SCHEMA')
                actual['observed'] = observed
            except (ValueError, AttributeError, TypeError, RuntimeError, ProbeError) as error:
                result['errors'].append({'stage': 'sdl-' + mode, 'reason': str(error)})
            if actual['reason'] is not None or actual['exit'] not in (0, 2) or 'observed' not in actual:
                result['errors'].append({'stage': 'sdl-' + mode, 'reason': 'PROBE_PROCESS_INCOMPLETE'})
        result['status'] = 'DIAGNOSTIC_COMPLETED' if not result['errors'] else 'DIAGNOSTIC_INCOMPLETE'
    except Exception as error:
        result['errors'].append({'type': type(error).__name__, 'reason': str(error)})
    finally:
        for fd in (read_fd, write_fd):
            if fd is not None:
                os.close(fd)
        if xvfb is not None:
            try:
                result['xvfb_cleanup'] = stop_owned(xvfb)
            except Exception as error:
                result['status'] = 'DIAGNOSTIC_INCOMPLETE'
                result['errors'].append({'stage': 'owned_xvfb_cleanup', 'type': type(error).__name__, 'reason': str(error)})
        if xvfb_log is not None:
            xvfb_log.close()
            with (root / 'xvfb.actual.log').open('rb') as handle:
                result['xvfb_raw_log'] = handle.read(MAX_OUTPUT).decode('utf8', 'replace')
        result['exit_code'] = 0 if result['status'] == 'DIAGNOSTIC_COMPLETED' else 1
        (root / 'ACTUAL.json').write_text(json.dumps(result, sort_keys=True) + '\n', encoding='utf8')
        print(json.dumps(result, separators=(',', ':')))
    return result['exit_code']


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--reviewed-payload-sha256')
    parser.add_argument('--prepare-egl', action='store_true')
    args = parser.parse_args(argv)
    if not args.execute:
        calibration.validate_payload(args.reviewed_payload_sha256)
        print(json.dumps({'schema': SCHEMA, 'status': 'SOURCE_ONLY_GRAPHICS_NOT_RUN',
                          'minecraft_client_acceptance': False, 'holdClearance': False}))
        return 0
    try:
        return execute(args.reviewed_payload_sha256, args.prepare_egl)
    except Exception as error:
        print(json.dumps({'schema': SCHEMA, 'status': 'HOSTED_DIAGNOSTIC_REFUSED',
                          'reason': str(error), 'error_type': type(error).__name__,
                          'minecraft_client_acceptance': False, 'holdClearance': False}, separators=(',', ':')))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
