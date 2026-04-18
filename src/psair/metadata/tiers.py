from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from psair.core.logger import logger


# -------------------------
# Tier
# -------------------------

@dataclass(frozen=True)
class Tier:
    """
    A single filename-parsing tier.

    Simplified config contract example:

      tiers:
        site: [AC, BU, TU]
        test: [Pre, Post, Maint]
        study_id: "(AC|BU|TU)\\d+"

    Interpretation:
      - list[str] -> literal values tier
      - str       -> regex tier
    """
    name: str
    kind: str                   # "values" | "regex" | "default"
    pattern: re.Pattern
    values: List[str]
    regex: Optional[str] = None

    def match(
        self,
        text: str,
        *,
        return_none: bool = False,
        must_match: bool = False,
    ) -> Optional[str]:
        m = self.pattern.search(text)
        if m:
            return m.group(0)

        if must_match:
            logger.warning(f"No match for tier '{self.name}' in text: {text!r}")

        return None if return_none else self.name


# -------------------------
# TierManager
# -------------------------

class TierManager:
    """
    Parse tier definitions from config into Tier objects and provide:
      - ordered tier matching
      - tier name access in config order

    Tiers are strictly for extracting metadata from input filenames.
    """

    def __init__(
        self,
        config: Dict[str, Any],
        *,
        name_transform: Optional[Callable[[str], str]] = None,
    ):
        self._name_transform = name_transform or (lambda s: s)

        self.tiers: Dict[str, Tier] = {}
        self.order: List[str] = []

        self._init_from_config(config)

    # ---- init ----

    def _init_from_config(self, config: Dict[str, Any]) -> None:
        raw_tiers = config.get("tiers", None)

        if not isinstance(raw_tiers, dict) or not raw_tiers:
            logger.warning(
                "Tier config missing/invalid — defaulting to single 'file_name' tier "
                "matching full filename stem before '.cha'."
            )
            self.tiers = self._default_tiers()
            self.order = list(self.tiers.keys())
            return

        self.tiers = self._read_tiers(raw_tiers)
        self.order = list(self.tiers.keys())

        logger.info(f"Initialized TierManager with {len(self.tiers)} tiers.")
        logger.info(f"Tier order: {self.order}")

    def _default_tiers(self) -> Dict[str, Tier]:
        name = "file_name"
        regex = r".*(?=\.cha)"
        pat = re.compile(regex)
        tier = Tier(
            name=name,
            kind="default",
            pattern=pat,
            values=[],
            regex=regex,
        )
        logger.info(f"Created default tier '{name}' with regex={regex!r}")
        return {name: tier}

    def _read_tiers(self, raw_tiers: Dict[str, Any]) -> Dict[str, Tier]:
        tiers: Dict[str, Tier] = {}

        for raw_name, spec in raw_tiers.items():
            name = self._name_transform(raw_name)

            if isinstance(spec, str):
                tier = self._build_regex_tier(name=name, regex=spec)
            elif isinstance(spec, list):
                tier = self._build_values_tier(name=name, values=spec)
            else:
                raise TypeError(
                    f"Tier '{raw_name}' must be either a regex string or a list[str] "
                    f"of literal values. Got: {type(spec).__name__}"
                )

            tiers[name] = tier

        if not tiers:
            logger.warning(
                "No tiers constructed (unexpected) — defaulting to 'file_name' tier."
            )
            return self._default_tiers()

        return tiers

    def _build_regex_tier(self, *, name: str, regex: str) -> Tier:
        if not regex.strip():
            raise ValueError(f"Tier '{name}': regex string must be non-empty.")

        try:
            pat = re.compile(regex)
        except re.error as e:
            raise ValueError(f"Tier '{name}': invalid regex {regex!r}: {e}") from e

        logger.info(f"Created tier '{name}' from regex={regex!r}")
        return Tier(
            name=name,
            kind="regex",
            pattern=pat,
            values=[],
            regex=regex,
        )

    def _build_values_tier(self, *, name: str, values: List[Any]) -> Tier:
        if not all(isinstance(v, str) for v in values):
            raise ValueError(f"Tier '{name}': values tier must be a list[str].")

        if not values:
            logger.warning(
                f"Tier '{name}' has empty values list — it will never match anything."
            )
            search_str = r"(?!x)x"
            pat = re.compile(search_str)
        else:
            escaped = [re.escape(v) for v in values]
            search_str = "(?:" + "|".join(escaped) + ")"
            pat = re.compile(search_str)

        logger.info(
            f"Created tier '{name}' from {len(values)} literal values; regex={search_str!r}"
        )
        return Tier(
            name=name,
            kind="values",
            pattern=pat,
            values=list(values),
            regex=None,
        )

    # ---- public API ----

    def get_tier_names(self) -> List[str]:
        return list(self.order)

    def match_tiers(
        self,
        text: str,
        *,
        return_none: bool = False,
        must_match: bool = False,
    ) -> Dict[str, Optional[str]]:
        return {
            tier_name: self.tiers[tier_name].match(
                text,
                return_none=return_none,
                must_match=must_match,
            )
            for tier_name in self.order
        }
