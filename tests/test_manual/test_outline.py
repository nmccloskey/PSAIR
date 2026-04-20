from __future__ import annotations

from pathlib import Path

from psair.manual.chars import scan_file
from psair.manual.outline import (
    Entry,
    build_manual_outline,
    build_tree,
    ensure_manual_outline,
    extract_title,
    iter_markdown_entries,
    normalize_exts,
    numeric_key,
    render_grouped_outline,
    render_outline_markdown,
    render_tree,
)


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_normalize_exts_accepts_plain_and_dotted_extensions() -> None:
    assert normalize_exts({"MD", ".markdown", " "}) == {".md", ".markdown"}
    assert normalize_exts(None) == {".md", ".markdown"}


def test_numeric_key_sorts_numbered_paths_before_unnumbered() -> None:
    names = ["appendix.md", "02_topic.md", "01_10_deep.md", "01_intro.md"]

    assert sorted(names, key=numeric_key) == [
        "01_intro.md",
        "01_10_deep.md",
        "02_topic.md",
        "appendix.md",
    ]


def test_extract_title_supports_atx_and_setext_headings(tmp_path: Path) -> None:
    atx = write(tmp_path / "atx.md", "\n## First Heading\nBody")
    setext = write(tmp_path / "setext.md", "Setext Heading\n==============\nBody")
    empty = write(tmp_path / "empty.md", "Body only")

    assert extract_title(atx) == "First Heading"
    assert extract_title(setext) == "Setext Heading"
    assert extract_title(empty) is None


def test_iter_markdown_entries_skips_hidden_pycache_and_excluded_names(tmp_path: Path) -> None:
    manual = tmp_path / "manual"
    write(manual / "02_second.md", "# Second")
    write(manual / "01_first.md", "# First")
    write(manual / ".hidden" / "03_hidden.md", "# Hidden")
    write(manual / "__pycache__" / "04_cache.md", "# Cache")
    write(manual / "00_outline.md", "# Generated")
    write(manual / "notes.txt", "# Ignored")

    entries = iter_markdown_entries(manual, exclude_names={"00_outline.md"})

    assert [(entry.rel_path.as_posix(), entry.title) for entry in entries] == [
        ("01_first.md", "First"),
        ("02_second.md", "Second"),
    ]


def test_build_tree_and_renderers_use_entries() -> None:
    entries = [
        Entry(Path("01_intro.md"), "Intro"),
        Entry(Path("section/02_topic.md"), "Topic"),
    ]

    tree = build_tree(entries)
    tree_lines = render_tree(tree, links=True)
    plain_tree_lines = render_tree(tree)
    grouped = render_grouped_outline(entries)

    assert "01_intro.md" in tree
    assert "section" in tree
    assert any("[01_intro.md" in line and "Intro" in line for line in tree_lines)
    assert any("01_intro.md — Intro" in line for line in plain_tree_lines)
    assert grouped[0] == "### Manual root"
    assert any("section/" in line for line in grouped)


def test_render_outline_markdown_contains_metadata_and_empty_message() -> None:
    markdown = render_outline_markdown(
        entries=[],
        manual_title="Demo Manual",
        manual_version="1.2.3",
        max_depth=None,
    )

    assert markdown.startswith("# Demo Manual")
    assert "**Version:** 1.2.3" in markdown
    assert "(No Markdown files found.)" in markdown


def test_build_manual_outline_writes_file_and_excludes_existing_outline(tmp_path: Path) -> None:
    manual = tmp_path / "manual"
    write(manual / "00_outline.md", "# Old Outline\nShould not list itself.")
    write(manual / "01_intro.md", "# Intro")

    output = build_manual_outline(
        manual,
        manual_title="Demo Manual",
        manual_version="9.9.9",
    )

    text = output.read_text(encoding="utf-8")
    assert output == (manual / "00_outline.md").resolve()
    assert "# Demo Manual" in text
    assert "01_intro.md" in text
    assert text.count("00_outline.md") == 0


def test_build_manual_outline_writes_lf_without_trailing_whitespace(tmp_path: Path) -> None:
    manual = tmp_path / "manual"
    write(manual / "01_intro.md", "# Intro")

    output = build_manual_outline(
        manual,
        manual_title="Demo Manual",
        manual_version="9.9.9",
    )

    raw = output.read_bytes()
    warnings, errors = scan_file(
        output,
        check_trailing=True,
        check_line_endings=True,
    )

    assert b"\r\n" not in raw
    assert warnings == []
    assert errors == []


def test_ensure_manual_outline_respects_if_missing_only(tmp_path: Path) -> None:
    manual = tmp_path / "manual"
    manual.mkdir()
    outline = write(manual / "00_outline.md", "# Keep Me\n")

    result = ensure_manual_outline(manual, if_missing_only=True)

    assert result == outline.resolve()
    assert outline.read_text(encoding="utf-8") == "# Keep Me\n"
