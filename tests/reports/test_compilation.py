"""Compiler failure and artifact verification tests without a TeX installation."""

from pathlib import Path
import subprocess

import pytest

from osdagbridge.core.reports import compilation


@pytest.fixture
def source(tmp_path):
    path = tmp_path / "report.tex"
    path.write_text(r"\documentclass{article}\begin{document}Report\end{document}", encoding="utf-8")
    return path


def test_explicit_missing_compiler_is_an_actionable_error(monkeypatch):
    monkeypatch.setattr(compilation.shutil, "which", lambda executable: None)
    with pytest.raises(compilation.ReportCompilationError, match="not found.*missing-compiler"):
        compilation.find_compiler("missing-compiler")


def test_environment_can_select_a_compiler(monkeypatch):
    monkeypatch.setenv("OSDAGBRIDGE_LATEX_COMPILER", "chosen-compiler")
    monkeypatch.setattr(compilation.shutil, "which", lambda executable: "/bin/selected" if executable == "chosen-compiler" else None)
    assert compilation.find_compiler() == str(Path("/bin/selected").resolve())


@pytest.mark.parametrize("compiler,passes,protection", [
    ("pdflatex", 2, "-no-shell-escape"),
    ("tectonic", 1, "--untrusted"),
])
def test_compilers_write_pdf_with_expected_passes_and_safe_arguments(source, monkeypatch, compiler, passes, protection):
    executable = str(source.parent / "bin" / compiler)
    monkeypatch.setattr(compilation, "find_compiler", lambda explicit=None: executable)
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        source.with_suffix(".pdf").write_bytes(b"%PDF-1.7\nverified fixture")
        return subprocess.CompletedProcess(command, 0, stdout=b"Typeset report\n", stderr=b"")

    monkeypatch.setattr(compilation.subprocess, "run", run)
    pdf = compilation.compile_latex(source, timeout=17)

    assert pdf == source.with_suffix(".pdf")
    assert len(calls) == passes
    for command, kwargs in calls:
        assert command[0] == executable
        assert protection in command
        assert command[-1] == source.name
        assert kwargs["cwd"] == source.parent
        assert kwargs["timeout"] == 17
        assert kwargs.get("shell", False) is False
    assert source.with_suffix(".compile.log").read_text(encoding="utf-8").count("Typeset report") == passes


def test_nonzero_exit_retains_diagnostics_and_rejects_partial_pdf(source, monkeypatch):
    monkeypatch.setattr(compilation, "find_compiler", lambda explicit=None: "pdflatex")

    def run(command, **kwargs):
        source.with_suffix(".pdf").write_bytes(b"%PDF-1.7\npartial")
        return subprocess.CompletedProcess(command, 1, stdout=b"Undefined control sequence\n", stderr=b"bad byte: \xff")

    monkeypatch.setattr(compilation.subprocess, "run", run)
    with pytest.raises(compilation.ReportCompilationError, match="status 1"):
        compilation.compile_latex(source)
    assert "Undefined control sequence" in source.with_suffix(".compile.log").read_text(encoding="utf-8")
    assert source.is_file()


def test_second_pdflatex_pass_failure_is_reported(source, monkeypatch):
    monkeypatch.setattr(compilation, "find_compiler", lambda explicit=None: "pdflatex")
    statuses = iter([0, 2])

    def run(command, **kwargs):
        source.with_suffix(".pdf").write_bytes(b"%PDF-1.7\nfirst pass only")
        status = next(statuses)
        return subprocess.CompletedProcess(command, status, stdout=f"pass exit {status}".encode(), stderr=b"")

    monkeypatch.setattr(compilation.subprocess, "run", run)
    with pytest.raises(compilation.ReportCompilationError, match="status 2"):
        compilation.compile_latex(source)
    log = source.with_suffix(".compile.log").read_text(encoding="utf-8")
    assert "pass exit 0" in log and "pass exit 2" in log


@pytest.mark.parametrize("failure", [
    FileNotFoundError("compiler disappeared"),
    subprocess.TimeoutExpired("pdflatex", 7),
])
def test_launch_failure_and_timeout_are_wrapped_and_source_is_retained(source, monkeypatch, failure):
    monkeypatch.setattr(compilation, "find_compiler", lambda explicit=None: "pdflatex")

    def run(command, **kwargs):
        raise failure

    monkeypatch.setattr(compilation.subprocess, "run", run)
    with pytest.raises(compilation.ReportCompilationError, match="LaTeX compilation failed"):
        compilation.compile_latex(source, timeout=7)
    assert source.is_file()
    assert source.with_suffix(".compile.log").is_file()


@pytest.mark.parametrize("output", [None, b"not a PDF"])
def test_successful_exit_without_valid_pdf_is_an_error(source, monkeypatch, output):
    monkeypatch.setattr(compilation, "find_compiler", lambda explicit=None: "pdflatex")

    def run(command, **kwargs):
        if output is not None:
            source.with_suffix(".pdf").write_bytes(output)
        return subprocess.CompletedProcess(command, 0, stdout=b"", stderr=b"")

    monkeypatch.setattr(compilation.subprocess, "run", run)
    with pytest.raises(compilation.ReportCompilationError, match="no valid PDF"):
        compilation.compile_latex(source)


def test_stale_pdf_does_not_count_as_a_new_compilation(source, monkeypatch):
    source.with_suffix(".pdf").write_bytes(b"%PDF-1.7\nstale previous result")
    monkeypatch.setattr(compilation, "find_compiler", lambda explicit=None: "pdflatex")
    monkeypatch.setattr(compilation.subprocess, "run", lambda command, **kwargs: subprocess.CompletedProcess(command, 0, stdout=b"", stderr=b""))

    with pytest.raises(compilation.ReportCompilationError, match="no valid PDF"):
        compilation.compile_latex(source)
