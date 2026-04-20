from __future__ import annotations

import shutil
import subprocess
import tempfile
import tomllib
import re
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path
from typing import Any, Iterable


MD_EXTS = {".md", ".markdown"}
_PLACEHOLDER_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_-]*)\}")
_LATEX_ARG_PLACEHOLDER_RE = re.compile(
    r"(\\[A-Za-z@]+(?:\[[^\]]*\])*)\{([A-Za-z_][A-Za-z0-9_-]*)\}"
)


def normalize_exts(exts: set[str] | None) -> set[str]:
    """
    Normalize extension strings to lowercase dotted forms.
    """
    if not exts:
        return set(MD_EXTS)

    normalized = {e.strip().lower() for e in exts if e and e.strip()}
    return {("." + e) if not e.startswith(".") else e for e in normalized}


def resolve_executable(name: str) -> str:
    """
    Resolve an executable from PATH or pypandoc, or raise a helpful error.
    """
    resolved = shutil.which(name)
    if resolved:
        return resolved

    if name == "pandoc":
        try:
            import pypandoc

            return pypandoc.get_pandoc_path()
        except Exception as exc:
            raise FileNotFoundError(
                "Required executable not found: pandoc. Install Pandoc and make "
                "pandoc.exe available on PATH, or install/download Pandoc through "
                "pypandoc. On Windows, common options are "
                "`winget install JohnMacFarlane.Pandoc`, "
                "`conda install -c conda-forge pandoc`, or "
                "`python -c \"import pypandoc; pypandoc.download_pandoc()\"`."
            ) from exc

    raise FileNotFoundError(f"Required executable not found on PATH: {name}")


def resolve_project_version(start: Path | None = None) -> str:
    """
    Resolve the project version, preferring the nearest pyproject.toml.

    This mirrors the installed-package lookup used by psair.__version__, but
    checks source-tree metadata first so local manual builds stay in sync with
    the repository being compiled.
    """
    for pyproject in _candidate_pyprojects(start):
        try:
            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        except Exception:
            continue

        project = data.get("project")
        if isinstance(project, dict) and isinstance(project.get("version"), str):
            return project["version"].strip()

    try:
        return package_version("psair")
    except PackageNotFoundError:  # pragma: no cover
        return "0.0.0"


def render_pandoc_metadata_text(
    yaml_path: Path,
    *,
    project_root: Path | None = None,
) -> str:
    """
    Render lightweight placeholders in a Pandoc metadata YAML file.

    Supported placeholders are based on top-level YAML metadata plus
    package-version helpers:

    - {package_version}: version from pyproject.toml, falling back to installed psair
    - {version}: top-level YAML version after placeholder expansion, or package version
    - {title}, {date}, etc.: top-level scalar YAML fields

    LaTeX command arguments like ``\\fancyhead[R]{date}`` keep their surrounding
    braces and become ``\\fancyhead[R]{Version 0.0.1}``.
    """
    raw = yaml_path.read_text(encoding="utf-8")
    metadata = _load_yaml_mapping(raw)
    package_ver = resolve_project_version(project_root or yaml_path)
    context = _build_metadata_context(metadata, package_version=package_ver)
    return _replace_metadata_placeholders(raw, context)


def prepare_pandoc_metadata_file(yaml_path: Path | None) -> tuple[Path | None, Path | None]:
    """
    Return the metadata file Pandoc should use and any temporary file to delete.
    """
    if yaml_path is None:
        return None, None

    rendered = render_pandoc_metadata_text(yaml_path)
    original = yaml_path.read_text(encoding="utf-8")
    if rendered == original:
        return yaml_path, None

    temp = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".yaml",
        prefix="psair_pandoc_metadata_",
        delete=False,
        encoding="utf-8",
        newline="\n",
    )
    try:
        temp.write(rendered)
        temp.flush()
    finally:
        temp.close()

    rendered_path = Path(temp.name)
    return rendered_path, rendered_path


def _candidate_pyprojects(start: Path | None) -> list[Path]:
    starts = []
    if start is not None:
        starts.append(Path(start).resolve())
    starts.extend([Path(__file__).resolve(), Path.cwd().resolve()])

    seen: set[Path] = set()
    candidates: list[Path] = []
    for item in starts:
        current = item if item.is_dir() else item.parent
        for parent in (current, *current.parents):
            candidate = parent / "pyproject.toml"
            if candidate in seen:
                continue
            seen.add(candidate)
            if candidate.exists():
                candidates.append(candidate)
    return candidates


def _load_yaml_mapping(raw: str) -> dict[str, Any]:
    try:
        import yaml

        loaded = yaml.safe_load(raw)
    except Exception:
        return _parse_simple_yaml_scalars(raw)

    return loaded if isinstance(loaded, dict) else {}


def _parse_simple_yaml_scalars(raw: str) -> dict[str, str]:
    metadata: dict[str, str] = {}
    scalar_re = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*?)\s*$")

    for line in raw.splitlines():
        match = scalar_re.match(line)
        if not match:
            continue

        value = match.group(2).strip()
        if not value or value.startswith(("[", "{")):
            continue
        if value[0:1] in {"'", '"'} and value[-1:] == value[0]:
            value = value[1:-1]
        metadata[match.group(1)] = value

    return metadata


def _build_metadata_context(
    metadata: dict[str, Any],
    *,
    package_version: str,
) -> dict[str, str]:
    context = {
        "package_version": package_version,
    }

    raw_version = metadata.get("version")
    if isinstance(raw_version, str) and raw_version.strip().lower() not in {"", "auto"}:
        context["version"] = _replace_metadata_placeholders(raw_version, context)
    else:
        context["version"] = package_version

    for _ in range(3):
        changed = False
        for key, value in metadata.items():
            if not isinstance(key, str) or not isinstance(value, str):
                continue
            rendered = _replace_metadata_placeholders(value, context)
            if context.get(key) != rendered:
                context[key] = rendered
                changed = True
        if not changed:
            break

    context.setdefault("date", f"Version {context['version']}")
    return context


def _replace_metadata_placeholders(text: str, context: dict[str, str]) -> str:
    def latex_repl(match: re.Match[str]) -> str:
        key = match.group(2)
        if key not in context:
            return match.group(0)
        return f"{match.group(1)}{{{context[key]}}}"

    def plain_repl(match: re.Match[str]) -> str:
        key = match.group(1)
        return context.get(key, match.group(0))

    text = _LATEX_ARG_PLACEHOLDER_RE.sub(latex_repl, text)
    return _PLACEHOLDER_RE.sub(plain_repl, text)


def iter_markdown_files(
    manual_dir: Path,
    *,
    include_exts: set[str] | None = None,
    include_outline: bool = False,
    outline_name: str = "00_outline.md",
) -> list[Path]:
    """
    Collect markdown files under manual_dir in stable lexical/path order.

    Hidden paths and __pycache__ are skipped.
    """
    manual_dir = manual_dir.resolve()
    include_exts = normalize_exts(include_exts)

    paths: list[Path] = []
    for path in manual_dir.rglob("*"):
        if not path.is_file():
            continue

        rel = path.relative_to(manual_dir)

        if any(part.startswith(".") for part in rel.parts):
            continue
        if "__pycache__" in rel.parts:
            continue
        if path.suffix.lower() not in include_exts:
            continue
        if not include_outline and path.name == outline_name:
            continue

        paths.append(path)

    paths.sort(key=lambda p: tuple(part.lower() for part in p.relative_to(manual_dir).parts))
    return paths


def strip_leading_heading_numbers(text: str) -> str:
    """
    Remove leading numeric prefixes from ATX headings.

    Examples
    --------
    '# 03 Overview' -> '# Overview'
    '## 03_02 Methods' -> '## Methods'
    """
    import re

    lines = []
    pattern = re.compile(r"^(#{1,6}\s+)\d+(?:[_-]\d+)*\s*[-:)]?\s*")
    for line in text.splitlines():
        lines.append(pattern.sub(r"\1", line))
    return "\n".join(lines)


def add_pagebreaks_between_sections(chunks: list[str]) -> str:
    """
    Join section chunks with LaTeX page breaks for Pandoc PDF compilation.
    """
    if not chunks:
        return ""

    pagebreak = "\n\n\\newpage\n\n"
    return pagebreak.join(chunks).strip() + "\n"


def assemble_markdown(
    files: Iterable[Path],
    *,
    manual_dir: Path,
    strip_heading_numbers: bool = True,
    pagebreaks: bool = True,
    file_dividers: bool = False,
) -> str:
    """
    Assemble multiple markdown files into one markdown document.
    """
    chunks: list[str] = []

    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")

        if strip_heading_numbers:
            text = strip_leading_heading_numbers(text)

        rel = path.relative_to(manual_dir).as_posix()

        if file_dividers:
            divider = [
                f"<!-- BEGIN FILE: {rel} -->",
                "",
                text.strip(),
                "",
                f"<!-- END FILE: {rel} -->",
            ]
            chunk = "\n".join(divider)
        else:
            chunk = text.strip()

        if chunk:
            chunks.append(chunk)

    if pagebreaks:
        return add_pagebreaks_between_sections(chunks)

    return "\n\n".join(chunks).strip() + ("\n" if chunks else "")


def build_pandoc_extra_args(
    *,
    margin: str | None = None,
    toc: bool = True,
    toc_depth: int | None = 3,
    extra_pandoc_args: list[str] | None = None,
) -> list[str]:
    """
    Build Pandoc CLI args for manual PDF compilation.

    Command-line flags are appended after any metadata file so they can
    override YAML defaults when appropriate.
    """
    args: list[str] = []

    if toc:
        args.append("--toc")
        if toc_depth is not None:
            args.extend(["--toc-depth", str(toc_depth)])

    if margin:
        args.extend(["-V", f"geometry:margin={margin}"])

    if extra_pandoc_args:
        args.extend(extra_pandoc_args)

    return args


def run_pandoc(
    *,
    markdown_path: Path,
    output_path: Path,
    pandoc: str = "pandoc",
    pdf_engine: str = "xelatex",
    yaml_path: Path | None = None,
    extra_args: list[str] | None = None,
) -> None:
    """
    Run pandoc to compile a markdown file to PDF.
    """
    pandoc_exec = resolve_executable(pandoc)

    cmd = [
        pandoc_exec,
        str(markdown_path),
        "-o",
        str(output_path),
        "--pdf-engine",
        pdf_engine,
    ]

    metadata_path, temp_metadata_path = prepare_pandoc_metadata_file(yaml_path)
    if metadata_path is not None:
        cmd.extend(["--metadata-file", str(metadata_path)])

    if extra_args:
        cmd.extend(extra_args)

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=False,
        )
    finally:
        if temp_metadata_path is not None and temp_metadata_path.exists():
            temp_metadata_path.unlink(missing_ok=True)

    stdout = proc.stdout.decode("utf-8", errors="replace")
    stderr = proc.stderr.decode("utf-8", errors="replace")

    if proc.returncode != 0:
        stderr = stderr.strip()
        stdout = stdout.strip()
        details = "\n".join(part for part in [stdout, stderr] if part)
        raise RuntimeError(
            f"Pandoc compilation failed with exit code {proc.returncode}.\n{details}"
        )


def build_manual_pdf(
    manual_dir: Path,
    *,
    yaml_path: Path | None = None,
    output_path: Path | None = None,
    pandoc: str = "pandoc",
    pdf_engine: str = "xelatex",
    pagebreaks: bool = True,
    strip_heading_numbers: bool = True,
    include_outline: bool = False,
    outline_name: str = "00_outline.md",
    include_exts: set[str] | None = None,
    file_dividers: bool = False,
    extra_pandoc_args: list[str] | None = None,
    keep_temp_md: bool = False,
    temp_md_path: Path | None = None,
    margin: str | None = None,
    toc: bool = True,
    toc_depth: int | None = None,
) -> Path:
    """
    Build a PDF manual from modular markdown files.

    Parameters
    ----------
    manual_dir
        Root manual directory to scan.
    yaml_path
        Optional Pandoc metadata YAML.
    output_path
        Destination PDF path. Defaults to <manual_dir>/<manual_dir_name>.pdf
    pandoc
        Pandoc executable name or path.
    pdf_engine
        Pandoc PDF engine, e.g. xelatex.
    pagebreaks
        Insert page breaks between assembled sections.
    strip_heading_numbers
        Remove numeric prefixes from headings before compilation.
    include_outline
        Whether to include 00_outline.md in the compiled PDF.
    outline_name
        Outline filename to optionally exclude/include.
    include_exts
        Markdown-like file extensions to include.
    file_dividers
        Insert HTML comments marking file boundaries in the assembled markdown.
    extra_pandoc_args
        Additional args passed through to pandoc.
    keep_temp_md
        Keep the assembled temporary markdown file.
    temp_md_path
        Explicit path for the assembled markdown file.
    margin
        Optional page margin override passed to Pandoc, e.g. '1in' or '2.2cm'.
    toc
        Whether to request an auto-generated table of contents.
    toc_depth
        Heading depth for the table of contents when toc is enabled.

    Returns
    -------
    Path
        Written PDF path.
    """
    manual_dir = Path(manual_dir).resolve()
    if not manual_dir.exists() or not manual_dir.is_dir():
        raise FileNotFoundError(
            f"manual_dir does not exist or is not a directory: {manual_dir}"
        )

    yaml_path = Path(yaml_path).resolve() if yaml_path else (manual_dir / "manual_pdf.yaml")
    if not yaml_path.exists():
        yaml_path = None

    if output_path is None:
        output_path = manual_dir.parent / "manual.pdf"
    else:
        output_path = Path(output_path).resolve()

    files = iter_markdown_files(
        manual_dir,
        include_exts=include_exts,
        include_outline=include_outline,
        outline_name=outline_name,
    )

    if not files:
        raise FileNotFoundError(f"No markdown files found under: {manual_dir}")

    assembled = assemble_markdown(
        files,
        manual_dir=manual_dir,
        strip_heading_numbers=strip_heading_numbers,
        pagebreaks=pagebreaks,
        file_dividers=file_dividers,
    )

    pandoc_args = build_pandoc_extra_args(
        margin=margin,
        toc=toc,
        toc_depth=toc_depth,
        extra_pandoc_args=extra_pandoc_args,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if temp_md_path is not None:
        temp_md_path = temp_md_path.resolve()
        temp_md_path.parent.mkdir(parents=True, exist_ok=True)
        temp_md_path.write_text(assembled, encoding="utf-8")
        md_path = temp_md_path
        cleanup = False
    else:
        tmp = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".md",
            prefix="psair_manual_",
            delete=False,
            encoding="utf-8",
        )
        try:
            tmp.write(assembled)
            tmp.flush()
        finally:
            tmp.close()
        md_path = Path(tmp.name)
        cleanup = not keep_temp_md

    try:
        run_pandoc(
            markdown_path=md_path,
            output_path=output_path,
            pandoc=pandoc,
            pdf_engine=pdf_engine,
            yaml_path=yaml_path,
            extra_args=pandoc_args,
        )
    finally:
        if cleanup and md_path.exists():
            md_path.unlink(missing_ok=True)

    return output_path
