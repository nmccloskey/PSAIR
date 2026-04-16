from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

from .args import (
    add_chars_parser,
    add_index_parser,
    add_outline_parser,
    add_pdf_parser,
    add_search_parser,
    add_tree_parser,
)
from ..manual.chars import check_manual_chars, normalize_exts as normalize_char_exts
from ..manual.index import build_manual_index, render_generated_tree_text, search_manual
from ..manual.outline import (
    build_manual_outline,
    ensure_manual_outline,
    normalize_exts as normalize_outline_exts,
)
from ..manual.pdf import build_manual_pdf, normalize_exts as normalize_pdf_exts


def _resolve_path(pathlike: str | Path) -> Path:
    return Path(pathlike).expanduser().resolve()


def _confirm(prompt: str) -> bool:
    while True:
        response = input(f"{prompt} [y/n]: ").strip().lower()
        if response in {"y", "yes"}:
            return True
        if response in {"n", "no"}:
            return False
        print("Please enter 'y' or 'n'.")


def _print_lines(lines: list[str]) -> None:
    for line in lines:
        print(line)


def _parse_csv_exts(raw: Optional[str], normalizer) -> set[str] | None:
    if raw is None:
        return None
    return normalizer(set(part.strip() for part in raw.split(",") if part.strip()))


def cmd_tree(args: argparse.Namespace) -> int:
    manual_dir = _resolve_path(args.manual_dir)

    if not manual_dir.exists():
        print(f"[psair] Manual directory not found: {manual_dir}", file=sys.stderr)
        return 1

    tree, flat = build_manual_index(manual_dir)

    if not flat:
        print(f"[psair] No markdown files found under: {manual_dir}", file=sys.stderr)
        return 1

    print(render_generated_tree_text(tree))
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    manual_dir = _resolve_path(args.manual_dir)

    if not manual_dir.exists():
        print(f"[psair] Manual directory not found: {manual_dir}", file=sys.stderr)
        return 1

    _, flat = build_manual_index(manual_dir)

    if not flat:
        print(f"[psair] No markdown files found under: {manual_dir}", file=sys.stderr)
        return 1

    results = search_manual(flat, args.query, limit=args.limit)

    if not results:
        print(f"[psair] No matches for: {args.query}")
        return 0

    for rel_str, score in results:
        mf = flat[rel_str]
        print(f"{score:>3}  {rel_str}  --  {mf.title}")

    return 0


def cmd_index(args: argparse.Namespace) -> int:
    manual_dir = _resolve_path(args.manual_dir)

    if not manual_dir.exists():
        print(f"[psair] Manual directory not found: {manual_dir}", file=sys.stderr)
        return 1

    tree, flat = build_manual_index(manual_dir)

    print(f"manual_dir: {manual_dir}")
    print(f"files_indexed: {len(flat)}")
    print(f"top_level_nodes: {len(tree)}")

    if args.show_files:
        for rel_str in flat:
            print(rel_str)

    return 0


def cmd_outline(args: argparse.Namespace) -> int:
    manual_dir = _resolve_path(args.manual_dir)
    output_path = _resolve_path(args.output) if args.output else None
    include_exts = _parse_csv_exts(args.exts, normalize_outline_exts)

    try:
        if args.if_missing_only:
            output = ensure_manual_outline(
                manual_dir,
                output_path=output_path,
                manual_title=args.title,
                manual_version=args.version,
                include_exts=include_exts,
                max_depth=args.max_depth,
                if_missing_only=True,
            )
        else:
            output = build_manual_outline(
                manual_dir,
                output_path=output_path,
                manual_title=args.title,
                manual_version=args.version,
                include_exts=include_exts,
                max_depth=args.max_depth,
            )
    except Exception as exc:
        print(f"[psair] ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote outline: {output}")
    return 0


def cmd_chars(args: argparse.Namespace) -> int:
    root = _resolve_path(args.root)
    exts = _parse_csv_exts(args.exts, normalize_char_exts)

    try:
        result = check_manual_chars(
            root,
            exts=exts,
            include_hidden=args.include_hidden,
            report_nonascii=args.report_nonascii,
            fail_on_nonascii=args.fail_on_nonascii,
            report_controls=args.report_controls,
            fail_on_controls=args.fail_on_controls,
            check_trailing=args.check_trailing,
            strip_trailing=args.strip_trailing,
            check_line_endings=args.check_line_endings,
            fix_line_endings=args.fix_line_endings,
            remove_control_chars=args.remove_control_chars,
            max_nonascii=args.max_nonascii,
            max_controls=args.max_controls,
            warnings_as_errors=args.warnings_as_errors,
        )
    except Exception as exc:
        print(f"[psair] ERROR: {exc}", file=sys.stderr)
        return 1

    if args.summary_only:
        _print_lines(result.summary_lines())
    else:
        _print_lines(result.report_lines(show_lines=not args.no_line_context))

    return 0 if result.ok else 1


def cmd_pdf(args: argparse.Namespace) -> int:
    manual_dir = _resolve_path(args.manual_dir)
    yaml_path = _resolve_path(args.yaml_path) if args.yaml_path else None
    output_path = _resolve_path(args.output_path) if args.output_path else None
    temp_md_path = _resolve_path(args.temp_md_path) if args.temp_md_path else None
    include_exts = _parse_csv_exts(args.exts, normalize_pdf_exts)

    if not manual_dir.exists():
        print(f"[psair] Manual directory not found: {manual_dir}", file=sys.stderr)
        return 1

    if not args.skip_outline:
        try:
            outline_output = ensure_manual_outline(
                manual_dir,
                output_path=None,
                manual_title=args.outline_title,
                manual_version=args.outline_version,
                include_exts=None,
                max_depth=args.outline_max_depth,
                if_missing_only=not args.rebuild_outline,
            )
            print(f"[psair] Outline ready: {outline_output}")
        except Exception as exc:
            print(f"[psair] ERROR during outline step: {exc}", file=sys.stderr)
            return 1

    if not args.skip_chars:
        try:
            char_result = check_manual_chars(
                manual_dir,
                exts=None,
                include_hidden=args.include_hidden,
                report_nonascii=args.report_nonascii,
                fail_on_nonascii=args.fail_on_nonascii,
                report_controls=args.report_controls,
                fail_on_controls=args.fail_on_controls,
                check_trailing=args.check_trailing,
                strip_trailing=args.strip_trailing,
                check_line_endings=args.check_line_endings,
                fix_line_endings=args.fix_line_endings,
                remove_control_chars=args.remove_control_chars,
                max_nonascii=args.max_nonascii,
                max_controls=args.max_controls,
                warnings_as_errors=args.warnings_as_errors,
            )
        except Exception as exc:
            print(f"[psair] ERROR during character check: {exc}", file=sys.stderr)
            return 1

        if args.summary_only:
            _print_lines(char_result.summary_lines())
        else:
            _print_lines(char_result.report_lines(show_lines=not args.no_line_context))

        has_issues = bool(char_result.warnings or char_result.errors)

        if has_issues and not args.force:
            if args.non_interactive:
                print(
                    "[psair] Character/content issues were found. "
                    "Aborting in non-interactive mode.",
                    file=sys.stderr,
                )
                return 1

            if not _confirm("Issues were found. Proceed to PDF compilation anyway?"):
                print("[psair] Aborted.")
                return 0

    try:
        output = build_manual_pdf(
            manual_dir,
            yaml_path=yaml_path,
            output_path=output_path,
            pandoc=args.pandoc,
            pdf_engine=args.pdf_engine,
            pagebreaks=not args.no_pagebreaks,
            strip_heading_numbers=not args.keep_heading_numbers,
            include_outline=args.include_outline,
            outline_name=args.outline_name,
            include_exts=include_exts,
            file_dividers=args.file_dividers,
            extra_pandoc_args=args.extra_pandoc_args,
            keep_temp_md=args.keep_temp_md,
            temp_md_path=temp_md_path,
            margin=args.margin,
            toc=not args.no_toc,
            toc_depth=args.toc_depth,
        )
    except Exception as exc:
        print(f"[psair] ERROR during PDF build: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote PDF: {output}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="psair",
        description="Utilities for indexing, viewing, validating, and compiling project manuals.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_tree_parser(subparsers, func=cmd_tree)
    add_search_parser(subparsers, func=cmd_search)
    add_index_parser(subparsers, func=cmd_index)
    add_outline_parser(subparsers, func=cmd_outline)
    add_chars_parser(subparsers, func=cmd_chars)
    add_pdf_parser(subparsers, func=cmd_pdf)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
