from __future__ import annotations
from pathlib import Path
from psair.core.logger import logger, get_rel_path


def find_matching_files(
    match_metadata_fields=None,
    directories=None,
    search_base="",
    search_ext=".xlsx",
    deduplicate=True,
):
    """
    Recursively find files matching metadata labels and a base pattern.

    Behavior
    --------
    • Searches all provided directories for filenames containing both
      `search_base` and every label in `match_metadata_fields` (case-sensitive).
    • Returns a list[Path] of matches (empty if none found).
    • Optionally deduplicates identical filenames across directories,
      logging which duplicates were removed.

    Parameters
    ----------
    match_metadata_fields : list[str] | None
        Metadata labels (e.g., ["AC", "PreTx"]). None/empty ignored.
    directories : Path | str | list[Path | str] | None
        One or more directories to search (default: CWD).
    search_base : str
        Core substring to match in filenames.
    search_ext : str, default ".xlsx"
        File extension (with dot).
    deduplicate : bool, default True
        Remove duplicate filenames across directories.

    Returns
    -------
    list[Path]
        Matching file paths (may be empty).
    """
    match_metadata_fields = [str(mt) for mt in (match_metadata_fields or []) if mt]
    if directories is None:
        directories = [Path.cwd()]
    elif isinstance(directories, (str, Path)):
        directories = [directories]

    all_matches = []
    for d in directories:
        try:
            d = Path(d)
            if not d.exists():
                logger.warning(f"Directory not found: {get_rel_path(d)} (skipping).")
                continue

            for f in d.rglob(f"*{search_base}*{search_ext}"):
                if all(mt in f.name for mt in match_metadata_fields):
                    all_matches.append(f)
        except Exception as e:
            logger.error(f"Error searching in {get_rel_path(d)}: {e}")

    if not all_matches:
        logger.warning(
            f"No matches found for base '{search_base}' with metadata labels {match_metadata_fields}."
        )
        return []

    if deduplicate:
        seen = {}
        duplicates = {}
        for f in all_matches:
            if f.name in seen:
                duplicates.setdefault(f.name, []).append(f)
            else:
                seen[f.name] = f

        unique_matches = list(seen.values())

        if duplicates:
            logger.warning(
                f"Removed {sum(len(v) for v in duplicates.values())} duplicate filename(s) across directories."
            )
            for fname, paths in duplicates.items():
                logger.warning(f"Duplicate filename '{fname}' found in:")
                for p in [seen[fname], *paths]:
                    logger.warning(f"  - {get_rel_path(p)}")

    else:
        unique_matches = all_matches

    if len(unique_matches) == 1:
        logger.info(f"Matched file for '{search_base}': {get_rel_path(unique_matches[0])}")
    else:
        logger.info(
            f"Multiple ({len(unique_matches)}) files matched '{search_base}' and {match_metadata_fields}."
        )
        for f in unique_matches:
            logger.debug(f"  - {get_rel_path(f)}")

    return unique_matches
