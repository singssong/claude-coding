"""
기사 관련 API 라우터
"""

import json
from datetime import date
from fastapi import APIRouter, HTTPException
from app.database import get_db

router = APIRouter(prefix="/api", tags=["articles"])


@router.get("/articles")
def get_articles(limit: int = 50):
    """인기순 기사 목록 반환"""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT id, title_original, title_ko, summary_ko,
                   url, source, score, comment_count, keywords, crawled_at,
                   is_translated, why_for_user
            FROM articles
            ORDER BY score DESC
            LIMIT ?
        """, (limit,)).fetchall()

    articles = []
    for row in rows:
        article = dict(row)
        try:
            article["keywords"] = json.loads(article.get("keywords") or "[]")
        except Exception:
            article["keywords"] = []
        articles.append(article)

    return {"articles": articles}


@router.post("/articles/{article_id}/translate")
def translate_article(article_id: int):
    """
    온디맨드 기사 번역
    - DB에 캐시된 번역이 있으면 즉시 반환
    - 없으면 본문 수집 + Gemini 번역 후 DB에 저장
    """
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, title_original, url, title_ko, summary_ko, keywords, is_translated, why_for_user FROM articles WHERE id = ?",
            (article_id,)
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="기사를 찾을 수 없습니다.")

    article = dict(row)

    # 이미 번역된 경우 캐시 반환
    if article.get("is_translated"):
        try:
            article["keywords"] = json.loads(article.get("keywords") or "[]")
        except Exception:
            article["keywords"] = []
        return article

    # 크롤 시점에 why_for_user가 이미 생성된 경우 보존 (덮어쓰지 않음)
    existing_why = article.get("why_for_user") or None

    # 본문 수집
    from app.services.content_fetcher import fetch_article_content
    from app.services.ai_service import translate_and_summarize, generate_keyword_tooltip

    content = fetch_article_content(article["url"])

    # Gemini 번역/요약/키워드 추출
    ai_result = translate_and_summarize(article["title_original"], article["url"], content)

    title_ko = ai_result.get("title_ko", article["title_original"])
    summary_ko = ai_result.get("summary_ko", "")
    keywords = ai_result.get("keywords", [])
    # 크롤 시점 값이 있으면 보존, 없으면 온디맨드 결과 사용
    why_for_user = existing_why or ai_result.get("why_for_user")

    # 키워드 툴팁 캐싱 (단어장에 없는 것만)
    with get_db() as conn:
        for keyword in keywords:
            exists = conn.execute(
                "SELECT id FROM keyword_tooltips WHERE keyword = ?", (keyword,)
            ).fetchone()
            if not exists:
                tooltip = generate_keyword_tooltip(keyword)
                conn.execute(
                    "INSERT OR IGNORE INTO keyword_tooltips (keyword, explanation) VALUES (?, ?)",
                    (keyword, tooltip)
                )

        # 번역 결과 DB 저장 (캐싱)
        conn.execute("""
            UPDATE articles
            SET title_ko = ?, summary_ko = ?, keywords = ?, is_translated = 1,
                why_for_user = ?
            WHERE id = ?
        """, (
            title_ko,
            summary_ko,
            json.dumps(keywords, ensure_ascii=False),
            why_for_user,
            article_id,
        ))

    return {
        "id": article_id,
        "title_original": article["title_original"],
        "title_ko": title_ko,
        "summary_ko": summary_ko,
        "keywords": keywords,
        "url": article["url"],
        "is_translated": 1,
        "why_for_user": why_for_user,
    }


@router.get("/daily-summary")
def get_daily_summary():
    """오늘의 핵심 이슈 반환"""
    today = date.today().isoformat()
    with get_db() as conn:
        row = conn.execute(
            "SELECT summary, created_at FROM daily_summary WHERE date = ?", (today,)
        ).fetchone()

    if row:
        return {"date": today, "summary": row["summary"], "created_at": row["created_at"]}
    return {"date": today, "summary": None, "created_at": None}


@router.get("/profile")
def get_profile():
    """사용자 프로필 반환 (없으면 404)"""
    try:
        from app.services.ai_service import load_user_profile
        profile = load_user_profile()
        return {"name": profile.get("name"), "interests": profile.get("interests", [])}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="프로필 없음")


@router.get("/keyword-tooltip/{keyword}")
def get_keyword_tooltip(keyword: str):
    """키워드 툴팁 설명 반환 (캐시 우선)"""
    with get_db() as conn:
        row = conn.execute(
            "SELECT explanation, image_url FROM keyword_tooltips WHERE keyword = ?", (keyword,)
        ).fetchone()

    if row:
        return {"keyword": keyword, "explanation": row["explanation"], "image_url": row["image_url"]}

    # 캐시 없으면 실시간 생성
    from app.services.ai_service import generate_keyword_tooltip
    explanation = generate_keyword_tooltip(keyword)

    with get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO keyword_tooltips (keyword, explanation) VALUES (?, ?)",
            (keyword, explanation)
        )

    return {"keyword": keyword, "explanation": explanation, "image_url": None}
