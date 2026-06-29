"""Tests for content_digester.core.registry — detect, register_adapter, get_adapter."""

import pytest

from content_digester.core.registry import (
    ADAPTER_REGISTRY,
    Adapter,
    detect,
    get_adapter,
    register_adapter,
)
from content_digester.schemas.intermediate import KnowledgeEntry, KnowledgeGraph, ParsedContent, RawContent


# ── detect() tests ──────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "source,expected",
    [
        ("https://github.com/user/repo", "repo"),
        ("https://gitlab.com/user/repo", "repo"),
        ("https://bitbucket.org/user/repo", "repo"),
        ("git@github.com:user/repo.git", "repo"),
        ("https://arxiv.org/abs/2301.12345", "paper"),
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "video"),
        ("https://youtu.be/dQw4w9WgXcQ", "video"),
        ("https://example.com/blog/post", "article"),
        ("http://some-website.com/page", "article"),
        ("2301.12345", "paper"),
        ("dQw4w9WgXcQ", "video"),
    ],
)
def test_detect_known_patterns(source, expected):
    """detect() \u5e94\u6b63\u786e\u8bc6\u522b\u5404\u7c7b\u5df2\u77e5\u7d20\u6750\u6807\u8bc6\u7b26."""
    assert detect(source) == expected


def test_detect_empty_string():
    """detect() \u5bf9\u7a7a\u5b57\u7b26\u4e32\u8fd4\u56de None."""
    assert detect("") is None


def test_detect_random_string():
    """detect() \u5bf9\u65e0\u6cd5\u8bc6\u522b\u7684\u5b57\u7b26\u4e32\u8fd4\u56de None."""
    assert detect("just some random text") is None


def test_detect_arxiv_id_with_version():
    """detect() \u8bc6\u522b\u5e26\u6709 v1/v2 \u7248\u672c\u53f7\u7684 ArXiv ID."""
    assert detect("2301.12345v1") == "paper"


def test_detect_case_insensitive():
    """detect() \u5bf9\u57df\u540d\u5927\u5c0f\u5199\u4e0d\u654f\u611f."""
    assert detect("HTTPS://GITHUB.COM/user/repo") == "repo"
    assert detect("HTTPS://ARXIV.ORG/abs/2301.12345") == "paper"


# ── register_adapter tests ──────────────────────────────────────────────────

def test_register_adapter_decorator():
    """register_adapter \u88c5\u9970\u5668\u5c06\u7c7b\u6dfb\u52a0\u5230\u5168\u5c40\u6ce8\u518c\u8868."""

    @register_adapter("test-fake")
    class FakeAdapter:
        pass

    assert "test-fake" in ADAPTER_REGISTRY
    assert ADAPTER_REGISTRY["test-fake"] is FakeAdapter


def test_get_adapter_returns_instance():
    """get_adapter \u8fd4\u56de\u6ce8\u518c adapter \u7684\u65b0\u5b9e\u4f8b."""

    @register_adapter("test-instance")
    class InstanceAdapter:
        pass

    result = get_adapter("test-instance")
    assert isinstance(result, InstanceAdapter)


def test_get_adapter_unknown_raises():
    """get_adapter \u5bf9\u672a\u6ce8\u518c\u7c7b\u578b\u629b\u51fa ValueError."""
    with pytest.raises(ValueError, match="Unknown source type"):
        get_adapter("nonexistent-type")


# ── get_adapter: real adapters ──────────────────────────────────────────────

def test_get_adapter_article():
    """get_adapter('article') \u8fd4\u56de ArticleAdapter \u5b9e\u4f8b."""
    # ArticleAdapter is registered by module import in adapters/__init__.py
    # We import explicitly to trigger registration
    from content_digester.adapters.article import ArticleAdapter
    adapter = get_adapter("article")
    assert adapter.source_type == "article"


def test_get_adapter_repo():
    """get_adapter('repo') \u8fd4\u56de RepoAdapter \u5b9e\u4f8b."""
    from content_digester.adapters.repo import RepoAdapter
    adapter = get_adapter("repo")
    assert adapter.source_type == "repo"


def test_get_adapter_paper():
    """get_adapter('paper') \u8fd4\u56de PaperAdapter \u5b9e\u4f8b."""
    from content_digester.adapters.paper import PaperAdapter
    adapter = get_adapter("paper")
    assert adapter.source_type == "paper"


def test_get_adapter_video():
    """get_adapter('video') \u8fd4\u56de VideoAdapter \u5b9e\u4f8b."""
    from content_digester.adapters.video import VideoAdapter
    adapter = get_adapter("video")
    assert adapter.source_type == "video"
