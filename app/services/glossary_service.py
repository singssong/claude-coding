"""
단어장 서비스
Wikipedia API로 기술 용어 설명 + 이미지 자동 수집
"""

import httpx
from app.database import get_db
from app.services.ai_service import _call_gemini


def fetch_from_wikipedia(keyword: str) -> dict:
    """
    Wikipedia REST API로 용어 설명 + 이미지 URL 수집
    한국어 위키 우선, 없으면 영문 위키 → Gemini로 번역
    반환: {"explanation": str, "image_url": str | None}
    """
    # 1. 한국어 위키피디아 시도
    result = _fetch_wiki("ko", keyword)
    if result["explanation"]:
        return result

    # 2. 영문 위키피디아 시도 후 번역
    result = _fetch_wiki("en", keyword)
    if result["explanation"]:
        translated = _translate_to_korean(keyword, result["explanation"])
        result["explanation"] = translated
        return result

    return {"explanation": "", "image_url": None}


def _fetch_wiki(lang: str, keyword: str) -> dict:
    """Wikipedia REST API 호출"""
    try:
        url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{keyword}"
        res = httpx.get(url, timeout=8, follow_redirects=True,
                        headers={"User-Agent": "TrendLens/1.0"})
        if res.status_code != 200:
            return {"explanation": "", "image_url": None}

        data = res.json()
        explanation = data.get("extract", "")
        image_url = None

        thumbnail = data.get("thumbnail") or data.get("originalimage")
        if thumbnail:
            image_url = thumbnail.get("source")

        # 너무 긴 설명은 앞부분만 사용
        if len(explanation) > 300:
            explanation = explanation[:300].rsplit(".", 1)[0] + "."

        return {"explanation": explanation, "image_url": image_url}

    except Exception:
        return {"explanation": "", "image_url": None}


def _translate_to_korean(keyword: str, english_text: str) -> str:
    """영문 위키 내용을 한국어로 번역"""
    prompt = f"""다음 기술 용어 "{keyword}"에 대한 영문 설명을 한국어로 번역해주세요.
비전공자도 이해할 수 있도록 쉽게 번역하되, 핵심 내용을 유지하세요.
마크다운 없이 2~3줄로 작성하세요.

원문: {english_text}"""
    result = _call_gemini(prompt)
    return result if result else english_text


def add_keyword_to_glossary(keyword: str, force_refresh: bool = False) -> dict:
    """
    단어장에 키워드 추가
    - Wikipedia에서 우선 수집
    - 없으면 Gemini로 생성
    - force_refresh=True면 기존 데이터 덮어쓰기
    """
    with get_db() as conn:
        existing = conn.execute(
            "SELECT keyword, explanation, image_url FROM keyword_tooltips WHERE keyword = ?",
            (keyword,)
        ).fetchone()

        if existing and not force_refresh:
            return dict(existing)

    # Wikipedia 수집 시도
    wiki = fetch_from_wikipedia(keyword)

    if wiki["explanation"]:
        explanation = wiki["explanation"]
        image_url = wiki["image_url"]
        source = "wikipedia"
    else:
        # Wikipedia 실패 시 Gemini로 생성
        from app.services.ai_service import generate_keyword_tooltip
        explanation = generate_keyword_tooltip(keyword)
        image_url = None
        source = "ai"

    with get_db() as conn:
        conn.execute("""
            INSERT INTO keyword_tooltips (keyword, explanation, image_url, source)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(keyword) DO UPDATE SET
                explanation = excluded.explanation,
                image_url = excluded.image_url,
                source = excluded.source
        """, (keyword, explanation, image_url, source))

    return {"keyword": keyword, "explanation": explanation, "image_url": image_url, "source": source}


# 기본 AI 기술 용어 목록 (단어장 초기 구축용)
INITIAL_KEYWORDS = [
    # AI/ML 기초
    "LLM", "GPT", "Transformer", "RAG", "Fine-tuning", "Prompt engineering",
    "Embedding", "Vector database", "Inference", "Training",
    # 모델 아키텍처
    "MoE", "Attention mechanism", "RLHF", "LoRA", "Quantization",
    # AI 에이전트
    "AI Agent", "Multi-agent", "Tool use", "Function calling",
    # 인프라
    "GPU", "TPU", "CUDA", "Data center", "Edge computing", "Kubernetes",
    # 스타트업/비즈니스
    "Unicorn", "Series A", "Seed funding", "Valuation",
    # 로봇
    "Humanoid robot", "Computer vision", "ROS",
]


def build_initial_glossary():
    """초기 단어장 구축 - 서버 시작 시 또는 수동으로 실행"""
    print(f"[단어장 구축 시작] 총 {len(INITIAL_KEYWORDS)}개 키워드")
    success = 0
    for keyword in INITIAL_KEYWORDS:
        try:
            result = add_keyword_to_glossary(keyword)
            src = result.get("source", "?")
            print(f"  OK [{src}] {keyword}")
            success += 1
        except Exception as e:
            print(f"  FAIL {keyword}: {e}")
    print(f"[단어장 구축 완료] {success}/{len(INITIAL_KEYWORDS)}개")
