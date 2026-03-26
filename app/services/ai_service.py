"""
Gemini API 연동 서비스
번역, 요약, 오늘의 핵심 이슈 생성, 키워드 툴팁 생성을 담당
"""

import os
import json
from typing import List, Dict
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Gemini 설정
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
model = genai.GenerativeModel(MODEL_NAME)


def _call_gemini(prompt: str) -> str:
    """Gemini API 호출 공통 함수"""
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"⚠️  Gemini API 오류: {e}")
        return ""


def translate_and_summarize(title: str, url: str = "") -> Dict[str, str]:
    """
    기사 제목을 한국어로 번역하고 1줄 요약 생성
    반환: {"title_ko": str, "summary_ko": str, "keywords": list}
    """
    prompt = f"""다음 기술 기사 제목을 한국어로 번역하고, 내용을 1줄로 요약해주세요.
또한 기술 전문 키워드(최대 4개)를 추출해주세요.

기사 제목: {title}
기사 URL: {url}

반드시 아래 JSON 형식으로만 응답하세요 (다른 설명 없이):
{{
  "title_ko": "번역된 제목",
  "summary_ko": "기사 내용 1줄 요약 (한국어, 50자 이내)",
  "keywords": ["키워드1", "키워드2", "키워드3"]
}}"""

    result = _call_gemini(prompt)

    try:
        # JSON 파싱
        # 마크다운 코드블록 제거
        result = result.replace("```json", "").replace("```", "").strip()
        data = json.loads(result)
        return {
            "title_ko": data.get("title_ko", title),
            "summary_ko": data.get("summary_ko", ""),
            "keywords": data.get("keywords", []),
        }
    except Exception:
        return {
            "title_ko": title,
            "summary_ko": "",
            "keywords": [],
        }


def generate_daily_summary(articles: List[Dict]) -> str:
    """
    상위 기사들을 바탕으로 오늘의 핵심 이슈 3~5줄 생성
    articles: [{"title_ko": str, "summary_ko": str, "source": str}, ...]
    """
    if not articles:
        return "오늘 수집된 기사가 없습니다."

    articles_text = "\n".join([
        f"- [{a.get('source', '')}] {a.get('title_ko') or a.get('title_original', '')}"
        for a in articles[:15]
    ])

    prompt = f"""오늘 기술 뉴스에서 수집된 인기 기사들입니다:

{articles_text}

위 기사들을 분석하여 오늘의 핵심 기술 트렌드를 3~5줄로 요약해주세요.
- 오늘 가장 주목받는 기술/이슈가 무엇인지
- 어떤 흐름이나 변화가 보이는지
- 독자가 바로 이해할 수 있도록 쉽게 작성

마크다운 없이 순수 텍스트로만 응답하세요. 각 문장은 줄바꿈으로 구분하세요."""

    result = _call_gemini(prompt)
    return result if result else "핵심 이슈를 생성하지 못했습니다."


def generate_keyword_tooltip(keyword: str) -> str:
    """
    기술 키워드에 대한 툴팁 설명 생성 (2~3줄)
    """
    prompt = f"""기술 키워드 "{keyword}"에 대해 비전공자도 이해할 수 있도록 2~3줄로 설명해주세요.
- 이 기술이 무엇인지
- 어떤 역할을 하는지
- (해당되면) 새로운 기술인지, 기존 개념을 발전시킨 것인지

마크다운 없이 순수 텍스트로 응답하세요."""

    result = _call_gemini(prompt)
    return result if result else f"{keyword}에 대한 설명을 불러오지 못했습니다."
