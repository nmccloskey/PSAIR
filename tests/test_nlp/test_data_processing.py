from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from psair.nlp.data_processing import (
    calc_props,
    clean_text,
    get_most_common,
    get_text_from_cha,
    get_two_cha_versions,
    matrix_metrics,
    process_clan_text,
    scrub_raw_text,
)


def test_scrub_raw_text_normalizes_line_breaks_to_paragraph_markers() -> None:
    assert scrub_raw_text(" Alpha\r\nBeta\u2029\n\nGamma ") == "Alpha<p>Beta<p>Gamma"


def test_clean_text_normalizes_spacing_punctuation_hyphens_and_symbols() -> None:
    text = " Hello.World ! broken-\n word @#$ "

    assert clean_text(text) == "Hello. World! broken-word"


def test_get_text_from_cha_extracts_and_excludes_speakers(tmp_path: Path) -> None:
    cha = tmp_path / "sample.cha"
    cha.write_text(
        "*CHI:\thi there .\n"
        "*INV: skip this.\n"
        "*CHI: second line continues\n"
        " more words?\n",
        encoding="utf-8",
    )

    text = get_text_from_cha(cha, exclude_speakers=["INV"])

    assert text == "Hi there. Second line continues more words?"


def test_process_clan_text_target_and_phon_versions() -> None:
    text = "birbday [: birthday] &+um &-paraphasia"

    assert process_clan_text(text, version="target") == "birthday"
    assert process_clan_text(text, version="phon") == "birbday um paraphasia"


def test_get_two_cha_versions_cleans_target_and_phonological_text() -> None:
    cleaned, cleaned_phon = get_two_cha_versions("birbday [: birthday] !")

    assert cleaned == "birthday!"
    assert cleaned_phon == "birbday!"


def test_calc_props_returns_num_columns_as_proportions() -> None:
    props = calc_props({"num_words": 3, "other": 99, "num_turns": 1}, total=4)

    assert props == {"prop_words": 0.75, "prop_turns": 0.25}
    assert calc_props({"num_words": 3}, total=0) == {}


def test_get_most_common_returns_ranked_keys_and_counts() -> None:
    results = get_most_common(Counter({"alpha": 3, "beta": 2}), 3, "word")

    assert results == {
        "rank1_commonest_word": "alpha",
        "rank1_commonest_word_count": 3,
        "rank2_commonest_word": "beta",
        "rank2_commonest_word_count": 2,
    }


def test_matrix_metrics_computes_nonzero_statistics() -> None:
    metrics = matrix_metrics([[0, 2], [4, 0]], ["aa", "bbbb"], "distance")

    assert metrics["distance_min"] == 2.0
    assert metrics["distance_max"] == 4.0
    assert metrics["distance_mean"] == 3.0
    assert metrics["distance_median"] == 3.0
    assert metrics["distance_weighted_mean_dist"] == pytest.approx(20 / 6)
    assert metrics["distance_normalized_diversity"] == pytest.approx(1.0)


def test_matrix_metrics_returns_empty_defaults_when_all_values_are_zero() -> None:
    metrics = matrix_metrics([[0, 0], [0, 0]], ["a", "b"], "distance")

    assert metrics["distance_min"] is None
    assert metrics["distance_weighted_mean_dist"] is None
