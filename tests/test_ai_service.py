"""
ai_service.py 핵심 순수 함수 테스트
"""

import json
import os
import tempfile
import pytest
from unittest.mock import patch


# ===== load_user_profile =====

def test_load_user_profile_missing_file():
    """프로필 파일 없으면 FileNotFoundError"""
    from app.services.ai_service import load_user_profile
    with patch("app.services.ai_service.os.path.normpath", return_value="/nonexistent/path/user_profile.json"):
        with pytest.raises(FileNotFoundError) as exc:
            load_user_profile()
    assert "user_profile.json" in str(exc.value)


def test_load_user_profile_valid_file():
    """정상 프로필 파일 로드"""
    profile = {
        "name": "테스터",
        "expertise": ["Python", "FastAPI"],
        "already_knows": ["RLHF"],
        "interests": ["AI reasoning"],
        "context": "테스트 컨텍스트",
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False)
        tmp_path = f.name

    try:
        with patch("app.services.ai_service.os.path.normpath", return_value=tmp_path):
            result = __import__("app.services.ai_service", fromlist=["load_user_profile"]).load_user_profile()
        assert result["name"] == "테스터"
        assert "Python" in result["expertise"]
    finally:
        os.unlink(tmp_path)


# ===== _build_profile_context =====

def test_build_profile_context_all_fields():
    """모든 필드 있을 때 컨텍스트 문자열 생성"""
    from app.services.ai_service import _build_profile_context
    profile = {
        "name": "ehson",
        "expertise": ["transformer", "LLM"],
        "already_knows": ["MoE"],
        "interests": ["inference"],
        "context": "AI engineer",
    }
    result = _build_profile_context(profile)
    assert "ehson" in result
    assert "transformer" in result
    assert "MoE" in result
    assert "inference" in result
    assert "AI engineer" in result


def test_build_profile_context_missing_fields():
    """필드 일부 없어도 KeyError 없이 동작"""
    from app.services.ai_service import _build_profile_context
    result = _build_profile_context({})
    assert result == ""


def test_build_profile_context_partial_fields():
    """name만 있는 경우"""
    from app.services.ai_service import _build_profile_context
    result = _build_profile_context({"name": "테스터"})
    assert "테스터" in result


# ===== translate_and_summarize (Gemini mock) =====

def test_translate_and_summarize_empty_gemini_response():
    """Gemini API가 빈 문자열 반환 시 원제목 그대로 반환"""
    from app.services.ai_service import translate_and_summarize
    with patch("app.services.ai_service._call_gemini", return_value=""):
        result = translate_and_summarize("Test Article Title")
    assert result["title_ko"] == "Test Article Title"
    assert result["summary_ko"] == ""
    assert result["keywords"] == []
    assert result["why_for_user"] is None


def test_translate_and_summarize_valid_response():
    """정상 JSON 응답 파싱"""
    from app.services.ai_service import translate_and_summarize
    mock_response = json.dumps({
        "title_ko": "테스트 기사 제목",
        "summary_ko": "요약 내용입니다.",
        "keywords": ["LLM", "RLHF"],
        "why_for_user": "당신에게 흥미로운 이유",
    }, ensure_ascii=False)
    with patch("app.services.ai_service._call_gemini", return_value=mock_response):
        result = translate_and_summarize("Test Article Title")
    assert result["title_ko"] == "테스트 기사 제목"
    assert result["summary_ko"] == "요약 내용입니다."
    assert "LLM" in result["keywords"]
    assert result["why_for_user"] == "당신에게 흥미로운 이유"


def test_translate_and_summarize_why_null_normalized():
    """why_for_user가 'null' 문자열이면 None으로 정규화"""
    from app.services.ai_service import translate_and_summarize
    mock_response = json.dumps({
        "title_ko": "제목",
        "summary_ko": "요약",
        "keywords": [],
        "why_for_user": "null",
    })
    with patch("app.services.ai_service._call_gemini", return_value=mock_response):
        result = translate_and_summarize("Title")
    assert result["why_for_user"] is None
