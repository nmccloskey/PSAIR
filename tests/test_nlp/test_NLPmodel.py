from __future__ import annotations

import subprocess
import sys
import types

import pytest

from psair.nlp.NLPmodel import NLPModel


@pytest.fixture(autouse=True)
def reset_singleton() -> None:
    NLPModel._instance = None
    yield
    NLPModel._instance = None


class FakeNlp:
    def __init__(self) -> None:
        self.pipe_names: list[str] = []
        self.added_pipes: list[tuple[str, dict[str, str]]] = []
        self.tokenizer = object()

    def add_pipe(self, name: str, config: dict[str, str]) -> None:
        self.pipe_names.append(name)
        self.added_pipes.append((name, config))


class FakeSpacy:
    def __init__(self, *, fail_load: bool = False) -> None:
        self.fail_load = fail_load
        self.load_calls: list[str] = []
        self.nlp = FakeNlp()

    def load(self, model_name: str) -> FakeNlp:
        self.load_calls.append(model_name)
        if self.fail_load:
            raise OSError(model_name)
        return self.nlp


def test_nlp_model_is_a_singleton() -> None:
    first = NLPModel()
    second = NLPModel()

    assert first is second
    assert first._nlp_models == {}


def test_import_optional_returns_module_or_raises_helpful_error() -> None:
    model = NLPModel()

    assert model._import_optional("math").sqrt(9) == 3

    with pytest.raises(ImportError, match="Optional dependency 'not_a_real_package_123'"):
        model._import_optional("not_a_real_package_123")


def test_get_spacy_imports_only_once(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_spacy = FakeSpacy()
    imports: list[str] = []

    def fake_import(name: str) -> object:
        imports.append(name)
        return fake_spacy

    model = NLPModel()
    monkeypatch.setattr("psair.nlp.NLPmodel.importlib.import_module", fake_import)

    assert model._get_spacy() is fake_spacy
    assert model._get_spacy() is fake_spacy
    assert imports == ["spacy"]


def test_ensure_spacy_model_downloads_missing_model(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_spacy = FakeSpacy(fail_load=True)
    model = NLPModel()
    model._spacy = fake_spacy
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], check: bool) -> subprocess.CompletedProcess:
        calls.append(cmd)
        assert check is True
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr("psair.nlp.NLPmodel.subprocess.run", fake_run)

    model.ensure_spacy_model("en_core_web_sm")

    assert fake_spacy.load_calls == ["en_core_web_sm"]
    assert calls == [[sys.executable, "-m", "spacy", "download", "en_core_web_sm"]]


def test_load_nlp_caches_loaded_models() -> None:
    fake_spacy = FakeSpacy()
    model = NLPModel()
    model._spacy = fake_spacy

    first = model.load_nlp("demo_model", auto_download_model=False)
    second = model.load_nlp("demo_model", auto_download_model=False)

    assert first is second
    assert fake_spacy.load_calls == ["demo_model"]


def test_load_nlp_can_add_benepar(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_spacy = FakeSpacy()
    fake_benepar = types.SimpleNamespace(download=lambda model_name: None)
    model = NLPModel()
    model._spacy = fake_spacy
    monkeypatch.setattr(model, "_import_optional", lambda package: fake_benepar)

    nlp = model.load_nlp(
        "demo_model",
        require_benepar=True,
        auto_download_model=False,
    )

    assert nlp.added_pipes == [("benepar", {"model": "benepar_en3"})]


def test_get_tokenizer_returns_loaded_pipeline_tokenizer() -> None:
    fake_spacy = FakeSpacy()
    model = NLPModel()
    model._spacy = fake_spacy

    assert model.get_tokenizer("demo_model") is fake_spacy.nlp.tokenizer


def test_get_cmu_dict_loads_and_caches_corpus(monkeypatch: pytest.MonkeyPatch) -> None:
    cmudict_module = types.ModuleType("nltk.corpus.cmudict")
    cmudict_module.dict = lambda: {"hello": [["HH", "AH0", "L", "OW1"]]}
    corpus_module = types.ModuleType("nltk.corpus")
    corpus_module.cmudict = cmudict_module
    fake_nltk = types.SimpleNamespace(download=lambda name: None)

    monkeypatch.setitem(sys.modules, "nltk", fake_nltk)
    monkeypatch.setitem(sys.modules, "nltk.corpus", corpus_module)
    monkeypatch.setitem(sys.modules, "nltk.corpus.cmudict", cmudict_module)

    model = NLPModel()
    monkeypatch.setattr(model, "_import_optional", lambda package: fake_nltk)

    first = model.get_cmu_dict()
    second = model.get_cmu_dict()

    assert first == {"hello": [["HH", "AH0", "L", "OW1"]]}
    assert first is second
