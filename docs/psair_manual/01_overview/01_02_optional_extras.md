# Optional Extras and Build Splits

## Why PSAIR uses extras

PSAIR keeps its base installation deliberately small. The package includes
several areas of functionality, but not every user needs the same dependency
stack. Optional extras let users install only the dependencies needed for a
particular workflow.

This matters because the supported documentation tooling, Streamlit viewing,
ETL helpers, EDA stack, and NLP stack have very different dependency profiles.
For example, a project that only wants the manual CLI should not have to install
spaCy, scikit-learn, matplotlib, or Streamlit.

Install extras with standard `pip` syntax:

```bash
pip install "psair[docs]"
```

For editable development installs, use:

```bash
python -m pip install -e ".[docs]"
```

Multiple extras can be combined:

```bash
python -m pip install -e ".[docs,view,dev]"
```

## Base install

```bash
pip install psair
```

The base install has no required third-party dependencies. It installs the
`psair` package and the CLI entry points, but workflows that require optional
libraries will need the appropriate extra.

Use the base install when a project needs only dependency-light package
functionality or when another environment layer manages dependencies directly.

## Documentation extra

```bash
pip install "psair[docs]"
```

The `docs` extra is the recommended install target for the currently supported
PSAIR documentation toolchain. It includes dependencies used for manual export,
document handling, YAML configuration, and PDF support.

Use `docs` for:

- `psair tree`
- `psair index`
- `psair search`
- `psair outline`
- `psair chars`
- `psair pdf`
- Markdown manual workflows
- Pandoc-oriented PDF builds

Pandoc and a LaTeX PDF engine such as XeLaTeX are still external system tools.
They are not installed by `pip install "psair[docs]"`.

## Viewer extra

```bash
pip install "psair[view]"
```

The `view` extra supports the Streamlit manual viewer and browser-oriented
manual export helpers. It is useful for projects that want to embed PSAIR manual
browsing inside a Streamlit app.

Use `view` for:

- interactive manual browsing
- Streamlit-hosted documentation panels
- lightweight manual export from the viewer
- deployments such as Streamlit Community Cloud

The repository-level `requirements.txt` installs `.[view]` so the hosted viewer
can keep the base package dependency-free while still installing the packages
needed by the app.

## ETL extra

```bash
pip install "psair[etl]"
```

The `etl` extra installs dependencies used by the experimental ETL helpers,
including tabular data and YAML support.

Use this extra only when intentionally working with the alpha ETL modules. These
modules are not yet considered stable public APIs.

## EDA extra

```bash
pip install "psair[eda]"
```

The `eda` extra installs the exploratory data analysis stack, including
scientific computing, plotting, and spreadsheet dependencies.

Use this extra only for active development against the experimental EDA modules.
The EDA area is expected to change as PSAIR matures.

## NLP extra

```bash
pip install "psair[nlp]"
```

The `nlp` extra installs dependencies for the experimental NLP modules,
including spaCy, benepar, NLTK, document text extraction, and progress reporting.

Some NLP tools may also require model downloads or corpus downloads outside the
Python package installation. Treat this extra as a development target rather
than a stable user-facing interface.

## Web extra

```bash
pip install "psair[web]"
```

The `web` extra installs Streamlit and Markdown rendering dependencies for
web-facing PSAIR components. It overlaps with `view`, but is kept as a separate
build split for broader web-facing work as the package evolves.

Use `view` when the goal is the manual viewer specifically. Use `web` when
working on broader web application pieces.

## Development extra

```bash
python -m pip install -e ".[dev]"
```

The `dev` extra installs test tooling for contributors. At present, this means
`pytest`.

For documentation development, contributors will usually want:

```bash
python -m pip install -e ".[docs,view,dev]"
```

## Full extra

```bash
pip install "psair[full]"
```

The `full` extra installs the union of the main optional dependency groups. It
is intended for contributors who are developing across the package, not for
minimal downstream use.

Use `full` when:

- testing several package areas in one environment
- developing against experimental modules
- preparing broad integration checks
- investigating dependency interactions before a release

Avoid `full` for lightweight deployments unless the deployment truly needs the
whole experimental stack.

## Recommended install targets

For most users of the current alpha release:

```bash
pip install "psair[docs]"
```

For the manual viewer:

```bash
pip install "psair[view]"
```

For contributors working on documentation and tests:

```bash
python -m pip install -e ".[docs,view,dev]"
```

For broad experimental development:

```bash
python -m pip install -e ".[full,dev]"
```

## Release guidance

The optional extras are part of PSAIR's release hygiene. Before publishing a new
alpha release, check that each extra still matches the code it is meant to
support.

At minimum, verify:

- the base package imports without optional dependencies
- `psair --help` works after the intended documentation install
- the `docs` extra supports the manual CLI and PDF workflow
- the `view` extra supports the Streamlit manual viewer
- experimental extras do not accidentally become required for base imports
- the `full` extra includes the active optional dependency groups

Because PSAIR is still alpha, the extras may be reorganized in future releases.
When that happens, update this manual and the README together.
