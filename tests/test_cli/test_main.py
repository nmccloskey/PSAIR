from __future__ import annotations

from pathlib import Path

import pytest

from psair.cli import main as cli


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_parse_csv_exts_uses_normalizer() -> None:
    assert cli._parse_csv_exts("md, .txt, ", lambda parts: {p.upper() for p in parts}) == {
        "MD",
        ".TXT",
    }
    assert cli._parse_csv_exts(None, lambda parts: parts) is None


def test_main_index_tree_and_search_commands(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manual = tmp_path / "manual"
    write(manual / "01_intro.md", "# Intro\nNeedle text.")
    write(manual / "section" / "02_topic.md", "# Topic\nMore text.")

    assert cli.main(["index", str(manual), "--show-files"]) == 0
    index_out = capsys.readouterr().out
    assert "files_indexed: 2" in index_out
    assert "01_intro.md" in index_out

    assert cli.main(["tree", str(manual)]) == 0
    tree_out = capsys.readouterr().out
    assert "Manual Map (Tree)" in tree_out
    assert "section/" in tree_out

    assert cli.main(["search", "needle", str(manual), "--limit", "5"]) == 0
    search_out = capsys.readouterr().out
    assert "01_intro.md" in search_out
    assert "Intro" in search_out


def test_main_commands_report_missing_or_empty_manual(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    missing = tmp_path / "missing"
    empty = tmp_path / "empty"
    empty.mkdir()

    assert cli.main(["tree", str(missing)]) == 1
    assert "Manual directory not found" in capsys.readouterr().err

    assert cli.main(["search", "anything", str(empty)]) == 1
    assert "No markdown files found" in capsys.readouterr().err


def test_main_outline_and_chars_commands(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manual = tmp_path / "manual"
    write(manual / "01_intro.md", "# Intro\nClean text.\n")
    outline = tmp_path / "outline.md"

    assert cli.main(
        [
            "outline",
            str(manual),
            "--output",
            str(outline),
            "--title",
            "CLI Manual",
            "--version",
            "1.0",
        ]
    ) == 0
    outline_out = capsys.readouterr().out
    assert "Wrote outline:" in outline_out
    assert "# CLI Manual" in outline.read_text(encoding="utf-8")

    assert cli.main(["chars", str(manual), "--summary-only"]) == 0
    chars_out = capsys.readouterr().out
    assert "Files scanned: 1" in chars_out
    assert "Errors: 0" in chars_out


def test_main_chars_returns_error_for_findings(tmp_path: Path) -> None:
    manual = tmp_path / "manual"
    write(manual / "01_intro.md", "Bad \x07 bell\n")

    assert cli.main(["chars", str(manual), "--summary-only", "--fail-on-controls"]) == 1


def test_main_pdf_skip_preflight_calls_pdf_builder(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manual = tmp_path / "manual"
    write(manual / "01_intro.md", "# Intro")
    output = tmp_path / "manual.pdf"
    captured: dict[str, object] = {}

    def fake_build_manual_pdf(*args: object, **kwargs: object) -> Path:
        captured["manual_dir"] = args[0]
        captured.update(kwargs)
        output.write_bytes(b"%PDF-1.4\n")
        return output

    monkeypatch.setattr(cli, "build_manual_pdf", fake_build_manual_pdf)

    assert cli.main(
        [
            "pdf",
            str(manual),
            "--skip-outline",
            "--skip-chars",
            "--output",
            str(output),
            "--no-toc",
            "--exts",
            "md",
        ]
    ) == 0

    out = capsys.readouterr().out
    assert "Wrote PDF:" in out
    assert captured["manual_dir"] == manual.resolve()
    assert captured["output_path"] == output.resolve()
    assert captured["toc"] is False
    assert captured["include_exts"] == {".md"}


def test_main_pdf_aborts_noninteractive_when_char_issues_exist(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manual = tmp_path / "manual"
    write(manual / "01_intro.md", "Bad \x07 bell\n")
    called = False

    def fake_build_manual_pdf(*args: object, **kwargs: object) -> Path:
        nonlocal called
        called = True
        return tmp_path / "never.pdf"

    monkeypatch.setattr(cli, "build_manual_pdf", fake_build_manual_pdf)

    assert cli.main(
        [
            "pdf",
            str(manual),
            "--skip-outline",
            "--non-interactive",
            "--fail-on-controls",
        ]
    ) == 1
    assert called is False
    assert "Aborting in non-interactive mode" in capsys.readouterr().err


def test_main_pdf_force_proceeds_past_char_issues(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manual = tmp_path / "manual"
    write(manual / "01_intro.md", "Bad \x07 bell\n")

    monkeypatch.setattr(cli, "build_manual_pdf", lambda *args, **kwargs: tmp_path / "manual.pdf")

    assert cli.main(["pdf", str(manual), "--skip-outline", "--force"]) == 0
