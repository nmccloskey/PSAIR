from __future__ import annotations

import importlib
import subprocess
import sys
from typing import Any, ClassVar

from psair.core.logger import logger


class NLPModel:
    """
    Singleton manager for spaCy pipelines and optional NLP resources.

    Core assumptions:
    - spaCy is installed
    - spaCy language models may or may not be installed
    - optional resources (benepar, nltk/cmudict) are loaded only when requested
    """

    _instance: ClassVar[NLPModel | None] = None
    _cmu_dict: dict[str, list[list[str]]] | None
    _nlp_models: dict[str, Any]
    _spacy: Any | None

    def __new__(cls) -> "NLPModel":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._nlp_models = {}
            cls._instance._cmu_dict = None
            cls._instance._spacy = None
        return cls._instance

    def _import_optional(self, package_name: str) -> Any:
        try:
            return importlib.import_module(package_name)
        except ImportError as exc:
            raise ImportError(
                f"Optional dependency '{package_name}' is not installed. "
                f"Install the appropriate PSAIR extra to use this feature."
            ) from exc

    def _get_spacy(self) -> Any:
        if self._spacy is None:
            self._spacy = self._import_optional("spacy")
        return self._spacy

    def ensure_spacy_model(self, model_name: str) -> None:
        spacy = self._get_spacy()
        try:
            spacy.load(model_name)
        except OSError:
            logger.warning(
                "%s is not installed. Attempting spaCy model download.",
                model_name,
            )
            subprocess.run(
                [sys.executable, "-m", "spacy", "download", model_name],
                check=True,
            )

    def load_nlp(
        self,
        model_name: str = "en_core_web_sm",
        *,
        require_benepar: bool = False,
        auto_download_model: bool = True,
    ) -> Any:
        spacy = self._get_spacy()
        if model_name not in self._nlp_models:
            if auto_download_model:
                self.ensure_spacy_model(model_name)
            self._nlp_models[model_name] = spacy.load(model_name)
            logger.info("Loaded spaCy model: %s", model_name)

        if require_benepar:
            self._ensure_benepar(self._nlp_models[model_name])

        return self._nlp_models[model_name]

    def _ensure_benepar(self, nlp: Any) -> None:
        if "benepar" in nlp.pipe_names:
            return

        benepar = self._import_optional("benepar")

        try:
            benepar.download("benepar_en3")
        except Exception as exc:
            logger.warning("Could not download benepar_en3 automatically: %s", exc)

        try:
            nlp.add_pipe("benepar", config={"model": "benepar_en3"})
            logger.info("Added benepar to spaCy pipeline.")
        except Exception as exc:
            raise RuntimeError(
                "benepar is installed, but could not be added to the spaCy pipeline."
            ) from exc

    def get_nlp(
        self,
        model_name: str = "en_core_web_sm",
        *,
        require_benepar: bool = False,
        auto_download_model: bool = True,
    ) -> Any:
        return self.load_nlp(
            model_name,
            require_benepar=require_benepar,
            auto_download_model=auto_download_model,
        )

    def get_tokenizer(self, model_name: str = "en_core_web_sm") -> Any:
        nlp = self.get_nlp(model_name=model_name, require_benepar=False)
        return nlp.tokenizer

    def get_cmu_dict(self) -> dict[str, list[list[str]]]:
        if self._cmu_dict is None:
            nltk = self._import_optional("nltk")
            from nltk.corpus import cmudict

            try:
                self._cmu_dict = cmudict.dict()
            except LookupError:
                logger.warning("CMUdict not found in NLTK data. Attempting download.")
                nltk.download("cmudict")
                self._cmu_dict = cmudict.dict()

        return self._cmu_dict


NLPmodel = NLPModel

__all__ = ["NLPModel", "NLPmodel"]
