# Metadata Tiers

## Purpose

The metadata tier system extracts structured labels from text filenames. It is
intended for research repositories where filenames encode useful information
such as site, group, assessment time, task, study identifier, or corpus label.

The implementation lives in `psair.metadata.tiers` and centers on two objects:

- `Tier`: one compiled filename-matching rule
- `TierManager`: an ordered collection of tiers built from configuration

Tiers are deliberately simple. They search a filename or other text string and
return the first matching substring for each configured tier.

## Configuration shape

`TierManager` expects a dictionary with a `tiers` entry:

```yaml
tiers:
  site: [AC, BU, TU]
  test: [Pre, Post, Maint]
  study_id: "(AC|BU|TU)\\d+"
```

Each tier value can be either:

- a list of strings, interpreted as literal allowed values
- a string, interpreted as a regular expression

The order of tiers follows the order in the configuration dictionary. That
order is preserved by `get_tier_names()` and by the dictionaries returned from
`match_tiers()`.

## Literal value tiers

A list of strings creates a literal-value tier:

```yaml
tiers:
  site: [AC, BU, TU]
```

This tier searches for any of the listed values in the filename. Values are
escaped before the regex is compiled, so characters such as `+`, `.`, or `-`
are treated literally rather than as regex syntax.

Example:

```python
from psair.metadata.tiers import TierManager

tm = TierManager({"tiers": {"site": ["AC", "BU", "TU"]}})
tm.match_tiers("AC001_Pre_story.cha")
```

Result:

```python
{"site": "AC"}
```

## Regex tiers

A string creates a regex tier:

```yaml
tiers:
  study_id: "(AC|BU|TU)\\d+"
```

Regex tiers are useful when the metadata value has a pattern rather than a
fixed list of known values.

Example:

```python
tm = TierManager({"tiers": {"study_id": r"(AC|BU|TU)\d+"}})
tm.match_tiers("AC001_Pre_story.cha")
```

Result:

```python
{"study_id": "AC001"}
```

## Matching behavior

Use `match_tiers(text)` to extract all configured tiers from a filename or text
label:

```python
config = {
    "tiers": {
        "site": ["AC", "BU", "TU"],
        "test": ["Pre", "Post", "Maint"],
        "study_id": r"(AC|BU|TU)\d+",
    }
}

tm = TierManager(config)
tm.match_tiers("AC001_Pre_story.cha")
```

Result:

```python
{
    "site": "AC",
    "test": "Pre",
    "study_id": "AC001",
}
```

By default, an unmatched tier returns the tier name. This keeps a placeholder in
the result and makes missing matches visible in downstream tables:

```python
tm.match_tiers("AC001_story.cha")
```

Result:

```python
{
    "site": "AC",
    "test": "test",
    "study_id": "AC001",
}
```

Set `return_none=True` when missing values should be represented as `None`:

```python
tm.match_tiers("AC001_story.cha", return_none=True)
```

Result:

```python
{
    "site": "AC",
    "test": None,
    "study_id": "AC001",
}
```

Set `must_match=True` when missing tiers should be logged as warnings:

```python
tm.match_tiers("AC001_story.cha", return_none=True, must_match=True)
```

## Default tier

If the config is missing, does not contain a valid `tiers` dictionary, or the
tiers dictionary is empty, `TierManager` creates one default tier:

```python
{"file_name": "..."}
```

The default tier uses the regex `.*(?=\.cha)`, which extracts the full filename
stem before `.cha`.

For example:

```python
tm = TierManager({})
tm.match_tiers("AC001_Pre_story.cha")
```

Result:

```python
{"file_name": "AC001_Pre_story"}
```

## Name transforms

`TierManager` accepts an optional `name_transform` callable. This can normalize
tier names as they are read from configuration:

```python
tm = TierManager(
    {"tiers": {"Study ID": r"(AC|BU|TU)\d+"}},
    name_transform=lambda name: name.lower().replace(" ", "_"),
)
```

Resulting tier name:

```python
"study_id"
```

## Validation

Tier construction validates the config before matching:

- regex tiers must be non-empty valid regular expressions
- value tiers must be lists containing only strings
- empty value lists are allowed, but they log a warning and never match
- unsupported tier specifications raise `TypeError`

This validation happens when `TierManager` is constructed, so configuration
errors are found early.

## Practical guidance

Use literal value tiers for controlled labels that should match exactly, such
as known sites or assessment names. Use regex tiers for identifiers, dates, or
compound labels whose valid values are easier to describe with a pattern.

Keep tier labels distinct enough that accidental substring matches are unlikely.
For example, if one tier has values `["Pre", "Post"]`, filenames such as
`"Preview_AC001.cha"` may match `Pre` unless the tier is expressed with a more
specific regex.
