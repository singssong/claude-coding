"""
Gemini API 연동 서비스
번역, 요약, 내러티브 브리핑, 키워드 툴팁 생성을 담당
"""

import os
import json
from typing import List, Dict
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Gemini 설정
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
model = genai.GenerativeModel(MODEL_NAME)


def _call_gemini(prompt: str) -> str:
    """Gemini API 호출 공통 함수"""
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"[Gemini API ERROR] {str(e)[:200]}")
        return ""


def load_user_profile() -> Dict:
    """
    사용자 프로필 로드 (호출마다 파일에서 읽음 — 캐시 없음)
    파일이 없으면 FileNotFoundError 발생
    """
    profile_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "config", "user_profile.json")
    )
    try:
        with open(profile_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"사용자 프로필 파일을 찾을 수 없습니다: {profile_path}\n"
            "app/config/user_profile.json 파일을 생성해주세요."
        )


def _build_profile_context(profile: Dict) -> str:
    """
    프로필 딕셔너리를 프롬프트 삽입용 컨텍스트 문자열로 변환
    누락된 필드는 빈 값으로 처리 (KeyError 방지)
    """
    parts = []
    name = profile.get("name", "")
    expertise = profile.get("expertise", [])
    already_knows = profile.get("already_knows", [])
    interests = profile.get("interests", [])
    context = profile.get("context", "")

    if name:
        parts.append(f"독자: {name}")
    if expertise:
        parts.append(f"전문 지식: {', '.join(expertise)}")
    if already_knows:
        parts.append(f"이미 아는 것: {', '.join(already_knows)}")
    if interests:
        parts.append(f"관심 분야: {', '.join(interests)}")
    if context:
        parts.append(f"배경: {context}")

    return "\n".join(parts)


def _try_load_profile() -> Dict:
    """프로필 로드 시도. 실패하면 빈 딕셔너리 반환 (프로필 없이도 동작)"""
    try:
        return load_user_profile()
    except Exception:
        return {}


def translate_and_summarize(title: str, url: str = "", content: str = "") -> Dict[str, str]:
    """
    기사 제목 + 본문을 바탕으로 한국어 번역, 요약, 키워드 추출, why_for_user 생성
    반환: {"title_ko": str, "summary_ko": str, "keywords": list, "why_for_user": str|None}
    """
    profile = _try_load_profile()
    profile_ctx = _build_profile_context(profile)

    profile_section = f"\n[독자 프로필]\n{profile_ctx}\n" if profile_ctx else ""
    why_instruction = (
        '- "당신에게" (1-2줄, 독자의 기존 지식과 연결하여 이 기사가 왜 흥미로운지. '
        '독자가 이미 아는 개념과 어떻게 연결/충돌/확장되는지 구체적으로 설명):'
        if profile_ctx else ""
    )

    if content:
        prompt = f"""{profile_section}다음 기술 기사를 분석해주세요.

기사 제목: {title}
기사 본문 (일부):
{content[:2500]}

아래 JSON 형식으로만 응답하세요 (다른 설명 없이):
{{
  "title_ko": "제목을 한국어로 번역 (없으면 한국어 제목 그대로)",
  "summary_ko": "기사 핵심 내용 요약 (한국어, 2~3문장, 100자 이내)",
  "keywords": ["핵심 기술 키워드1", "키워드2", "키워드3", "키워드4"],
  "why_for_user": "독자의 기존 지식과 연결하여 이 기사가 왜 흥미로운지 (1-2줄, 한국어). 프로필 없으면 null"
}}"""
    else:
        prompt = f"""{profile_section}다음 기술 기사 제목을 분석해주세요. (본문 수집 불가)

기사 제목: {title}

아래 JSON 형식으로만 응답하세요 (다른 설명 없이):
{{
  "title_ko": "제목을 한국어로 번역",
  "summary_ko": "제목 기반 예상 내용 요약 (한국어, 50자 이내)",
  "keywords": ["키워드1", "키워드2", "키워드3"],
  "why_for_user": "독자의 기존 지식과 연결하여 이 기사가 왜 흥미로운지 (1-2줄, 한국어). 프로필 없으면 null"
}}"""

    result = _call_gemini(prompt)

    try:
        result = result.replace("```json", "").replace("```", "").strip()
        data = json.loads(result)
        why = data.get("why_for_user")
        # 빈 문자열은 None으로 정규화 (idempotency 체크가 NULL OR ''로 되어 있어도 일관성 유지)
        if why is not None and str(why).strip() in ("", "null"):
            why = None
        return {
            "title_ko": data.get("title_ko", title),
            "summary_ko": data.get("summary_ko", ""),
            "keywords": data.get("keywords", []),
            "why_for_user": why,
        }
    except Exception:
        return {
            "title_ko": title,
            "summary_ko": "",
            "keywords": [],
            "why_for_user": None,
        }


def batch_translate_titles(articles: List[Dict]) -> List[str]:
    """
    여러 기사 제목을 한 번의 API 호출로 일괄 번역
    articles: [{"id": int, "title_original": str}, ...]
    반환: id 순서대로 번역된 제목 리스트
    """
    if not articles:
        return []

    titles_text = "\n".join([
        f"{i+1}. {a['title_original']}"
        for i, a in enumerate(articles)
    ])

    prompt = f"""다음 기술 기사 제목들을 한국어로 번역해주세요.
번호 순서대로, 번역된 제목만 한 줄씩 출력하세요. 다른 설명은 절대 추가하지 마세요.

{titles_text}"""

    result = _call_gemini(prompt)
    if not result:
        return [a["title_original"] for a in articles]

    lines = [l.strip() for l in result.strip().splitlines() if l.strip()]
    parsed = []
    for line in lines:
        import re
        cleaned = re.sub(r"^\d+\.\s*", "", line)
        if cleaned:
            parsed.append(cleaned)

    while len(parsed) < len(articles):
        parsed.append(articles[len(parsed)]["title_original"])

    return parsed[:len(articles)]


def generate_narrative_briefing(articles: List[Dict]) -> str:
    """
    상위 기사들을 바탕으로 오늘의 내러티브 브리핑 생성 (프로필 기반, 120단어 이내)
    articles: [{"title_ko": str, "summary_ko": str, "source": str}, ...]
    형식:
      오늘의 흐름: [2-3문장 내러티브]
      당신이 이미 아는 것: [1문장 연결]
      특히 주목할 기사: [1-2개 기사 언급]
    """
    if not articles:
        return "오늘 수집된 기사가 없습니다."

    profile = _try_load_profile()
    profile_ctx = _build_profile_context(profile)
    profile_section = f"\n[독자 프로필]\n{profile_ctx}\n" if profile_ctx else ""

    articles_text = "\n".join([
        f"- [{a.get('source', '')}] {a.get('title_ko') or a.get('title_original', '')}"
        for a in articles[:15]
    ])

    prompt = f"""{profile_section}오늘 기술 뉴스에서 수집된 인기 기사들입니다:

{articles_text}

위 기사들을 분석하여 독자 프로필에 맞는 오늘의 브리핑을 작성해주세요.
총 120단어 이내, 아래 형식으로 작성하세요 (마크다운 없이 순수 텍스트):

오늘의 흐름: [오늘 기술 뉴스의 주요 테마를 2-3문장으로 서술. 독자의 전문 지식 수준을 가정하고 작성]

당신이 이미 아는 것: [오늘의 흐름과 독자의 기존 지식이 어떻게 연결되는지 1문장]

특히 주목할 기사: [가장 흥미로운 기사 1-2개를 구체적으로 언급하고 이유 설명]"""

    result = _call_gemini(prompt)
    return result if result else "브리핑을 생성하지 못했습니다."


def generate_keyword_tooltip(keyword: str) -> str:
    """
    기술 키워드에 대한 툴팁 설명 생성 (프로필 기반 깊이 조정)
    """
    profile = _try_load_profile()
    profile_ctx = _build_profile_context(profile)

    if profile_ctx:
        already_knows = profile.get("already_knows", [])
        # 독자가 이미 아는 키워드면 더 심층적인 설명
        depth_hint = (
            "독자는 이 분야에 전문 지식이 있습니다. 기초 설명 대신 심층적인 메커니즘, "
            "최근 동향, 기존 지식과의 연결점을 중심으로 설명해주세요."
            if any(k.lower() in keyword.lower() for k in already_knows)
            else "독자는 ML/AI 전문가입니다. 전문 용어를 사용하되 2-3줄로 간결하게 설명해주세요."
        )
        prompt = f"""기술 키워드 "{keyword}"에 대해 2-3줄로 설명해주세요.
{depth_hint}

마크다운 없이 순수 텍스트로 응답하세요."""
    else:
        prompt = f"""기술 키워드 "{keyword}"에 대해 비전공자도 이해할 수 있도록 2~3줄로 설명해주세요.
- 이 기술이 무엇인지
- 어떤 역할을 하는지
- (해당되면) 새로운 기술인지, 기존 개념을 발전시킨 것인지

마크다운 없이 순수 텍스트로 응답하세요."""

    result = _call_gemini(prompt)
    return result if result else f"{keyword}에 대한 설명을 불러오지 못했습니다."
