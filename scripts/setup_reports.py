"""Set up an isolated reporting environment; optionally install pinned Tectonic."""

import argparse
import hashlib
import io
import json
from pathlib import Path
import platform
import subprocess
import sys
import tarfile
import urllib.request
import venv
import zipfile


ROOT = Path(__file__).resolve().parents[1]
COMPILERS = {
    ("Windows", "AMD64"): ("x86_64-pc-windows-msvc.zip", "f61ce51f0b0ade1015b7de7ef368541c5424e9756ecbd0d7af97d6d48030845f"),
    ("Linux", "x86_64"): ("x86_64-unknown-linux-musl.tar.gz", "8533d07f9ccbd7a65824b9e0459041bca34af1eb33daba48f59215593753a3b7"),
    ("Darwin", "x86_64"): ("x86_64-apple-darwin.tar.gz", "7c90ef5b6ddb1eb1937e4337add5237b79338e4b9676459fa91187d24d6cdf80"),
    ("Darwin", "arm64"): ("aarch64-apple-darwin.tar.gz", "a3f1cac7c5678f01661a92212f58480ae3b0634115d880dbc59e2953ded45667"),
}


def install_compiler():
    target = ROOT / ".tools" / ("tectonic.exe" if sys.platform == "win32" else "tectonic")
    asset, expected = COMPILERS.get((platform.system(), platform.machine()), (None, None))
    if not asset:
        raise RuntimeError("No bundled compiler setup for this platform. Install pdflatex or Tectonic manually.")
    url = "https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%400.17.0/tectonic-0.17.0-" + asset
    print("Downloading Tectonic 0.17.0 from its official GitHub release...", flush=True)
    with urllib.request.urlopen(url, timeout=60) as response:
        archive = response.read()
    if hashlib.sha256(archive).hexdigest() != expected:
        raise RuntimeError("Compiler archive checksum mismatch; nothing was installed.")
    if asset.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
            matches = [entry for entry in bundle.namelist() if Path(entry).name == target.name]
            if len(matches) != 1:
                raise RuntimeError("Compiler archive does not contain exactly one executable.")
            executable = bundle.read(matches[0])
    else:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as bundle:
            matches = [entry for entry in bundle.getmembers() if entry.isfile() and Path(entry.name).name == target.name]
            if len(matches) != 1:
                raise RuntimeError("Compiler archive does not contain exactly one executable.")
            executable = bundle.extractfile(matches[0]).read()
    target.parent.mkdir(exist_ok=True)
    target.write_bytes(executable)
    target.chmod(0o755)
    marker = {"version": "0.17.0", "archive_sha256": expected,
              "executable_sha256": hashlib.sha256(executable).hexdigest()}
    target.with_suffix(target.suffix + ".json").write_text(json.dumps(marker), encoding="utf-8")
    print("Compiler installed:", target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--with-compiler", action="store_true")
    parser.add_argument("--dev", action="store_true", help="Also install test and PDF inspection dependencies.")
    parser.add_argument("--inspect-tools", action="store_true", help="Install PDF inspection tools without the test runner.")
    args = parser.parse_args()
    if not (3, 11) <= sys.version_info[:2] < (3, 13):
        parser.error("Use Python 3.11 or 3.12, as required by OsdagBridge.")
    environment = ROOT / ".venv"
    if not environment.exists():
        venv.EnvBuilder(with_pip=True).create(environment)
    python = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    command = [str(python), "-m", "pip", "install", "-r", str(ROOT / "requirements-report.txt")]
    if args.dev or args.inspect_tools:
        command.extend(["pypdf>=5,<7", "PyMuPDF>=1.24,<2"])
    if args.dev:
        command.append("pytest>=8,<10")
    subprocess.run(command, check=True)
    if args.with_compiler:
        install_compiler()
    print("Ready. Run:", str(python), "run_report.py --demo")


if __name__ == "__main__":
    main()
