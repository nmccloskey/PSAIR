# PSAIR — Python Scaffolding for Analysis Itineraries in Research

**Status:** Alpha, active development  
**Current supported component:** documentation/manual tooling  
**Broader scope:** experimental infrastructure for ETL, EDA, NLP, and pipeline development

PSAIR is a backend utility package for research software repositories. Its long-term goal is to provide reusable scaffolding for documentation workflows, data handling, exploratory analysis, and pipeline-oriented tooling across projects such as DIAAD, ALASTR, CLATR, and related systems.

At present, **only the documentation toolchain is considered ready for general use**. Other package areas are included as part of the package's evolving architecture, but they should currently be treated as **experimental, incomplete, and subject to substantial change**.

## What is ready now

The currently supported portion of PSAIR focuses on repository documentation workflows, including tools for:

- modular manual preparation
- outline generation
- character and formatting checks
- PDF-oriented manual export
- manual viewing utilities for Streamlit-style apps

These tools are intended to support repositories that maintain structured Markdown manuals and want lightweight support for viewing and export.

## What is not ready yet

The broader `psair` namespace also contains modules related to:

- ETL
- exploratory data analysis
- NLP utilities
- pipeline scaffolding

These components are being actively developed and reorganized. They are not yet stable enough to treat as public APIs.

## Installation

For the currently supported documentation tooling:

```bash
pip install psair[docs]
```

If you are developing against the full experimental package layout:

```bash
pip install psair[full]
```

## Stability note

PSAIR is currently in alpha. Module structure, APIs, and dependency groupings may change significantly across early releases. Until the package reaches a more stable milestone, only the documentation tooling should be treated as a supported interface.

## Intended use

PSAIR is primarily intended for developers and research programmers who want reusable infrastructure for analysis-oriented repositories. It is not yet a polished end-user application.

## Related projects

PSAIR serves as shared backend scaffolding for downstream repositories. Project-specific applications and domain workflows should be handled in those downstream tools rather than in PSAIR itself.