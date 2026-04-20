from __future__ import annotations

from pathlib import Path

from psair.metadata.discovery import find_matching_files


def touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("data", encoding="utf-8")
    return path


def test_find_matching_files_matches_base_extension_and_metadata_fields(tmp_path: Path) -> None:
    root = tmp_path / "root"
    match = touch(root / "study_AC_Pre.xlsx")
    touch(root / "study_AC_Post.xlsx")
    touch(root / "notes_AC_Pre.txt")

    results = find_matching_files(
        match_metadata_fields=["AC", "Pre"],
        directories=root,
        search_base="study",
        search_ext=".xlsx",
    )

    assert results == [match]


def test_find_matching_files_deduplicates_by_filename(tmp_path: Path) -> None:
    first = touch(tmp_path / "a" / "study_AC_Pre.xlsx")
    duplicate = touch(tmp_path / "b" / "study_AC_Pre.xlsx")

    deduped = find_matching_files(
        match_metadata_fields=["AC"],
        directories=[tmp_path / "a", tmp_path / "b"],
        search_base="study",
        search_ext=".xlsx",
        deduplicate=True,
    )
    all_matches = find_matching_files(
        match_metadata_fields=["AC"],
        directories=[tmp_path / "a", tmp_path / "b"],
        search_base="study",
        search_ext=".xlsx",
        deduplicate=False,
    )

    assert deduped == [first]
    assert all_matches == [first, duplicate]


def test_find_matching_files_handles_missing_directories_and_no_matches(tmp_path: Path) -> None:
    results = find_matching_files(
        match_metadata_fields=["AC"],
        directories=[tmp_path / "missing"],
        search_base="study",
        search_ext=".xlsx",
    )

    assert results == []


def test_find_matching_files_defaults_to_current_directory(
    tmp_path: Path,
    monkeypatch,
) -> None:
    match = touch(tmp_path / "baseline.xlsx")
    monkeypatch.chdir(tmp_path)

    assert find_matching_files(search_base="base", search_ext=".xlsx") == [match]
