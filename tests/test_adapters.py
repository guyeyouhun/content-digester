"""Tests for content_digester.adapters — adapter registration and source_type."""

import pytest

from content_digester.adapters.article import ArticleAdapter
from content_digester.adapters.paper import PaperAdapter
from content_digester.adapters.repo import RepoAdapter
from content_digester.adapters.video import VideoAdapter
from content_digester.core.registry import (
    ADAPTER_REGISTRY,
    Adapter,
    get_adapter,
)


# ── Adapter source_type ─────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "adapter_cls,expected_type",
    [
        (ArticleAdapter, "article"),
        (RepoAdapter, "repo"),
        (PaperAdapter, "paper"),
        (VideoAdapter, "video"),
    ],
)
def test_adapter_source_type(adapter_cls, expected_type):
    """\u6bcf\u4e2a adapter \u7684 source_type property \u8fd4\u56de\u6b63\u786e\u503c."""
    instance = adapter_cls()
    assert instance.source_type == expected_type


# ── Adapter registration in ADAPTER_REGISTRY ────────────────────────────────

@pytest.mark.parametrize(
    "source_type,expected_cls",
    [
        ("article", ArticleAdapter),
        ("repo", RepoAdapter),
        ("paper", PaperAdapter),
        ("video", VideoAdapter),
    ],
)
def test_adapter_registered(source_type, expected_cls):
    """\u6bcf\u4e2a adapter \u5df2\u5728 ADAPTER_REGISTRY \u4e2d\u6ce8\u518c."""
    assert source_type in ADAPTER_REGISTRY
    assert ADAPTER_REGISTRY[source_type] is expected_cls


# ── All adapters are proper Adapter subclasses ──────────────────────────────

@pytest.mark.parametrize(
    "adapter_cls",
    [ArticleAdapter, RepoAdapter, PaperAdapter, VideoAdapter],
)
def test_adapter_is_subclass_of_base(adapter_cls):
    """\u6bcf\u4e2a adapter \u662f Adapter \u7684\u5b50\u7c7b."""
    assert issubclass(adapter_cls, Adapter)


# ── get_adapter returns correct types ───────────────────────────────────────

@pytest.mark.parametrize(
    "source_type,expected_cls",
    [
        ("article", ArticleAdapter),
        ("repo", RepoAdapter),
        ("paper", PaperAdapter),
        ("video", VideoAdapter),
    ],
)
def test_get_adapter_returns_correct_type(source_type, expected_cls):
    """get_adapter \u8fd4\u56de\u6b63\u786e\u7c7b\u578b\u7684\u5b9e\u4f8b."""
    adapter = get_adapter(source_type)
    assert isinstance(adapter, expected_cls)
    assert isinstance(adapter, Adapter)


# ── Adapter has required abstract methods ───────────────────────────────────

def test_adapter_has_run_method():
    """Adapter \u57fa\u7c7b\u63d0\u4f9b run() \u6a21\u677f\u65b9\u6cd5."""
    from content_digester.core.registry import Adapter
    assert hasattr(Adapter, "run")
    assert callable(Adapter.run)


def test_adapter_has_kg_to_entries_method():
    """Adapter \u57fa\u7c7b\u63d0\u4f9b _kg_to_entries \u8f85\u52a9\u65b9\u6cd5."""
    from content_digester.core.registry import Adapter
    assert hasattr(Adapter, "_kg_to_entries")
    assert callable(Adapter._kg_to_entries)
