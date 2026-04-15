from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


TEXT_EXTS = {
    ".md",
    ".markdown",
    ".txt",
    ".yaml",
    ".yml",
    ".toml",
    ".json",
    ".py",
}


@dataclass(frozen=True)
class Finding:
    """
    A single character/content hygiene finding.
    """
    path: Path
    line_no: int
    kind: str
    message: str
    line: str = ""


@dataclass
class CharScanResult:
    """
    Structured result for a manual character/content scan.
    """
    root: Path
    scanned_files: list[Path] = field(default_factory=list)
    fixed_files: list[Path] = field(default_factory=list)
    warnings: list[Finding] = field(default_factory=list)
    errors: list[Finding] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    @property
    def total_findings(self) -> int:
        return len(self.warnings) + len(self.errors)

    def summary_lines(self) -> list[str]:
        return [
            f"Root: {self.root}",
            f"Files scanned: {len(self.scanned_files)}",
            f"Files modified: {len(self.fixed_files)}",
            f"Warnings: {len(self.warnings)}",
            f"Errors: {len(self.errors)}",
        ]

    def report_lines(self, *, show_lines: bool = True) -> list[str]:
        lines = self.summary_lines()

        if self.warnings:
            lines.extend(["", "Warnings", "--------"])
            for finding in self.warnings:
                lines.append(format_finding(finding, show_line=show_lines))

        if self.errors:
            lines.extend(["", "Errors", "------"])
            for finding in self.errors:
                lines.append(format_finding(finding, show_line=show_lines))

        return lines


def normalize_exts(exts: set[str] | None) -> set[str]:
    """
    Normalize extensions to lowercase dotted forms.
    """
    if not exts:
        return set(TEXT_EXTS)

    normalized = {e.strip().lower() for e in exts if e and e.strip()}
    return {("." + e) if not e.startswith(".") else e for e in normalized}


def iter_target_files(
    root: Path,
    *,
    exts: set[str] | None = None,
    include_hidden: bool = False,
) -> list[Path]:
    """
    Collect target text-like files under root.
    """
    exts = normalize_exts(exts)
    root = root.resolve()

    paths: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue

        rel = path.relative_to(root)

        if not include_hidden and any(part.startswith(".") for part in rel.parts):
            continue
        if "__pycache__" in rel.parts:
            continue
        if path.suffix.lower() not in exts:
            continue

        paths.append(path)

    paths.sort(key=lambda p: tuple(part.lower() for part in p.relative_to(root).parts))
    return paths


def _iter_nonascii_chars(line: str) -> Iterable[str]:
    for ch in line:
        if ord(ch) > 127:
            yield ch


def _iter_control_chars(line: str) -> Iterable[str]:
    """
    Yield ASCII control characters that should not appear inside text lines.

    Allowed:
    - tab (\t)

    Newlines are already removed by splitlines(), so they do not appear here.
    """
    for ch in line:
        code = ord(ch)
        if code < 32 and ch != "\t":
            yield ch
        elif code == 127:
            yield ch


def _char_label(ch: str) -> str:
    code = ord(ch)
    names = {
        0: "NUL",
        1: "SOH",
        2: "STX",
        3: "ETX",
        4: "EOT",
        5: "ENQ",
        6: "ACK",
        7: "BEL",
        8: "BS",
        11: "VT",
        12: "FF",
        14: "SO",
        15: "SI",
        16: "DLE",
        17: "DC1",
        18: "DC2",
        19: "DC3",
        20: "DC4",
        21: "NAK",
        22: "SYN",
        23: "ETB",
        24: "CAN",
        25: "EM",
        26: "SUB",
        27: "ESC",
        28: "FS",
        29: "GS",
        30: "RS",
        31: "US",
        127: "DEL",
    }
    name = names.get(code, f"U+{code:04X}")
    return f"{repr(ch)} ({name}, 0x{code:02X})"


def scan_file(
    path: Path,
    *,
    report_nonascii: bool = False,
    fail_on_nonascii: bool = False,
    report_controls: bool = True,
    fail_on_controls: bool = True,
    check_trailing: bool = False,
    check_line_endings: bool = False,
    max_nonascii: int = 50,
    max_controls: int = 50,
) -> tuple[list[Finding], list[Finding]]:
    """
    Scan one file and return (warnings, errors).
    """
    warnings: list[Finding] = []
    errors: list[Finding] = []

    raw = path.read_bytes()

    if check_line_endings and b"\r\n" in raw:
        warnings.append(
            Finding(
                path=path,
                line_no=0,
                kind="line_endings",
                message="CRLF line endings detected.",
                line="",
            )
        )

    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    for idx, line in enumerate(lines, start=1):
        if check_trailing and line.rstrip(" \t") != line:
            warnings.append(
                Finding(
                    path=path,
                    line_no=idx,
                    kind="trailing_whitespace",
                    message="Trailing whitespace detected.",
                    line=line,
                )
            )

        if report_nonascii or fail_on_nonascii:
            seen_nonascii: list[str] = []
            for ch in _iter_nonascii_chars(line):
                if ch not in seen_nonascii:
                    seen_nonascii.append(ch)
                if len(seen_nonascii) >= max_nonascii:
                    break

            if seen_nonascii:
                chars_str = ", ".join(repr(ch) for ch in seen_nonascii)
                finding = Finding(
                    path=path,
                    line_no=idx,
                    kind="nonascii",
                    message=f"Non-ASCII characters detected: {chars_str}",
                    line=line,
                )
                if fail_on_nonascii:
                    errors.append(finding)
                else:
                    warnings.append(finding)

        if report_controls or fail_on_controls:
            seen_controls: list[str] = []
            for ch in _iter_control_chars(line):
                if ch not in seen_controls:
                    seen_controls.append(ch)
                if len(seen_controls) >= max_controls:
                    break

            if seen_controls:
                chars_str = ", ".join(_char_label(ch) for ch in seen_controls)
                finding = Finding(
                    path=path,
                    line_no=idx,
                    kind="control_char",
                    message=f"Control characters detected: {chars_str}",
                    line=line,
                )
                if fail_on_controls:
                    errors.append(finding)
                else:
                    warnings.append(finding)

    return warnings, errors


def apply_fixes(
    path: Path,
    *,
    strip_trailing: bool = False,
    fix_line_endings: str | None = None,
    remove_control_chars: bool = False,
) -> bool:
    """
    Apply safe text fixes in place.

    Returns
    -------
    bool
        True if the file was modified.
    """
    original = path.read_text(encoding="utf-8", errors="replace")
    text = original

    if strip_trailing:
        text = "\n".join(line.rstrip(" \t") for line in text.splitlines())
        if original.endswith("\n"):
            text += "\n"

    if fix_line_endings:
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        if fix_line_endings.lower() == "lf":
            text = normalized
        elif fix_line_endings.lower() == "crlf":
            text = normalized.replace("\n", "\r\n")
        else:
            raise ValueError("fix_line_endings must be 'lf', 'crlf', or None")

    if remove_control_chars:
        cleaned_chars = []
        for ch in text:
            code = ord(ch)
            if ch in ("\n", "\r", "\t"):
                cleaned_chars.append(ch)
            elif 0 <= code < 32 or code == 127:
                continue
            else:
                cleaned_chars.append(ch)
        text = "".join(cleaned_chars)

    if text != original:
        path.write_text(text, encoding="utf-8", newline="")
        return True

    return False


def format_finding(finding: Finding, *, show_line: bool = True) -> str:
    """
    Format a finding for terminal/report output.
    """
    loc = f"{finding.path}:{finding.line_no}" if finding.line_no else str(finding.path)
    head = f"[{finding.kind}] {loc} - {finding.message}"

    if show_line and finding.line:
        return f"{head}\n    {finding.line}"
    return head


def check_manual_chars(
    root: Path,
    *,
    exts: set[str] | None = None,
    include_hidden: bool = False,
    report_nonascii: bool = False,
    fail_on_nonascii: bool = False,
    report_controls: bool = True,
    fail_on_controls: bool = True,
    check_trailing: bool = False,
    strip_trailing: bool = False,
    check_line_endings: bool = False,
    fix_line_endings: str | None = None,
    remove_control_chars: bool = False,
    max_nonascii: int = 50,
    max_controls: int = 50,
    warnings_as_errors: bool = False,
) -> CharScanResult:
    """
    Scan manual/documentation files under root and optionally apply safe fixes.
    """
    root = root.resolve()
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"root does not exist or is not a directory: {root}")

    result = CharScanResult(root=root)
    targets = iter_target_files(root, exts=exts, include_hidden=include_hidden)

    for path in targets:
        result.scanned_files.append(path)

        modified = apply_fixes(
            path,
            strip_trailing=strip_trailing,
            fix_line_endings=fix_line_endings,
            remove_control_chars=remove_control_chars,
        )
        if modified:
            result.fixed_files.append(path)

        warnings, errors = scan_file(
            path,
            report_nonascii=report_nonascii,
            fail_on_nonascii=fail_on_nonascii,
            report_controls=report_controls,
            fail_on_controls=fail_on_controls,
            check_trailing=check_trailing,
            check_line_endings=check_line_endings,
            max_nonascii=max_nonascii,
            max_controls=max_controls,
        )

        if warnings_as_errors:
            result.errors.extend(warnings)
        else:
            result.warnings.extend(warnings)

        result.errors.extend(errors)

    return result


def run_manual_chars(
    root: Path,
    *,
    exts: set[str] | None = None,
    include_hidden: bool = False,
    report_nonascii: bool = False,
    fail_on_nonascii: bool = False,
    report_controls: bool = True,
    fail_on_controls: bool = True,
    check_trailing: bool = False,
    strip_trailing: bool = False,
    check_line_endings: bool = False,
    fix_line_endings: str | None = None,
    remove_control_chars: bool = False,
    max_nonascii: int = 50,
    max_controls: int = 50,
    warnings_as_errors: bool = False,
    show_lines: bool = True,
    summary_only: bool = False,
) -> int:
    result = check_manual_chars(
        root,
        exts=exts,
        include_hidden=include_hidden,
        report_nonascii=report_nonascii,
        fail_on_nonascii=fail_on_nonascii,
        report_controls=report_controls,
        fail_on_controls=fail_on_controls,
        check_trailing=check_trailing,
        strip_trailing=strip_trailing,
        check_line_endings=check_line_endings,
        fix_line_endings=fix_line_endings,
        remove_control_chars=remove_control_chars,
        max_nonascii=max_nonascii,
        max_controls=max_controls,
        warnings_as_errors=warnings_as_errors,
    )

    lines = (
        result.summary_lines()
        if summary_only
        else result.report_lines(show_lines=show_lines)
    )

    for line in lines:
        print(line)

    return 0 if result.ok else 1
