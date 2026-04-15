from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Dict, List, Tuple, Union


@dataclass(frozen=True)
class ManualFile:
    rel_path: Path
    abs_path: Path
    title: str
    text: str


TreeNode = Dict[str, Union["TreeNode", ManualFile]]
_NUM_PREFIX_RE = re.compile(r"^(\d+)[_-]")


def numeric_sort_key(name: str) -> Tuple[int, str]:
    m = _NUM_PREFIX_RE.match(name)
    if m:
        return (int(m.group(1)), name.lower())
    return (10_000, name.lower())


def read_text_safely(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def extract_md_title(md_text: str, fallback: str) -> str:
    for line in md_text.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def build_manual_index(manual_dir: str | Path) -> Tuple[TreeNode, Dict[str, ManualFile]]:
    manual_root = Path(manual_dir).resolve()
    tree: TreeNode = {}
    flat: Dict[str, ManualFile] = {}

    if not manual_root.exists():
        return tree, flat

    md_paths = sorted(
        [p for p in manual_root.rglob("*.md") if p.is_file()],
        key=lambda p: [numeric_sort_key(part) for part in p.relative_to(manual_root).parts],
    )

    for abs_path in md_paths:
        if abs_path.name == "00_outline.md":
            continue

        rel_path = abs_path.relative_to(manual_root)
        rel_str = rel_path.as_posix()

        text = read_text_safely(abs_path)
        title = extract_md_title(text, fallback=abs_path.name)

        mf = ManualFile(rel_path=rel_path, abs_path=abs_path, title=title, text=text)
        flat[rel_str] = mf

        cursor: TreeNode = tree
        parts = list(rel_path.parts)
        for part in parts[:-1]:
            if part not in cursor or not isinstance(cursor[part], dict):
                cursor[part] = {}
            cursor = cursor[part]  # type: ignore[assignment]
        cursor[parts[-1]] = mf

    return tree, flat


def render_generated_tree_text(tree: TreeNode) -> str:
    lines: List[str] = ["Manual Map (Tree)"]

    def walk(node: TreeNode, prefix: str = "") -> None:
        keys = sorted(node.keys(), key=numeric_sort_key)
        for i, name in enumerate(keys):
            last = i == (len(keys) - 1)
            branch = "└── " if last else "├── "
            child = node[name]

            if isinstance(child, dict):
                lines.append(f"{prefix}{branch}{name}/")
                next_prefix = prefix + ("    " if last else "│   ")
                walk(child, next_prefix)
            else:
                lines.append(f"{prefix}{branch}{name}")

    walk(tree)
    return "\n".join(lines)


def search_manual(
    flat: Dict[str, ManualFile],
    q: str,
    limit: int = 25,
) -> List[Tuple[str, int]]:
    q = q.strip().lower()
    if not q:
        return []

    results: List[Tuple[str, int]] = []
    for rel_str, mf in flat.items():
        title_l = mf.title.lower()
        text_l = mf.text.lower()

        score = 0
        if q in title_l:
            score += 5
        score += min(text_l.count(q), 20)

        if score > 0:
            results.append((rel_str, score))

    results.sort(
        key=lambda x: (-x[1], [numeric_sort_key(p) for p in Path(x[0]).parts])
    )
    return results[:limit]
