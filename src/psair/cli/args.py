from __future__ import annotations

import argparse


OUTLINE_EXTS_DEFAULT = ".md,.markdown"
CHAR_EXTS_DEFAULT = ".md,.markdown,.txt,.yaml,.yml,.toml,.json,.py"
PDF_EXTS_DEFAULT = ".md,.markdown"


def add_manual_dir_arg(
    parser: argparse.ArgumentParser,
    *,
    default: str = "docs/manual",
) -> None:
    parser.add_argument(
        "manual_dir",
        nargs="?",
        default=default,
        help="Path to the manual directory.",
    )


def add_root_arg(
    parser: argparse.ArgumentParser,
    *,
    default: str = "docs/manual",
) -> None:
    parser.add_argument(
        "root",
        nargs="?",
        default=default,
        help="Root directory to scan.",
    )


def add_exts_arg(
    parser: argparse.ArgumentParser,
    *,
    default: str,
    help_text: str,
) -> None:
    parser.add_argument(
        "--exts",
        default=default,
        help=help_text,
    )


def add_char_check_args(parser: argparse.ArgumentParser) -> None:
    scan_group = parser.add_argument_group("character scan")
    scan_group.add_argument(
        "--include-hidden",
        action="store_true",
        help="Include hidden files and directories.",
    )
    scan_group.add_argument(
        "--report-nonascii",
        action="store_true",
        help="Report non-ASCII characters as warnings.",
    )
    scan_group.add_argument(
        "--fail-on-nonascii",
        action="store_true",
        help="Treat non-ASCII characters as errors.",
    )
    scan_group.add_argument(
        "--report-controls",
        action="store_true",
        help="Report ASCII control characters as warnings.",
    )
    scan_group.add_argument(
        "--fail-on-controls",
        action="store_true",
        help="Treat ASCII control characters as errors.",
    )
    scan_group.add_argument(
        "--check-trailing",
        action="store_true",
        help="Check for trailing whitespace.",
    )
    scan_group.add_argument(
        "--check-line-endings",
        action="store_true",
        help="Check for CRLF line endings.",
    )
    scan_group.add_argument(
        "--max-nonascii",
        type=int,
        default=50,
        help="Maximum unique non-ASCII characters to list per line.",
    )
    scan_group.add_argument(
        "--max-controls",
        type=int,
        default=50,
        help="Maximum unique control characters to list per line.",
    )

    fix_group = parser.add_argument_group("character auto-fixes")
    fix_group.add_argument(
        "--strip-trailing",
        action="store_true",
        help="Strip trailing whitespace in place before scanning.",
    )
    fix_group.add_argument(
        "--fix-line-endings",
        choices=["lf", "crlf"],
        default=None,
        help="Normalize line endings before scanning.",
    )
    fix_group.add_argument(
        "--remove-control-chars",
        action="store_true",
        help=(
            "Remove ASCII control characters in place before scanning "
            "(except tab, newline, and carriage return)."
        ),
    )

    report_group = parser.add_argument_group("character reporting")
    report_group.add_argument(
        "--warnings-as-errors",
        action="store_true",
        help="Promote warnings to errors for exit status purposes.",
    )
    report_group.add_argument(
        "--no-line-context",
        action="store_true",
        help="Do not print offending line text in the report.",
    )
    report_group.add_argument(
        "--summary-only",
        action="store_true",
        help="Print only the summary.",
    )


def add_outline_build_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Optional output outline path.",
    )
    parser.add_argument(
        "--title",
        default="Instruction Manual",
        help="Manual title for the outline header.",
    )
    parser.add_argument(
        "--version",
        default="0.0.0",
        help="Manual version string for the outline header.",
    )
    add_exts_arg(
        parser,
        default=OUTLINE_EXTS_DEFAULT,
        help_text="Comma-separated list of file extensions to include.",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=None,
        help="Maximum directory depth to render in the tree.",
    )
    parser.add_argument(
        "--if-missing-only",
        action="store_true",
        help="Only build the outline if it does not already exist.",
    )


def add_pdf_compile_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-y",
        "--yaml",
        dest="yaml_path",
        default=None,
        help="Optional Pandoc metadata YAML file. Defaults to <manual_dir>/manual_pdf.yaml if present.",
    )
    parser.add_argument(
        "-o",
        "--output",
        dest="output_path",
        default=None,
        help="Optional output PDF path.",
    )
    parser.add_argument(
        "--pandoc",
        default="pandoc",
        help="Pandoc executable name or path.",
    )
    parser.add_argument(
        "--pdf-engine",
        default="xelatex",
        help="Pandoc PDF engine.",
    )
    parser.add_argument(
        "--no-pagebreaks",
        action="store_true",
        help="Do not insert page breaks between sections.",
    )
    parser.add_argument(
        "--keep-heading-numbers",
        action="store_true",
        help="Keep numeric prefixes in headings.",
    )
    parser.add_argument(
        "--include-outline",
        action="store_true",
        help="Include 00_outline.md in the compiled PDF.",
    )
    parser.add_argument(
        "--outline-name",
        default="00_outline.md",
        help="Outline filename to exclude/include.",
    )
    add_exts_arg(
        parser,
        default=PDF_EXTS_DEFAULT,
        help_text="Comma-separated list of file extensions to include in the PDF build.",
    )
    parser.add_argument(
        "--file-dividers",
        action="store_true",
        help="Insert HTML comments marking file boundaries.",
    )
    parser.add_argument(
        "--extra-pandoc-arg",
        dest="extra_pandoc_args",
        action="append",
        default=None,
        help="Extra argument to pass through to Pandoc. Repeat as needed.",
    )
    parser.add_argument(
        "--keep-temp-md",
        action="store_true",
        help="Keep the assembled markdown file.",
    )
    parser.add_argument(
        "--temp-md-path",
        default=None,
        help="Explicit path for the assembled markdown file.",
    )
    parser.add_argument(
        "--margin",
        default="1in",
        help="Page margin passed to Pandoc geometry, e.g. 1in or 0.8in.",
    )
    parser.add_argument(
        "--no-toc",
        action="store_true",
        help="Do not include an automated table of contents.",
    )
    parser.add_argument(
        "--toc-depth",
        type=int,
        default=3,
        help="Pandoc table-of-contents depth.",
    )


def add_pdf_preflight_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--skip-outline",
        action="store_true",
        help="Skip outline generation/checking before compilation.",
    )
    parser.add_argument(
        "--rebuild-outline",
        action="store_true",
        help="Always rebuild the outline before compilation.",
    )
    parser.add_argument(
        "--outline-title",
        default="Instruction Manual",
        help="Manual title for the outline header when outline is ensured.",
    )
    parser.add_argument(
        "--outline-version",
        default="0.0.0",
        help="Manual version for the outline header when outline is ensured.",
    )
    parser.add_argument(
        "--outline-max-depth",
        type=int,
        default=None,
        help="Maximum directory depth for the ensured outline tree.",
    )
    parser.add_argument(
        "--skip-chars",
        action="store_true",
        help="Skip character/content validation before compilation.",
    )
    add_char_check_args(parser)
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Do not prompt; abort if issues are found and --force is not set.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Proceed to PDF compilation even if issues are found.",
    )


def add_tree_parser(subparsers, *, func) -> argparse.ArgumentParser:
    parser = subparsers.add_parser("tree", help="Print the generated manual tree.")
    add_manual_dir_arg(parser)
    parser.set_defaults(func=func)
    return parser


def add_search_parser(subparsers, *, func) -> argparse.ArgumentParser:
    parser = subparsers.add_parser("search", help="Search manual titles and content.")
    parser.add_argument("query", help="Search query.")
    add_manual_dir_arg(parser)
    parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help="Maximum number of results to display.",
    )
    parser.set_defaults(func=func)
    return parser


def add_index_parser(subparsers, *, func) -> argparse.ArgumentParser:
    parser = subparsers.add_parser("index", help="Summarize the indexed manual.")
    add_manual_dir_arg(parser)
    parser.add_argument(
        "--show-files",
        action="store_true",
        help="Print indexed relative file paths.",
    )
    parser.set_defaults(func=func)
    return parser


def add_outline_parser(subparsers, *, func) -> argparse.ArgumentParser:
    parser = subparsers.add_parser("outline", help="Build or refresh the manual outline.")
    add_manual_dir_arg(parser)
    add_outline_build_args(parser)
    parser.set_defaults(func=func)
    return parser


def add_chars_parser(subparsers, *, func) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        "chars",
        help="Run character/content checks on documentation files.",
    )
    add_root_arg(parser)
    add_exts_arg(
        parser,
        default=CHAR_EXTS_DEFAULT,
        help_text="Comma-separated list of file extensions to include.",
    )
    add_char_check_args(parser)
    parser.set_defaults(func=func)
    return parser


def add_pdf_parser(subparsers, *, func) -> argparse.ArgumentParser:
    parser = subparsers.add_parser("pdf", help="Compile the manual PDF.")
    add_manual_dir_arg(parser)
    add_pdf_compile_args(parser)
    add_pdf_preflight_args(parser)
    parser.set_defaults(func=func)
    return parser
