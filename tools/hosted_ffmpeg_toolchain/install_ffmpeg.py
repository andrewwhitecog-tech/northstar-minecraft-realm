"""Pinned public static GPL FFmpeg, no apt and no tokens. No action without --install."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import subprocess
import tarfile
import urllib.error
import urllib.parse
import urllib.request

REPOSITORY = "FFmpeg-Builds/FFmpeg-Builds"
RELEASE_ID = 429940126
ASSET_ID = 695397913
NAME = "ffmpeg-N-128227-g4811625b5f-linux64-gpl.tar.xz"
SIZE = 157360624
SHA256 = "67929be39bbb696f41d3295686597a439aeac902f61d82be660ccc1453c1fdfb"
URL = f"https://api.github.com/repos/{REPOSITORY}/releases/assets/{ASSET_ID}"
HOSTS = {"api.github.com", "github.com", "release-assets.githubusercontent.com", "objects.githubusercontent.com"}
MAX_ARCHIVE = 250 * 1024 * 1024
MAX_EXPANDED = 750 * 1024 * 1024
MAX_LICENSES = 16 * 1024 * 1024
MAX_MEMBERS = 4096


def require(condition, code):
    if not condition:
        raise ValueError(code)


def safe_url(url):
    p = urllib.parse.urlsplit(url)
    require(p.scheme == "https" and p.hostname in HOSTS and not p.username and not p.password
            and p.port in (None, 443) and not p.fragment, "download_url_refused")
    return url


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def bounded_get(url, destination, limit, accept):
    # No Authorization, token, cookies, environment proxy or inherited headers.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    for hop in range(4):
        request = urllib.request.Request(safe_url(url), headers={"Accept": accept, "User-Agent": "NorthStar-pinned-public-ffmpeg"})
        try:
            response = opener.open(request, timeout=45)
        except urllib.error.HTTPError as error:
            if error.code in (301, 302, 303, 307, 308):
                location = error.headers.get("Location")
                error.close()
                require(bool(location), "download_redirect_missing")
                url = safe_url(urllib.parse.urljoin(url, location))
                continue
            raise ValueError("public_download_http_" + str(error.code)) from None
        with response:
            require(response.status == 200, "download_not_200")
            length = response.headers.get("Content-Length")
            require(length is None or (length.isdigit() and int(length) <= limit), "download_header_size_exceeded")
            total = 0
            digest = hashlib.sha256()
            while True:
                chunk = response.read(min(1024 * 1024, limit - total + 1))
                if not chunk:
                    break
                total += len(chunk)
                require(total <= limit, "download_size_exceeded")
                destination.write(chunk)
                digest.update(chunk)
            return total, digest.hexdigest()
    raise ValueError("download_redirect_limit")


def validate_metadata(value):
    require(isinstance(value, dict) and value.get("id") == ASSET_ID and value.get("name") == NAME
            and value.get("size") == SIZE and value.get("digest") == "sha256:" + SHA256
            and value.get("state") == "uploaded", "pinned_asset_metadata_mismatch")


def member_kind(member):
    name = member.name
    p = PurePosixPath(name)
    require(name and "\\" not in name and not p.is_absolute() and ":" not in name
            and all(part not in ("", ".", "..") for part in name.split("/")), "archive_path_refused")
    require(member.isdir() or member.isfile(), "archive_link_or_special_refused")
    require(member.size >= 0 and not getattr(member, "sparse", None), "archive_sparse_or_size_refused")
    parts = p.parts
    if member.isdir():
        return None
    if len(parts) == 3 and parts[0] == NAME[:-7] and parts[1] == "bin" and parts[2] in ("ffmpeg", "ffprobe"):
        return "bin/" + parts[2]
    # Preserve only actual package license/copyright text, never unrelated programs.
    license_name = p.name.upper()
    if len(parts) >= 2 and parts[0] == NAME[:-7] and (license_name.startswith(("LICENSE", "COPYING", "COPYRIGHT"))
            or any(part.lower() in ("licenses", "license") for part in parts[1:-1])):
        return "licenses/" + "/".join(parts[1:])
    return None


def verify_archive(path):
    require(path.stat().st_size == SIZE and SIZE <= MAX_ARCHIVE, "archive_exact_size_mismatch")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    require(digest.hexdigest() == SHA256, "archive_sha256_mismatch")


def extract_selected(path, destination):
    expanded = licenses = count = 0
    seen = set()
    selected = []
    with tarfile.open(path, "r|xz") as archive:
        for member in archive:
            count += 1
            require(count <= MAX_MEMBERS, "archive_member_limit")
            require(member.name not in seen, "archive_duplicate_member")
            seen.add(member.name)
            expanded += member.size
            require(expanded <= MAX_EXPANDED, "archive_expansion_limit")
            relative = member_kind(member)
            if relative is None:
                continue
            if relative.startswith("licenses/"):
                licenses += member.size
                require(licenses <= MAX_LICENSES, "archive_license_limit")
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            require(not target.exists() and not target.is_symlink(), "archive_output_exists")
            stream = archive.extractfile(member)
            require(stream is not None, "archive_member_missing")
            actual = 0
            with stream, target.open("xb") as out:
                while True:
                    chunk = stream.read(1024 * 1024)
                    if not chunk:
                        break
                    actual += len(chunk)
                    require(actual <= member.size, "archive_member_overflow")
                    out.write(chunk)
            require(actual == member.size, "archive_member_truncated")
            if relative.startswith("bin/"):
                with target.open("rb") as binary:
                    header = binary.read(20)
                require(len(header) == 20 and header[:6] == b"\x7fELF\x02\x01" and header[18:20] == b"\x3e\x00", "not_linux_x64_elf")
                target.chmod(0o755)
            selected.append(relative)
    require({"bin/ffmpeg", "bin/ffprobe"}.issubset(selected), "required_binaries_missing")
    require(any(name.startswith("licenses/") for name in selected), "package_license_missing")
    return selected


def hosted_context(env, system, machine):
    require(system == "Linux" and machine in ("x86_64", "AMD64") and env.get("GITHUB_ACTIONS") == "true"
            and env.get("RUNNER_ENVIRONMENT") == "github-hosted" and env.get("RUNNER_OS") == "Linux"
            and env.get("RUNNER_ARCH") == "X64", "hosted_linux_x64_required")


def install(destination):
    hosted_context(os.environ, platform.system(), platform.machine())
    path_file = Path(os.environ["GITHUB_PATH"])
    require(path_file.is_file() and not path_file.is_symlink(), "github_path_file_required")
    destination = destination.absolute()
    require(not destination.exists() and not destination.is_symlink() and "\n" not in str(destination)
            and "\r" not in str(destination), "fresh_destination_required")
    destination.mkdir(parents=True, exist_ok=False)
    import io
    metadata_bytes = io.BytesIO()
    bounded_get(URL, metadata_bytes, 64 * 1024, "application/vnd.github+json")
    validate_metadata(json.loads(metadata_bytes.getvalue()))
    archive_path = destination / NAME
    with archive_path.open("xb") as out:
        length, digest = bounded_get(URL, out, MAX_ARCHIVE, "application/octet-stream")
    require(length == SIZE and digest == SHA256, "download_pinned_bytes_mismatch")
    verify_archive(archive_path)
    files = extract_selected(archive_path, destination)
    versions = {}
    for name in ("ffmpeg", "ffprobe"):
        r = subprocess.run([str(destination / "bin" / name), "-version"], capture_output=True, text=True, timeout=20, check=True)
        versions[name] = r.stdout.splitlines()[0]
    encoders = subprocess.run([str(destination / "bin/ffmpeg"), "-hide_banner", "-encoders"], capture_output=True, text=True, timeout=20, check=True)
    require(any(len(line.split()) >= 2 and line.split()[1] == "libx264" for line in encoders.stdout.splitlines()), "required_libx264_absent")
    with path_file.open("a", encoding="utf-8") as output:
        output.write(str(destination / "bin") + "\n")
    receipt = {"scope": "ACTUAL_HOSTED_TOOLCHAIN_ONLY_NOT_MEDIA_QC", "release_id": RELEASE_ID,
               "asset_id": ASSET_ID, "archive_size": length, "archive_sha256": digest,
               "versions": versions, "libx264_encoder_present": True, "extracted_files": files}
    (destination / "TOOLCHAIN_ACTUAL.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in receipt.items() if key != "extracted_files"}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--destination", type=Path)
    args = parser.parse_args()
    if args.install:
        require(args.destination is not None, "destination_required")
        try:
            install(args.destination)
        except Exception as error:
            # Fixed code/type only: never log redirect URLs, headers, or response bodies.
            print(json.dumps({"status": "TOOLCHAIN_INSTALL_FAILED", "error": str(error) if isinstance(error, ValueError) else type(error).__name__}))
            raise SystemExit(1) from None
    else:
        print("SOURCE_ONLY_TOOLCHAIN_NOT_INSTALLED")
