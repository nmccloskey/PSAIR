# NLP Preprocessing

## Purpose

The NLP preprocessing module reads text-oriented input files, normalizes text,
creates analysis-friendly text versions, and stores document-level or
sentence-level records through PSAIR's pipeline/output machinery.

The implementation is split across:

- `psair.nlp.preprocessing`, which orchestrates reading and preprocessing
- `psair.nlp.data_processing`, which contains text cleaning and helper metrics
- `psair.nlp.NLPmodel`, which loads the shared spaCy pipeline

This module is alpha-ready for projects already using PSAIR's pipeline shape,
but its integration points with ETL/output classes may still change.

## Supported input formats

`preprocess_text(PM)` discovers files under the configured input directory with
these extensions:

- `.cha`
- `.txt`
- `.docx`
- `.csv`
- `.xlsx`

Plain text and Word documents are treated as one document per file. CHAT files
are read as one document per file after speaker filtering. CSV and Excel files
are treated as tabular text sources where each row with a non-null `text` value
becomes a sample.

## Raw text readers

The reader functions handle format-specific extraction before NLP processing:

- `read_text_file()` reads UTF-8 text with replacement for invalid characters
- `read_docx_file()` extracts text with `docx2txt`
- `read_chat_file()` extracts utterances from CHAT/CLAN `.cha` files
- `read_spreadsheet()` reads `.csv` or `.xlsx` files with pandas

Raw `.txt` and `.docx` content is passed through `scrub_raw_text()`, which:

- normalizes line endings
- converts Unicode paragraph and line separators to newlines
- collapses one or more newlines into `<p>`
- trims leading and trailing whitespace

The `<p>` marker preserves paragraph breaks in an export-friendly text form.

## CHAT and CLAN handling

CHAT files are processed with `get_text_from_cha()`. The reader:

- merges raw lines into a single string for utterance matching
- extracts utterances from speaker-prefixed lines like `*PAR: ...`
- excludes configured speakers, defaulting to `["INV"]`
- normalizes spaces before final punctuation
- joins included utterances into one document string

For `.cha` samples, PSAIR creates two cleaned versions:

- `cleaned`: a target form that uses CLAN correction annotations such as
  `birbday [: birthday]`
- `cleaned_phon`: a phonological form that keeps the original token before the
  correction annotation

This behavior is implemented by `process_clan_text()` and
`get_two_cha_versions()`.

## Text cleaning

`clean_text()` applies lightweight normalization:

- collapses repeated whitespace
- inserts missing spaces after `.`, `!`, and `?` when followed by a letter
- removes spaces before sentence-final punctuation
- rejoins split hyphenated words
- normalizes a small set of mojibake quote characters
- removes characters outside word characters, whitespace, common punctuation,
  semicolons, question/exclamation marks, and hyphens

The goal is not to create a linguistically perfect representation. It creates a
consistent cleaned string suitable for downstream feature extraction and
exports.

## Semantic text

The preprocessing workflow also creates a `semantic` text representation using
spaCy:

```python
" ".join(
    token.lemma_
    for token in doc
    if token.is_alpha and not token.is_stop
)
```

This keeps alphabetic, non-stopword tokens and stores their lemmas. It is useful
for analyses that need a compact content-word representation of each document
or sentence.

## Document and sentence outputs

`process_sample_data(PM, sample_data)` expects each sample to include:

- `doc_id`
- `doc_label`
- `text`
- any tier metadata returned by `TierManager.match_tiers()`

It initializes preprocessing result tables from
`PM.sections["preprocessing"].init_results_dict()`, loads the shared spaCy
pipeline through `NLPModel`, and processes the sample.

When `PM.sentence_level` is true, each spaCy sentence becomes a sentence-level
record. The module produces:

- `sample_data_doc`: document metadata without the raw text
- `sample_text_doc`: raw, cleaned, semantic, and optional `cleaned_phon` text
- `sample_data_sent`: sentence metadata
- `sample_text_sent`: raw, cleaned, semantic, and optional `cleaned_phon`
  sentence text

When `PM.sentence_level` is false, only document-level records are populated.

## Spreadsheet inputs

Spreadsheet files must contain a `text` column. Every row with non-null text is
converted into a sample.

Other columns are treated as row-level metadata. The preprocessing code builds a
compound `doc_label` from the filename, the non-text column values, and the row
index, then assigns sequential document IDs.

This makes spreadsheet rows behave similarly to individual text files while
preserving source-row context.

## End-to-end workflow

`preprocess_text(PM)` performs the full preprocessing pass:

1. Creates an `OutputManager`.
2. Validates that the configured input directory exists.
3. Creates raw preprocessing tables.
4. Recursively discovers supported input files.
5. Converts each file or spreadsheet row into one or more samples.
6. Processes each sample into document-level and optional sentence-level text.
7. Updates output tables.
8. Exports preprocessing tables to Excel.
9. Returns the assigned document IDs.

## Dependencies

Use the NLP extras that match the workflow:

```bash
pip install "psair[nlp,nlp-process]"
```

Use `nlp-full` when preprocessing also needs parsing or phonology-oriented
resources:

```bash
pip install "psair[nlp-full]"
```

The spaCy language model, benepar model, and NLTK corpora are external model or
data resources. PSAIR can attempt some downloads at runtime, but production or
locked-down environments should provision them ahead of time.
