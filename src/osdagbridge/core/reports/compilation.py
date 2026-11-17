"""Discover and run a LaTeX compiler without a shell or GUI dependencies."""

import importlib
import os
from pathlib import Path
import shutil
import subprocess


class ReportCompilationError(RuntimeError):
    """The source is retained, but a verified PDF could not be produced."""


def find_compiler(explicit=None):
    """Prefer an explicit executable, the Osdag bundle, then PATH compilers."""
    selected = explicit or os.environ.get("OSDAGBRIDGE_LATEX_COMPILER")
    if selected:
        executable = shutil.which(str(selected))
        if executable:
            return str(Path(executable).resolve())
        raise ReportCompilationError(f"LaTeX compiler was not found: {selected}")
    try:
        environment = importlib.import_module("osdag_latex_env.__main__").OsdagLatexEnv()
        if environment.pdflatex and Path(environment.pdflatex).is_file():
            return str(environment.pdflatex)
    except (ImportError, AttributeError, OSError):
        pass
    for name in ("pdflatex", "tectonic"):
        executable = shutil.which(name)
        if executable:
            return executable
    local = Path(__file__).resolve().parents[4] / ".tools" / ("tectonic.exe" if os.name == "nt" else "tectonic")
    if local.is_file():
        return str(local)
    raise ReportCompilationError(
        "No LaTeX compiler found. Install MiKTeX/TeX Live (pdflatex), or Tectonic, "
        "then set OSDAGBRIDGE_LATEX_COMPILER to its executable. "
        "The .tex source and assets are still available."
    )


def compile_latex(source, executable=None, timeout=300):
    """Compile in the source directory, retain diagnostics, reject partial PDFs."""
    source = Path(source).resolve()
    compiler = find_compiler(executable)
    tectonic = "tectonic" in Path(compiler).stem.lower()
    command = ([compiler, "--untrusted", "--keep-logs", "--keep-intermediates", source.name]
               if tectonic else
               [compiler, "-no-shell-escape", "-interaction=nonstopmode",
                "-halt-on-error", "-file-line-error", source.name])
    environment = os.environ.copy()
    environment["PATH"] = str(Path(compiler).parent) + os.pathsep + environment.get("PATH", "")
    diagnostics = []
    log = source.with_suffix(".compile.log")
    pdf = source.with_suffix(".pdf")
    # A successful process must create a fresh artifact; an earlier PDF cannot
    # turn an empty or failed compiler run into apparent success.
    pdf.unlink(missing_ok=True)
    try:
        for _ in range(1 if tectonic else 2):
            try:
                result = subprocess.run(
                    command, cwd=source.parent, capture_output=True, check=False,
                    timeout=timeout, env=environment,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise ReportCompilationError(f"LaTeX compilation failed: {exc}") from exc
            output = (result.stdout + result.stderr).decode("utf-8", errors="replace")
            diagnostics.append(output)
            if result.returncode:
                raise ReportCompilationError(
                    f"LaTeX exited with status {result.returncode}. See {log.name}.\n"
                    + "\n".join(output.splitlines()[-12:])
                )
        if not pdf.is_file() or not pdf.read_bytes().startswith(b"%PDF-"):
            raise ReportCompilationError("LaTeX exited successfully but produced no valid PDF.")
        return pdf
    finally:
        log.write_text("\n".join(diagnostics), encoding="utf-8")
