"""Exercise launcher decisions and the files that leave a development checkout."""

import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[2]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def launcher():
    return load_module("report_launcher_test", ROOT / "start.py")


@pytest.fixture
def packager():
    return load_module("report_packager_test", ROOT / "scripts/package_reports.py")


@pytest.fixture
def package_tree(tmp_path, packager):
    root = tmp_path / "Project with spaces"
    for relative in packager.FILES:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Example distribution content\n", encoding="utf-8")
    reports = root / "src/osdagbridge/core/reports"
    reports.mkdir(parents=True)
    (reports / "__init__.py").write_text("# report package\n", encoding="utf-8")
    (root / "private.pdf").write_bytes(b"private local document")
    (root / ".env").write_text("TOKEN=not-for-distribution", encoding="ascii")
    return root


def test_package_contains_only_allowed_files_and_verifiable_manifest(packager, package_tree, tmp_path):
    destination, expected = packager.build_package(package_tree, tmp_path / "reports.zip", revision="abc123")
    with zipfile.ZipFile(destination) as archive:
        names = archive.namelist()
        assert "private.pdf" not in names and ".env" not in names
        assert all(not Path(name).is_absolute() and ".." not in Path(name).parts for name in names)
        manifest = json.loads(archive.read("PACKAGE_MANIFEST.json"))
        assert manifest == expected
        assert manifest["source_commit"] == "abc123"
        for name, checksum in manifest["files"].items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == checksum
    assert destination.with_suffix(".zip.sha256").read_text().startswith(hashlib.sha256(destination.read_bytes()).hexdigest())


def test_same_sources_produce_identical_zip_bytes(packager, package_tree, tmp_path):
    first, _ = packager.build_package(package_tree, tmp_path / "one.zip", revision="abc123")
    second, _ = packager.build_package(package_tree, tmp_path / "two.zip", revision="abc123")
    assert first.read_bytes() == second.read_bytes()


def test_release_bytes_do_not_depend_on_checkout_newlines(packager, package_tree, tmp_path):
    first, _ = packager.build_package(package_tree, tmp_path / "lf.zip", revision="abc123")
    for path in packager.collect_files(package_tree):
        if path.suffix != ".png":
            path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
    second, _ = packager.build_package(package_tree, tmp_path / "crlf.zip", revision="abc123")
    assert first.read_bytes() == second.read_bytes()


def test_package_fails_when_required_runtime_file_is_missing(packager, package_tree, tmp_path):
    (package_tree / "start.py").unlink()
    with pytest.raises(ValueError, match="start.py"):
        packager.build_package(package_tree, tmp_path / "bad.zip", revision="abc123")
    assert not (tmp_path / "bad.zip").exists()


def test_runtime_probe_handles_missing_python(launcher, tmp_path):
    assert not launcher.runtime_ready(tmp_path / "missing.exe")


@pytest.mark.parametrize("arguments", [["--input", "missing.json"], ["--inspect", "missing.pdf"]])
def test_missing_input_fails_before_setup(launcher, monkeypatch, arguments):
    monkeypatch.setattr(launcher.subprocess, "run", lambda *args, **kwargs: pytest.fail("No installation should happen"))
    with pytest.raises(SystemExit) as result:
        launcher.main(arguments)
    assert result.value.code == 2


def test_ready_runtime_and_source_only_run_never_installs_compiler(launcher, monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(launcher, "runtime_ready", lambda *args, **kwargs: True)
    monkeypatch.setattr(launcher, "available_compiler", lambda: None)
    monkeypatch.setattr(launcher.subprocess, "run", lambda command, **kwargs: calls.append(command) or SimpleNamespace(returncode=0))
    assert launcher.main(["--no-pdf", "--output", str(tmp_path / "output with spaces")]) == 0
    assert len(calls) == 1 and "--no-pdf" in calls[0]
    assert str(tmp_path / "output with spaces") in calls[0]


def test_explicit_compiler_is_preserved_without_downloading(launcher, monkeypatch):
    calls = []
    monkeypatch.setattr(launcher, "runtime_ready", lambda *args, **kwargs: True)
    monkeypatch.setattr(launcher.subprocess, "run", lambda command, **kwargs: calls.append(command) or SimpleNamespace(returncode=0))
    assert launcher.main(["--compiler", "C:/Existing compiler/tectonic.exe"]) == 0
    assert len(calls) == 1 and calls[0][-1] == "C:/Existing compiler/tectonic.exe"


def test_setup_failure_prevents_report_run(launcher, monkeypatch):
    calls = []
    monkeypatch.setattr(launcher, "runtime_ready", lambda *args, **kwargs: False)
    monkeypatch.setattr(launcher.subprocess, "run", lambda command, **kwargs: calls.append(command) or SimpleNamespace(returncode=7))
    assert launcher.main(["--no-pdf"]) == 7
    assert len(calls) == 1


def test_failed_report_returns_its_exit_status(launcher, monkeypatch):
    monkeypatch.setattr(launcher, "runtime_ready", lambda *args, **kwargs: True)
    monkeypatch.setattr(launcher.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=4))
    assert launcher.main(["--no-pdf"]) == 4
