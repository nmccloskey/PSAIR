from __future__ import annotations

from pathlib import Path

import pytest

from psair.manual.chars import (
    Finding,
    apply_fixes,
    check_manual_chars,
    format_finding,
    iter_target_files,
    normalize_exts,
    run_manual_chars,
    scan_file,
)


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="")
    return path


def test_normalize_exts_defaults_and_normalizes_values() -> None:
    assert ".md" in normalize_exts(None)
    assert normalize_exts({"MD", ".YAML", " "}) == {".md", ".yaml"}


def test_iter_target_files_filters_extensions_hidden_and_pycache(tmp_path: Path) -> None:
    root = tmp_path / "docs"
    keep_md = write(root / "b.md", "b")
    keep_py = write(root / "a.py", "a")
    write(root / ".hidden" / "secret.md", "hidden")
    write(root / "__pycache__" / "cache.py", "cache")
    write(root / "image.png", "ignored")

    paths = iter_target_files(root)

    assert paths == [keep_py.resolve(), keep_md.resolve()]


def test_scan_file_reports_trailing_crlf_nonascii_and_control_characters(tmp_path: Path) -> None:
    path = tmp_path / "manual.md"
    path.write_bytes("Clean\r\nCafe é  \r\nBad \x07 bell\r\n".encode("utf-8"))

    warnings, errors = scan_file(
        path,
        report_nonascii=True,
        fail_on_controls=True,
        check_trailing=True,
        check_line_endings=True,
    )

    warning_kinds = [finding.kind for finding in warnings]
    error_kinds = [finding.kind for finding in errors]
    assert "line_endings" in warning_kinds
    assert "trailing_whitespace" in warning_kinds
    assert "nonascii" in warning_kinds
    assert error_kinds == ["control_char"]


def test_scan_file_can_treat_nonascii_as_error(tmp_path: Path) -> None:
    path = write(tmp_path / "manual.md", "Cafe é\n")

    warnings, errors = scan_file(path, fail_on_nonascii=True)

    assert warnings == []
    assert len(errors) == 1
    assert errors[0].kind == "nonascii"


def test_apply_fixes_strips_trailing_whitespace_normalizes_lf_and_removes_controls(
    tmp_path: Path,
) -> None:
    path = tmp_path / "manual.md"
    path.write_bytes(b"Alpha  \r\nBad \x07 bell\t \r\n")

    changed = apply_fixes(
        path,
        strip_trailing=True,
        fix_line_endings="lf",
        remove_control_chars=True,
    )

    assert changed is True
    assert path.read_bytes() == b"Alpha\nBad  bell\n"


def test_apply_fixes_rejects_unknown_line_ending_mode(tmp_path: Path) -> None:
    path = write(tmp_path / "manual.md", "Alpha\n")

    with pytest.raises(ValueError, match="fix_line_endings"):
        apply_fixes(path, fix_line_endings="native")


def test_check_manual_chars_collects_findings_and_fixed_files(tmp_path: Path) -> None:
    root = tmp_path / "docs"
    dirty = write(root / "dirty.md", "Trailing   \n")

    result = check_manual_chars(
        root,
        check_trailing=True,
        strip_trailing=True,
        warnings_as_errors=True,
    )

    assert result.ok is True
    assert result.fixed_files == [dirty.resolve()]
    assert result.scanned_files == [dirty.resolve()]
    assert result.total_findings == 0
    assert dirty.read_text(encoding="utf-8") == "Trailing\n"


def test_check_manual_chars_promotes_warnings_to_errors(tmp_path: Path) -> None:
    root = tmp_path / "docs"
    write(root / "dirty.md", "Trailing   \n")

    result = check_manual_chars(
        root,
        check_trailing=True,
        warnings_as_errors=True,
    )

    assert result.ok is False
    assert result.warnings == []
    assert [finding.kind for finding in result.errors] == ["trailing_whitespace"]


def test_check_manual_chars_requires_existing_directory(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        check_manual_chars(tmp_path / "missing")


def test_format_finding_and_run_manual_chars_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = tmp_path / "docs"
    path = write(root / "manual.md", "Bad \x07 bell\n")
    finding = Finding(path=path, line_no=1, kind="control_char", message="bad", line="Bad")

    assert "control_char" in format_finding(finding)
    assert "Bad" in format_finding(finding)

    exit_code = run_manual_chars(root, summary_only=True)
    out = capsys.readouterr().out

    assert exit_code == 1
    assert "Files scanned: 1" in out
    assert "Errors: 1" in out
