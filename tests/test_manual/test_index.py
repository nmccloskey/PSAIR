from __future__ import annotations

from pathlib import Path

from psair.manual.index import (
    build_manual_index,
    extract_md_title,
    numeric_sort_key,
    read_text_safely,
    render_generated_tree_text,
    search_manual,
)


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_numeric_sort_key_prioritizes_leading_numbers() -> None:
    names = ["intro.md", "10_late.md", "02_middle.md", "01_start.md"]

    assert sorted(names, key=numeric_sort_key) == [
        "01_start.md",
        "02_middle.md",
        "10_late.md",
        "intro.md",
    ]


def test_extract_md_title_uses_first_h1_or_fallback() -> None:
    assert extract_md_title("text\n# Real Title\n## Child", "fallback.md") == "Real Title"
    assert extract_md_title("## Not an H1", "fallback.md") == "fallback.md"


def test_read_text_safely_replaces_invalid_utf8(tmp_path: Path) -> None:
    path = tmp_path / "bad.md"
    path.write_bytes(b"# Title\nbad byte: \xff\n")

    text = read_text_safely(path)

    assert "Title" in text
    assert "\ufffd" in text


def test_build_manual_index_builds_tree_and_skips_outline(tmp_path: Path) -> None:
    manual = tmp_path / "manual"
    intro = write(manual / "01_intro.md", "# Introduction\nWelcome.")
    write(manual / "00_outline.md", "# Generated Outline\nShould be ignored.")
    write(manual / "section" / "02_topic.md", "# Topic\nNeedle topic text.")
    write(manual / "notes.txt", "# Not Markdown\nIgnored.")

    tree, flat = build_manual_index(manual)

    assert list(flat) == ["01_intro.md", "section/02_topic.md"]
    assert flat["01_intro.md"].abs_path == intro.resolve()
    assert flat["01_intro.md"].title == "Introduction"
    assert "00_outline.md" not in flat
    assert "section" in tree
    assert "02_topic.md" in tree["section"]


def test_build_manual_index_missing_directory_returns_empty(tmp_path: Path) -> None:
    tree, flat = build_manual_index(tmp_path / "missing")

    assert tree == {}
    assert flat == {}


def test_render_generated_tree_text_includes_directories_and_files(tmp_path: Path) -> None:
    manual = tmp_path / "manual"
    write(manual / "01_intro.md", "# Introduction")
    write(manual / "section" / "02_topic.md", "# Topic")
    tree, _flat = build_manual_index(manual)

    rendered = render_generated_tree_text(tree)

    assert rendered.startswith("Manual Map (Tree)")
    assert "01_intro.md" in rendered
    assert "section/" in rendered
    assert "02_topic.md" in rendered

    rendered_with_titles = render_generated_tree_text(tree, show_titles=True)
    assert "01_intro.md — Introduction" in rendered_with_titles
    assert "02_topic.md — Topic" in rendered_with_titles


def test_search_manual_scores_titles_and_content(tmp_path: Path) -> None:
    manual = tmp_path / "manual"
    write(manual / "01_alpha.md", "# Needle Guide\nOnly once.")
    write(manual / "02_beta.md", "# Beta\nneedle needle needle")
    write(manual / "03_gamma.md", "# Gamma\nNo match.")
    _tree, flat = build_manual_index(manual)

    results = search_manual(flat, "needle", limit=1)

    assert results == [("01_alpha.md", 6)]
    assert search_manual(flat, "   ") == []
