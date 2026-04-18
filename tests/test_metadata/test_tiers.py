from __future__ import annotations

import pytest

from psair.metadata.tiers import TierManager


def test_default_tier_matches_cha_filename_stem() -> None:
    tm = TierManager({})

    assert tm.get_tier_names() == ["file_name"]
    assert tm.match_tiers("sample_001.cha") == {"file_name": "sample_001"}
    assert tm.match_tiers("sample_001.txt") == {"file_name": "file_name"}


def test_values_and_regex_tiers_match_in_config_order() -> None:
    tm = TierManager(
        {
            "tiers": {
                "site": ["AC", "BU"],
                "visit": r"(Pre|Post)\d?",
            }
        }
    )

    assert tm.get_tier_names() == ["site", "visit"]
    assert tm.match_tiers("study_AC_Pre2.xlsx") == {
        "site": "AC",
        "visit": "Pre2",
    }


def test_tier_match_can_return_none_for_missing_values() -> None:
    tm = TierManager({"tiers": {"site": ["AC"]}})

    assert tm.match_tiers("study_BU.xlsx") == {"site": "site"}
    assert tm.match_tiers("study_BU.xlsx", return_none=True) == {"site": None}


def test_name_transform_is_applied_to_tier_names() -> None:
    tm = TierManager(
        {"tiers": {"Study Site": ["AC"]}},
        name_transform=lambda value: value.lower().replace(" ", "_"),
    )

    assert tm.get_tier_names() == ["study_site"]
    assert tm.match_tiers("AC_001.cha") == {"study_site": "AC"}


def test_empty_values_tier_never_matches() -> None:
    tm = TierManager({"tiers": {"site": []}})

    assert tm.match_tiers("AC_001.cha", return_none=True) == {"site": None}


def test_invalid_tier_specs_raise_clear_errors() -> None:
    with pytest.raises(TypeError, match="must be either"):
        TierManager({"tiers": {"bad": {"nested": "value"}}})

    with pytest.raises(ValueError, match="list\\[str\\]"):
        TierManager({"tiers": {"bad": ["AC", 12]}})

    with pytest.raises(ValueError, match="non-empty"):
        TierManager({"tiers": {"bad": "   "}})

    with pytest.raises(ValueError, match="invalid regex"):
        TierManager({"tiers": {"bad": "("}})
