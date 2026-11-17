"""Build a reproducible reporting-only ZIP from a clean source checkout."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile


ROOT = Path(__file__).resolve().parents[1]
FILES = (
    "start.py", "Start_Report.cmd", "start.sh", "run_report.py", "requirements-report.txt",
    "LICENSE", "README.md", "docs/deployment.md", "docs/task_requirements.md",
    "scripts/setup_reports.py", "scripts/verify_report_pdf.py",
    "src/osdagbridge/core/utils/common.py",
    "src/osdagbridge/core/utils/codes/irc6_2017.py",
    "src/osdagbridge/core/utils/codes/irc5_2015.py",
    "src/osdagbridge/core/utils/codes/keyfile.py",
    "src/osdagbridge/core/boq/boq_generator.py",
    "src/osdagbridge/core/data/ResourceFiles/vectors/Osdag Logo.png",
)


def collect_files(root):
    """Use an allowlist so local documents, credentials and runtimes stay out."""
    paths = [root / relative for relative in FILES]
    paths += sorted((root / "src/osdagbridge/core/reports").rglob("*.py"))
    paths += sorted((root / "docs").glob("*.md"))
    missing = [str(path.relative_to(root)) for path in paths if not path.is_file()]
    if missing:
        raise ValueError("Package files are missing: " + ", ".join(missing))
    if any(not path.resolve().is_relative_to(root.resolve()) for path in paths):
        raise ValueError("Package source links must stay inside the project directory.")
    return sorted(set(paths), key=lambda path: path.relative_to(root).as_posix())


def build_package(root, destination, *, revision):
    root, destination = Path(root).resolve(), Path(destination).resolve()
    files = collect_files(root)
    def archive_bytes(path):
        contents = path.read_bytes()
        if path.suffix.lower() in {".py", ".md", ".txt", ".sh", ".cmd"} or path.name == "LICENSE":
            contents = contents.replace(b"\r\n", b"\n")
            if path.suffix.lower() == ".cmd":
                contents = contents.replace(b"\n", b"\r\n")
        return contents
    contents = {path.relative_to(root).as_posix(): archive_bytes(path) for path in files}
    manifest = {"format": 1, "source_commit": revision,
                "python": "3.11 or 3.12", "compiler": "Tectonic 0.17.0, downloaded on first setup",
                "files": {name: hashlib.sha256(data).hexdigest() for name, data in contents.items()}}
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = destination.with_suffix(destination.suffix + ".tmp")
    try:
        with zipfile.ZipFile(staging, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in files:
                info = zipfile.ZipInfo(path.relative_to(root).as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (0o100755 if path.suffix == ".sh" else 0o100644) << 16
                archive.writestr(info, contents[path.relative_to(root).as_posix()])
            info = zipfile.ZipInfo("PACKAGE_MANIFEST.json", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        staging.replace(destination)
    finally:
        staging.unlink(missing_ok=True)
    checksum = hashlib.sha256(destination.read_bytes()).hexdigest()
    destination.with_suffix(destination.suffix + ".sha256").write_text(checksum + "  " + destination.name + "\n", encoding="ascii")
    return destination, manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist/OsdagBridge-Reports.zip")
    parser.add_argument("--allow-dirty", action="store_true", help="Development only: package working files with an explicit dirty marker.")
    args = parser.parse_args(argv)
    try:
        revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
        status = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
        if status.strip():
            if not args.allow_dirty:
                raise ValueError("Commit source changes before creating a release package, or use --allow-dirty for a development build.")
            revision += "-dirty"
        package, manifest = build_package(ROOT, args.output, revision=revision)
        print("Package:", package)
        print("Source:", revision)
        print("Files:", len(manifest["files"]))
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        parser.exit(1, f"Packaging failed: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
