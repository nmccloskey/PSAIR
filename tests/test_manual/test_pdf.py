from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from psair.manual import pdf
from psair.manual.pdf import (
    add_pagebreaks_between_sections,
    assemble_markdown,
    build_manual_pdf,
    build_pandoc_extra_args,
    iter_markdown_files,
    render_pandoc_metadata_text,
    resolve_project_version,
    normalize_exts,
    resolve_executable,
    run_pandoc,
    strip_leading_heading_numbers,
)


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_normalize_exts_defaults_and_normalizes_values() -> None:
    assert normalize_exts(None) == {".md", ".markdown"}
    assert normalize_exts({"MD", ".markdown"}) == {".md", ".markdown"}


def test_iter_markdown_files_filters_outline_hidden_and_pycache(tmp_path: Path) -> None:
    manual = tmp_path / "manual"
    first = write(manual / "01_intro.md", "# Intro")
    second = write(manual / "section" / "02_topic.markdown", "# Topic")
    outline = write(manual / "00_outline.md", "# Outline")
    write(manual / ".hidden" / "03_hidden.md", "# Hidden")
    write(manual / "__pycache__" / "04_cache.md", "# Cache")
    write(manual / "notes.txt", "# Ignored")

    assert iter_markdown_files(manual) == [first.resolve(), second.resolve()]
    assert outline.resolve() in iter_markdown_files(manual, include_outline=True)


def test_strip_leading_heading_numbers_removes_numeric_prefixes_only_from_headings() -> None:
    text = "# 03 Overview\nBody 03 stays\n## 03_02 - Methods\n"

    stripped = strip_leading_heading_numbers(text)

    assert "# Overview" in stripped
    assert "Body 03 stays" in stripped
    assert "## Methods" in stripped


def test_add_pagebreaks_and_assemble_markdown(tmp_path: Path) -> None:
    manual = tmp_path / "manual"
    first = write(manual / "01_intro.md", "# 01 Intro\nAlpha\n")
    second = write(manual / "02_topic.md", "# 02 Topic\nBeta\n")

    assert add_pagebreaks_between_sections([]) == ""
    assert "\\newpage" in add_pagebreaks_between_sections(["A", "B"])

    assembled = assemble_markdown(
        [first, second],
        manual_dir=manual,
        pagebreaks=False,
        file_dividers=True,
    )

    assert "<!-- BEGIN FILE: 01_intro.md -->" in assembled
    assert "# Intro" in assembled
    assert "# Topic" in assembled
    assert "\\newpage" not in assembled


def test_build_pandoc_extra_args_combines_toc_margin_and_extra_args() -> None:
    assert build_pandoc_extra_args(
        margin="0.8in",
        toc=True,
        toc_depth=2,
        extra_pandoc_args=["--number-sections"],
    ) == [
        "--toc",
        "--toc-depth",
        "2",
        "-V",
        "geometry:margin=0.8in",
        "--number-sections",
    ]

    assert build_pandoc_extra_args(toc=False, margin=None) == []


def test_resolve_executable_uses_path_or_raises_helpful_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pdf.shutil, "which", lambda name: "C:/bin/pandoc.exe")
    assert resolve_executable("pandoc") == "C:/bin/pandoc.exe"

    monkeypatch.setattr(pdf.shutil, "which", lambda name: None)
    with pytest.raises(FileNotFoundError, match="Required executable"):
        resolve_executable("definitely-not-pandoc")


def test_resolve_project_version_prefers_nearest_pyproject(tmp_path: Path) -> None:
    project = tmp_path / "project"
    write(project / "pyproject.toml", '[project]\nname = "demo"\nversion = "1.2.3"\n')
    nested = project / "docs" / "manual"
    nested.mkdir(parents=True)

    assert resolve_project_version(nested) == "1.2.3"


def test_render_pandoc_metadata_text_expands_ssot_placeholders(tmp_path: Path) -> None:
    project = tmp_path / "project"
    write(project / "pyproject.toml", '[project]\nname = "demo"\nversion = "1.2.3"\n')
    yaml_path = write(
        project / "docs" / "manual_pdf.yaml",
        "\n".join(
            [
                'title: "Demo Manual"',
                'version: "{package_version}"',
                'date: "Version {version}"',
                "header-includes:",
                r"  - \usepackage{fancyhdr}",
                r"  - \fancyhead[L]{title}",
                r"  - \fancyhead[R]{date}",
                "",
            ]
        ),
    )

    rendered = render_pandoc_metadata_text(yaml_path)

    assert 'version: "1.2.3"' in rendered
    assert 'date: "Version 1.2.3"' in rendered
    assert r"\fancyhead[L]{Demo Manual}" in rendered
    assert r"\fancyhead[R]{Version 1.2.3}" in rendered
    assert r"\usepackage{fancyhdr}" in rendered


def test_run_pandoc_builds_command_and_decodes_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    markdown = write(tmp_path / "manual.md", "# Manual")
    output = tmp_path / "manual.pdf"
    yaml = write(tmp_path / "manual_pdf.yaml", "title: Manual\n")
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], capture_output: bool, text: bool) -> subprocess.CompletedProcess:
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout=b"", stderr=b"")

    monkeypatch.setattr(pdf, "resolve_executable", lambda name: "pandoc-bin")
    monkeypatch.setattr(pdf.subprocess, "run", fake_run)

    run_pandoc(
        markdown_path=markdown,
        output_path=output,
        yaml_path=yaml,
        extra_args=["--toc"],
    )

    assert calls == [
        [
            "pandoc-bin",
            str(markdown),
            "-o",
            str(output),
            "--pdf-engine",
            "xelatex",
            "--metadata-file",
            str(yaml),
            "--toc",
        ]
    ]

    def failing_run(cmd: list[str], capture_output: bool, text: bool) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(cmd, 2, stdout=b"out", stderr=b"err")

    monkeypatch.setattr(pdf.subprocess, "run", failing_run)
    with pytest.raises(RuntimeError, match="exit code 2"):
        run_pandoc(markdown_path=markdown, output_path=output)


def test_build_manual_pdf_assembles_temp_markdown_and_invokes_pandoc(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manual = tmp_path / "manual"
    write(manual / "manual_pdf.yaml", "title: Demo\n")
    write(manual / "00_outline.md", "# Outline")
    write(manual / "01_intro.md", "# 01 Intro\nAlpha")
    write(manual / "02_topic.md", "# 02 Topic\nBeta")
    output = tmp_path / "out" / "manual.pdf"
    temp_md = tmp_path / "assembled.md"
    captured: dict[str, object] = {}

    def fake_run_pandoc(**kwargs: object) -> None:
        captured.update(kwargs)
        Path(kwargs["output_path"]).write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(pdf, "run_pandoc", fake_run_pandoc)

    result = build_manual_pdf(
        manual,
        output_path=output,
        temp_md_path=temp_md,
        include_outline=False,
        toc_depth=2,
        margin="1in",
    )

    assembled = temp_md.read_text(encoding="utf-8")
    assert result == output.resolve()
    assert output.exists()
    assert "# Intro" in assembled
    assert "# Topic" in assembled
    assert "# Outline" not in assembled
    assert captured["markdown_path"] == temp_md.resolve()
    assert captured["yaml_path"] == (manual / "manual_pdf.yaml").resolve()
    assert captured["extra_args"] == ["--toc", "--toc-depth", "2", "-V", "geometry:margin=1in"]


def test_build_manual_pdf_requires_manual_dir_and_markdown_files(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="manual_dir"):
        build_manual_pdf(tmp_path / "missing")

    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(FileNotFoundError, match="No markdown files"):
        build_manual_pdf(empty)
