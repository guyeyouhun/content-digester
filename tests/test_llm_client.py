"""Tests for content_digester.lib.llm — LLMClient, DECOMPOSE_SYSTEM."""

import json
from unittest.mock import MagicMock, patch

import pytest

from content_digester.lib.llm import DECOMPOSE_SYSTEM, LLMClient
from content_digester.schemas.intermediate import KnowledgeGraph


# ── DECOMPOSE_SYSTEM prompt ─────────────────────────────────────────────────

def test_decompose_system_prompt_exists():
    """DECOMPOSE_SYSTEM \u662f\u4e00\u4e2a\u975e\u7a7a\u5b57\u7b26\u4e32."""
    assert isinstance(DECOMPOSE_SYSTEM, str)
    assert len(DECOMPOSE_SYSTEM) > 100


def test_decompose_system_prompt_has_keywords():
    """DECOMPOSE_SYSTEM \u5305\u542b\u5173\u952e\u7ed3\u6784\u63cf\u8ff0."""
    assert "entities" in DECOMPOSE_SYSTEM
    assert "relations" in DECOMPOSE_SYSTEM
    assert "knowledge" in DECOMPOSE_SYSTEM.lower()
    assert "type" in DECOMPOSE_SYSTEM


# ── LLMClient.parse_kg ─────────────────────────────────────────────────────


def _make_llm_with_response(content: str) -> LLMClient:
    """Helper: \u521b\u5efa\u4e00\u4e2a mock \u4e86 chat() \u8fd4\u56de content \u7684 LLMClient."""
    client = LLMClient()
    client.chat = MagicMock(return_value=content)
    return client


def test_decompose_empty_content_returns_empty_kg():
    """decompose \u5bf9\u7a7a\u5185\u5bb9\u8fd4\u56de\u7a7a KnowledgeGraph."""
    client = LLMClient()
    result = client.decompose("", "")
    assert isinstance(result, KnowledgeGraph)
    assert result.entities == []
    assert result.relations == []


def test_decompose_whitespace_only_returns_empty_kg():
    """decompose \u5bf9\u7a7a\u767d\u5185\u5bb9\u8fd4\u56de\u7a7a KnowledgeGraph."""
    client = LLMClient()
    result = client.decompose("   \n  ", "")
    assert isinstance(result, KnowledgeGraph)
    assert result.entities == []
    assert result.relations == []


def test_parse_kg_valid_json():
    """decompose \u6b63\u786e\u89e3\u6790\u5408\u6cd5 JSON \u54cd\u5e94."""
    mock_response = json.dumps({
        "entities": [
            {
                "name": "SQL Injection",
                "type": "concept",
                "summary": "A security vulnerability",
                "detail": "SQL injection allows attackers to manipulate database queries.",
                "tags": ["security", "database"],
                "evidence": "OWASP Top 10",
            },
            {
                "name": "Prepared Statements",
                "type": "method",
                "summary": "Defense against SQL injection",
                "detail": "Parameterized queries prevent injection attacks.",
                "tags": ["security", "defense"],
                "evidence": "Always use parameterized queries.",
            },
        ],
        "relations": [
            {
                "source": "Prepared Statements",
                "target": "SQL Injection",
                "type": "contradicts",
            },
        ],
    })

    client = _make_llm_with_response(mock_response)
    result = client.decompose("some content", "Title")

    assert len(result.entities) == 2
    assert result.entities[0].name == "SQL Injection"
    assert result.entities[0].type == "concept"
    assert result.entities[0].tags == ["security", "database"]
    assert result.entities[0].confidence == "EXTRACTED"  # evidence present
    assert result.entities[1].name == "Prepared Statements"
    assert result.entities[1].confidence == "EXTRACTED"

    assert len(result.relations) == 1
    assert result.relations[0].source == "Prepared Statements"
    assert result.relations[0].target == "SQL Injection"
    assert result.relations[0].type == "contradicts"


def test_parse_kg_json_with_markdown_fence():
    """decompose \u6b63\u786e\u89e3\u6790 markdown \u4ee3\u7801\u5757\u4e2d\u7684 JSON."""
    mock_response = '```json\n{"entities": [], "relations": []}\n```'
    client = _make_llm_with_response(mock_response)
    result = client.decompose("content")
    assert result.entities == []
    assert result.relations == []


def test_parse_kg_invalid_json_returns_empty():
    """decompose \u5bf9\u65e0\u6548 JSON \u8fd4\u56de\u7a7a KnowledgeGraph."""
    client = _make_llm_with_response("not valid json {{")
    result = client.decompose("content")
    assert result.entities == []
    assert result.relations == []


def test_parse_kg_chat_returns_none():
    """decompose \u5f53 chat() \u8fd4\u56de None \u65f6\u8fd4\u56de\u7a7a KnowledgeGraph."""
    client = _make_llm_with_response(None)  # mock chat returns None
    result = client.decompose("content")
    assert result.entities == []
    assert result.relations == []


def test_parse_kg_missing_fields_get_defaults():
    """decompose \u5bf9\u7f3a\u5931\u5b57\u6bb5\u7684\u5b9e\u4f53\u5e94\u7528\u9ed8\u8ba4\u503c."""
    mock_response = json.dumps({
        "entities": [{"name": "E1"}],
        "relations": [],
    })
    client = _make_llm_with_response(mock_response)
    result = client.decompose("content")

    e = result.entities[0]
    assert e.name == "E1"
    assert e.type == "concept"
    assert e.summary == ""
    assert e.detail == ""
    assert e.tags == []
    assert e.confidence == "INFERRED"  # no evidence \u2192 inferred


def test_parse_kg_entity_without_evidence_is_inferred():
    """decompose \u5bf9\u65e0 evidence \u7684\u5b9e\u4f53\u8bbe\u7f6e\u7f6e\u4fe1\u5ea6\u4e3a INFERRED."""
    mock_response = json.dumps({
        "entities": [{"name": "E1", "detail": "d"}],
        "relations": [],
    })
    client = _make_llm_with_response(mock_response)
    result = client.decompose("content")

    assert result.entities[0].confidence == "INFERRED"


def test_parse_kg_relation_default_type():
    """decompose \u5bf9\u7f3a\u5931 type \u7684\u5173\u7cfb\u4f7f\u7528\u9ed8\u8ba4\u503c 'references'."""
    mock_response = json.dumps({
        "entities": [{"name": "A"}, {"name": "B"}],
        "relations": [{"source": "A", "target": "B"}],
    })
    client = _make_llm_with_response(mock_response)
    result = client.decompose("content")

    assert result.relations[0].type == "references"


# ── LLMClient.configured ────────────────────────────────────────────────────

def test_client_not_configured_by_default():
    """\u65b0 LLMClient \u9ed8\u8ba4\u672a\u914d\u7f6e."""
    client = LLMClient()
    assert client.configured is False


def test_client_chat_returns_none_when_not_configured(monkeypatch):
    """chat() \u5728\u672a\u914d\u7f6e\u65f6\u8fd4\u56de None \u4e14\u4e0d\u53d1\u8d77\u8bf7\u6c42."""
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    client = LLMClient()
    result = client.chat("system", "user")
    assert result is None
