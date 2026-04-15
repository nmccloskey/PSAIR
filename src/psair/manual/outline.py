from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any


MD_EXTS = {".md", ".markdown"}
_NUM_RE = re.compile(r"^\d+(?:[_-]\d+)*")


@dataclass(frozen=True)
class Entry:
    """
    A manual file entry relative to the manual root.
    """
    rel_path: Path
    title: Optional[str]


def normalize_exts(exts: set[str] | None) -> set[str]:
    """
    Normalize extension strings to lowercase dotted forms.

    Example
    -------
    {"md", ".markdown"} -> {".md", ".markdown"}
    """
    if not exts:
        return set(MD_EXTS)

    normalized = {e.strip().lower() for e in exts if e and e.strip()}
    return {("." + e) if not e.startswith(".") else e for e in normalized}


def numeric_key(name: str) -> Tuple:
    """
    Sort key that respects leading numeric prefixes like:

      00_outline.md
      03_workflow
      03_02_transcript_tables.md

    Falls back to lexicographic order when no prefix exists.
    """
    stem = name
    if "." in stem:
        stem = stem.rsplit(".", 1)[0]

    match = _NUM_RE.match(stem)
    if not match:
        return (1, stem.lower())

    prefix = match.group(0)
    parts = re.split(r"[_-]", prefix)
    nums = tuple(int(p) for p in parts if p.isdigit())
    rest = stem[len(prefix):].lstrip("_-").lower()
    return (0, nums, rest)


def extract_title(md_path: Path) -> Optional[str]:
    """
    Extract the first Markdown heading from a file.

    Strategy
    --------
    1. First ATX heading (# Title)
    2. Else first plausible Setext heading (Title + ==== / ----)
    """
    try:
        text = md_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            title = stripped.lstrip("#").strip()
            if title:
                return title

    lines = text.splitlines()
    for i in range(len(lines) - 1):
        title_line = lines[i].strip()
        underline = lines[i + 1].strip()

        if not title_line:
            continue

        if set(underline) <= {"="} or set(underline) <= {"-"}:
            if len(underline) >= max(3, len(title_line) // 2):
                return title_line

    return None


def iter_markdown_entries(
    manual_dir: Path,
    *,
    include_exts: set[str] | None = None,
    exclude_names: set[str] | None = None,
) -> List[Entry]:
    """
    Collect markdown entries under manual_dir, skipping hidden paths and __pycache__.
    """
    include_exts = normalize_exts(include_exts)
    exclude_names = exclude_names or set()

    manual_dir = manual_dir.resolve()
    entries: List[Entry] = []

    for path in manual_dir.rglob("*"):
        rel = path.relative_to(manual_dir)

        if any(part.startswith(".") for part in rel.parts):
            continue
        if "__pycache__" in rel.parts:
            continue
        if path.name in exclude_names:
            continue

        if path.is_file() and path.suffix.lower() in include_exts:
            entries.append(
                Entry(
                    rel_path=rel,
                    title=extract_title(path),
                )
            )

    entries.sort(key=lambda e: tuple(numeric_key(part) for part in e.rel_path.parts))
    return entries


def build_tree(entries: List[Entry]) -> Dict[str, Any]:
    """
    Build a nested dict tree.

    Directories are dicts.
    Files are Entry objects.
    """
    tree: Dict[str, Any] = {}

    for entry in entries:
        cursor = tree
        parts = list(entry.rel_path.parts)

        for segment in parts[:-1]:
            cursor = cursor.setdefault(segment, {})

        cursor[parts[-1]] = entry

    return tree


def render_tree(
    tree: Dict[str, Any],
    *,
    base_rel: Path = Path("."),
    prefix: str = "",
    max_depth: Optional[int] = None,
    depth: int = 0,
    links: bool = False,
    show_titles: bool = True,
    indent_mid: str = "│   ",
    indent_last: str = "    ",
) -> List[str]:
    """
    Render a tree dict into unicode tree lines.

    Parameters
    ----------
    links
        If True, render Markdown links for files.
    show_titles
        If True, append extracted titles to file labels when links=True.
    indent_mid / indent_last
        Indentation fragments used to build child prefixes.

    Notes
    -----
    The default rendering is intentionally clean and filesystem-like.
    """
    if max_depth is not None and depth > max_depth:
        return []

    keys = sorted(tree.keys(), key=numeric_key)
    lines: List[str] = []

    for i, key in enumerate(keys):
        last = i == len(keys) - 1
        branch = "└── " if last else "├── "
        next_prefix = prefix + (indent_last if last else indent_mid)
        node = tree[key]

        if isinstance(node, dict):
            lines.append(f"{prefix}{branch}{key}/")
            lines.extend(
                render_tree(
                    node,
                    base_rel=base_rel / key,
                    prefix=next_prefix,
                    max_depth=max_depth,
                    depth=depth + 1,
                    links=links,
                    show_titles=show_titles,
                    indent_mid=indent_mid,
                    indent_last=indent_last,
                )
            )
        else:
            if not links:
                lines.append(f"{prefix}{branch}{key}")
            else:
                rel_link = (base_rel / key).as_posix()
                label = key
                if show_titles and node.title:
                    label = f"{key} — {node.title}"
                lines.append(f"{prefix}{branch}[{label}]({rel_link})")

    return lines


def render_grouped_outline(entries: List[Entry]) -> List[str]:
    """
    Render a grouped bullet outline, grouped by directory.
    """
    entries_sorted = sorted(
        entries,
        key=lambda e: tuple(numeric_key(part) for part in e.rel_path.parts),
    )

    lines: List[str] = []
    current_dir: Optional[Path] = None

    for entry in entries_sorted:
        parent = entry.rel_path.parent

        if current_dir != parent:
            if lines:
                lines.append("")
            heading = "Manual root" if str(parent) == "." else f"{parent.as_posix()}/"
            lines.append(f"### {heading}")
            current_dir = parent

        link = entry.rel_path.as_posix()
        fname = entry.rel_path.name
        if entry.title:
            lines.append(f"- [{fname} — {entry.title}]({link})")
        else:
            lines.append(f"- [{fname}]({link})")

    return lines


def render_outline_markdown(
    *,
    entries: List[Entry],
    manual_title: str,
    manual_version: str,
    max_depth: Optional[int],
) -> str:
    """
    Render the full outline markdown text.
    """
    tree = build_tree(entries)
    tree_lines = render_tree(tree, base_rel=Path("."), max_depth=max_depth)
    outline_lines = render_grouped_outline(entries)
    today = _dt.date.today().isoformat()

    md: List[str] = []
    md.append(f"# {manual_title}")
    md.append("")
    md.append(f"**Version:** {manual_version}  ")
    md.append(f"**Generated:** {today}  ")
    md.append("")
    md.append("---")
    md.append("")
    md.append("## Manual Map (Tree)")
    md.append("")
    md.append("```")
    md.extend(tree_lines if tree_lines else ["(No Markdown files found.)"])
    md.append("```")
    md.append("")
    md.append("## Outline (Links)")
    md.append("")
    md.extend(outline_lines if outline_lines else ["(No Markdown files found.)"])
    md.append("")
    md.append("---")
    md.append("")
    md.append("## Notes")
    md.append("")
    md.append("- Regenerate this file after adding or renaming manual sections.")
    md.append("- Keep numeric prefixes stable to preserve predictable ordering.")
    md.append("- This outline is a derived support artifact for navigation and build workflows.")
    md.append("")

    return "\n".join(md)


def build_manual_outline(
    manual_dir: Path,
    *,
    output_path: Path | None = None,
    manual_title: str = "Instruction Manual",
    manual_version: str = "0.0.0",
    include_exts: set[str] | None = None,
    max_depth: Optional[int] = None,
) -> Path:
    """
    Build and write a manual outline markdown file.

    Returns
    -------
    Path
        The written outline path.
    """
    manual_dir = manual_dir.resolve()
    if not manual_dir.exists() or not manual_dir.is_dir():
        raise FileNotFoundError(f"manual_dir does not exist or is not a directory: {manual_dir}")

    output_path = (output_path or (manual_dir / "00_outline.md")).resolve()

    exclude_names = {output_path.name} if output_path.parent == manual_dir else set()
    entries = iter_markdown_entries(
        manual_dir,
        include_exts=include_exts,
        exclude_names=exclude_names,
    )

    markdown = render_outline_markdown(
        entries=entries,
        manual_title=manual_title,
        manual_version=manual_version,
        max_depth=max_depth,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    return output_path


def ensure_manual_outline(
    manual_dir: Path,
    *,
    output_path: Path | None = None,
    manual_title: str = "Instruction Manual",
    manual_version: str = "0.0.0",
    include_exts: set[str] | None = None,
    max_depth: Optional[int] = None,
    if_missing_only: bool = True,
) -> Path:
    """
    Ensure that an outline file exists.

    If if_missing_only is True, write only when the output file does not exist.
    Otherwise always rebuild.
    """
    manual_dir = manual_dir.resolve()
    output_path = (output_path or (manual_dir / "00_outline.md")).resolve()

    if if_missing_only and output_path.exists():
        return output_path

    return build_manual_outline(
        manual_dir,
        output_path=output_path,
        manual_title=manual_title,
        manual_version=manual_version,
        include_exts=include_exts,
        max_depth=max_depth,
    )


def run_manual_outline(
    manual_dir: Path,
    *,
    output_path: Path | None = None,
    manual_title: str = "Instruction Manual",
    manual_version: str = "0.0.0",
    include_exts: set[str] | None = None,
    max_depth: int | None = None,
    if_missing_only: bool = True,
) -> Path:
    return ensure_manual_outline(
        manual_dir,
        output_path=output_path,
        manual_title=manual_title,
        manual_version=manual_version,
        include_exts=include_exts,
        max_depth=max_depth,
        if_missing_only=if_missing_only,
    )
