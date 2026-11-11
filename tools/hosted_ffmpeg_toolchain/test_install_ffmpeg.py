import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import install_ffmpeg as target

PREFIX = target.NAME[:-7]
ELF = b"\x7fELF\x02\x01" + b"\x00" * 12 + b"\x3e\x00" + b"fixture"


def archive(path, entries):
    with tarfile.open(path, "w:xz") as out:
        for name, data, kind in entries:
            info = tarfile.TarInfo(name)
            info.type = kind
            info.size = len(data) if kind == tarfile.REGTYPE else 0
            if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE):
                info.linkname = "../../outside"
            out.addfile(info, io.BytesIO(data) if info.size else None)


def valid_entries():
    return [(PREFIX + "/bin/ffmpeg", ELF, tarfile.REGTYPE),
            (PREFIX + "/bin/ffprobe", ELF, tarfile.REGTYPE),
            (PREFIX + "/LICENSE.txt", b"synthetic license fixture", tarfile.REGTYPE)]


class SourceOnlyGuardTests(unittest.TestCase):
    def test_exact_asset_metadata(self):
        value = {"id": target.ASSET_ID, "name": target.NAME, "size": target.SIZE,
                 "digest": "sha256:" + target.SHA256, "state": "uploaded"}
        target.validate_metadata(value)
        for key in value:
            with self.subTest(key=key), self.assertRaises(ValueError):
                target.validate_metadata({**value, key: None})

    def test_https_host_allowlist(self):
        target.safe_url("https://release-assets.githubusercontent.com/example?signature=synthetic")
        for url in ["http://api.github.com/x", "https://evil.example/x", "https://api.github.com.evil.example/x",
                    "https://name:password@api.github.com/x", "https://api.github.com:8443/x", "https://api.github.com/x#fragment"]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                target.safe_url(url)

    def test_local_and_self_hosted_execution_refused(self):
        env = {"GITHUB_ACTIONS": "true", "RUNNER_ENVIRONMENT": "github-hosted", "RUNNER_OS": "Linux", "RUNNER_ARCH": "X64"}
        target.hosted_context(env, "Linux", "x86_64")
        for key in env:
            with self.subTest(key=key), self.assertRaises(ValueError):
                target.hosted_context({**env, key: "wrong"}, "Linux", "x86_64")
        with self.assertRaises(ValueError):
            target.hosted_context(env, "Windows", "AMD64")

    def test_traversal_absolute_and_windows_paths_refused(self):
        for name in ["../outside", "/root/evil", PREFIX + "/../evil", "C:/evil", PREFIX + "\\evil", PREFIX + "//evil"]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                target.member_kind(tarfile.TarInfo(name))

    def test_links_and_devices_refused_even_if_unselected(self):
        for kind in [tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.CHRTYPE, tarfile.FIFOTYPE]:
            info = tarfile.TarInfo(PREFIX + "/doc/unselected")
            info.type = kind
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.member_kind(info)

    def test_extracts_only_two_elfs_and_license(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "fixture.tar.xz"
            archive(source, valid_entries() + [(PREFIX + "/bin/untrusted", b"ignored", tarfile.REGTYPE)])
            output = root / "out"
            files = target.extract_selected(source, output)
            self.assertEqual(set(files), {"bin/ffmpeg", "bin/ffprobe", "licenses/LICENSE.txt"})
            self.assertEqual((output / "bin/ffmpeg").read_bytes(), ELF)
            self.assertFalse((output / "bin/untrusted").exists())

    def test_missing_binary_or_license_refused(self):
        for entries in [valid_entries()[:-1], valid_entries()[1:]]:
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                source = root / "fixture.tar.xz"
                archive(source, entries)
                with self.assertRaises(ValueError):
                    target.extract_selected(source, root / "out")

    def test_duplicate_members_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "fixture.tar.xz"
            archive(source, valid_entries() + valid_entries()[:1])
            with self.assertRaisesRegex(ValueError, "duplicate"):
                target.extract_selected(source, root / "out")

    def test_non_elf_executable_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "fixture.tar.xz"
            archive(source, [(PREFIX + "/bin/ffmpeg", b"not ELF", tarfile.REGTYPE)])
            with self.assertRaisesRegex(ValueError, "not_linux_x64_elf"):
                target.extract_selected(source, root / "out")

    def test_archive_limits_are_enforced(self):
        for name, limit in [("MAX_EXPANDED", 1), ("MAX_MEMBERS", 1), ("MAX_LICENSES", 1)]:
            with tempfile.TemporaryDirectory() as folder, patch.object(target, name, limit):
                root = Path(folder)
                source = root / "fixture.tar.xz"
                archive(source, valid_entries())
                with self.subTest(limit=name), self.assertRaises(ValueError):
                    target.extract_selected(source, root / "out")

    def test_existing_output_never_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "fixture.tar.xz"
            archive(source, valid_entries())
            output = root / "out"
            (output / "bin").mkdir(parents=True)
            (output / "bin/ffmpeg").write_bytes(b"keeper")
            with self.assertRaisesRegex(ValueError, "output_exists"):
                target.extract_selected(source, output)
            self.assertEqual((output / "bin/ffmpeg").read_bytes(), b"keeper")

    def test_exact_size_and_digest_required(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "download"
            source.write_bytes(b"actual bytes")
            with self.assertRaisesRegex(ValueError, "size_mismatch"):
                target.verify_archive(source)
            with patch.object(target, "SIZE", source.stat().st_size):
                with self.assertRaisesRegex(ValueError, "sha256_mismatch"):
                    target.verify_archive(source)

    def test_redirect_never_inherits_auth_or_accepts_other_hosts(self):
        seen = []
        class Opener:
            def open(self, request, timeout):
                seen.append(dict(request.header_items()))
                raise target.urllib.error.HTTPError(request.full_url, 302, "redirect", {"Location": "https://evil.example/asset"}, None)
        with patch.object(target.urllib.request, "build_opener", return_value=Opener()):
            with self.assertRaisesRegex(ValueError, "download_url_refused"):
                target.bounded_get(target.URL, io.BytesIO(), 20, "application/octet-stream")
        self.assertEqual(len(seen), 1)
        self.assertFalse(any(key.lower() == "authorization" for key in seen[0]))

    def test_download_403_is_failure_without_retry(self):
        calls = []
        class Opener:
            def open(self, request, timeout):
                calls.append(request)
                raise target.urllib.error.HTTPError(request.full_url, 403, "forbidden", {}, None)
        with patch.object(target.urllib.request, "build_opener", return_value=Opener()):
            with self.assertRaisesRegex(ValueError, "public_download_http_403"):
                target.bounded_get(target.URL, io.BytesIO(), 20, "application/octet-stream")
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
