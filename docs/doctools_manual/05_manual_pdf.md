
# manual_pdf Module

## Overview

The `manual_pdf` module compiles modular IRIDIC manual sections into a **single PDF document**.

It performs the final stage of the IRIDIC manual build pipeline by:

1. Collecting Markdown manual files
2. Assembling them into a unified Markdown document
3. Invoking **Pandoc** to generate a PDF

This module allows manuals to remain **modular and repository-friendly** while still producing a polished compiled manual suitable for:

- distribution
- publication
- archival documentation

The module is designed to integrate with the IRIDIC CLI and with automated documentation workflows.

---

# Data Model

The module does not introduce persistent data structures like other manual modules.  
Instead it operates on:

- **filesystem paths**
- **lists of Markdown files**
- **assembled Markdown text chunks**

This lightweight design keeps the PDF compilation pipeline simple and composable.

---

# Core Functions

## build_manual_pdf

Primary entry point for PDF compilation.

```
build_manual_pdf(manual_dir)
```

### Purpose

Creates a compiled manual PDF from modular Markdown files.

### Parameters

| Parameter | Description |
|----------|-------------|
| `manual_dir` | Root manual directory |
| `yaml_path` | Optional Pandoc metadata YAML |
| `output_path` | Destination PDF file |
| `pandoc` | Pandoc executable |
| `pdf_engine` | Pandoc PDF engine |
| `pagebreaks` | Insert page breaks between sections |
| `strip_heading_numbers` | Remove numeric prefixes from headings |
| `include_outline` | Include `00_outline.md` in the PDF |
| `include_exts` | File extensions to include |
| `file_dividers` | Insert HTML comments marking file boundaries |
| `extra_pandoc_args` | Additional Pandoc CLI arguments |
| `keep_temp_md` | Preserve the assembled Markdown file |
| `temp_md_path` | Explicit path for assembled Markdown |
| `margin` | Page margin override |
| `toc` | Enable automatic table of contents |
| `toc_depth` | Maximum table-of-contents heading depth |

### Workflow

The function performs the following sequence:

1. Discover Markdown files
2. Assemble them into a unified Markdown document
3. Write the temporary Markdown file
4. Invoke Pandoc to generate the PDF
5. Remove temporary artifacts unless preservation is requested

Returns:

```
Path
```

representing the compiled PDF location.

---

# Supporting Utilities

## iter_markdown_files

Collects Markdown manual files from the manual directory.

Key behaviors:

- recursive directory scanning
- hidden path exclusion
- deterministic ordering
- optional exclusion of `00_outline.md`

Example discovered structure:

```
manual/
    01_intro.md
    02_installation.md
    03_workflow/
        03_01_overview.md
```

The files are returned in stable lexical order.

---

## assemble_markdown

Combines multiple Markdown files into a single document.

Example behavior:

```
Section 1 text

\newpage

Section 2 text
```

Optional features include:

- page breaks between sections
- removal of numeric heading prefixes
- file boundary comments

These transformations help produce cleaner final PDFs.

---

## strip_leading_heading_numbers

Removes numeric prefixes from Markdown headings.

Example:

```
# 03 Overview
```

becomes

```
# Overview
```

This allows numeric ordering in filenames without cluttering the compiled manual.

---

## add_pagebreaks_between_sections

Inserts LaTeX page breaks between assembled Markdown sections.

```
\newpage
```

Pandoc interprets these directives during PDF generation.

---

## build_pandoc_extra_args

Constructs Pandoc CLI arguments used during compilation.

Example generated arguments:

```
--toc
--toc-depth 3
-V geometry:margin=1in
```

These parameters can override YAML configuration values.

---

## run_pandoc

Executes the Pandoc command used to produce the final PDF.

Example command executed internally:

```
pandoc assembled.md -o manual.pdf --pdf-engine xelatex
```

The function captures output and raises a descriptive error if compilation fails.

---

## resolve_executable

Resolves the Pandoc executable from the system PATH.

If Pandoc is not found, the function raises a clear error message.

---

# CLI Integration

The module is exposed through the IRIDIC CLI command:

```
iridic pdf
```

Example usage:

```
iridic pdf manual
```

Optional arguments include:

```
--yaml manual_pdf.yaml
--output manual.pdf
--margin 0.8in
--toc-depth 3
--include-outline
--file-dividers
```

Internally, the CLI command invokes:

```
build_manual_pdf()
```

after optional preflight steps such as outline generation and character validation. fileciteturn3file0

---

# Role Within IRIDIC

The `manual_pdf` module is the **final build stage** of the IRIDIC documentation pipeline.

Typical workflow:

```
manual editing
        ↓
manual_chars validation
        ↓
manual_outline generation
        ↓
manual_pdf compilation
```

This layered design allows each stage to remain modular and reusable.

The compiled PDF serves as the **canonical distributable manual**.

---

# Design Principles

The module follows several design goals.

**Modular documentation**  
Manual sections remain independent Markdown files.

**Deterministic builds**  
Stable file ordering ensures reproducible manuals.

**Minimal transformation**  
Content is preserved as written except for optional formatting adjustments.

**External rendering engine**  
Pandoc performs the heavy lifting for PDF generation.

---

# Summary

`manual_pdf` compiles modular Markdown manuals into a single formatted PDF.

Core capabilities include:

- Markdown file discovery
- section assembly
- optional formatting transformations
- Pandoc-driven PDF compilation

This module completes the IRIDIC documentation pipeline by producing **publishable manuals from modular source files**.
