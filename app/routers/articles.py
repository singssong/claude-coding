"""
기사 관련 API 라우터
"""

import json
from datetime import date
from fastapi import APIRouter
from app.database import get_db

router = APIRouter(prefix="/api", tags=["articles"])


@router.get("/articles")
def get_articles(limit: int = 30):
    """인기순 기사 목록 반환"""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT id, title_original, title_ko, summary_ko,
                   url, source, score, comment_count, keywords, crawled_at
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


@router.get("/keyword-tooltip/{keyword}")
def get_keyword_tooltip(keyword: str):
    """키워드 툴팁 설명 반환 (캐시 우선)"""
    with get_db() as conn:
        row = conn.execute(
            "SELECT explanation FROM keyword_tooltips WHERE keyword = ?", (keyword,)
        ).fetchone()

    if row:
        return {"keyword": keyword, "explanation": row["explanation"]}

    # 캐시 없으면 실시간 생성
    from app.services.ai_service import generate_keyword_tooltip
    explanation = generate_keyword_tooltip(keyword)

    with get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO keyword_tooltips (keyword, explanation) VALUES (?, ?)",
            (keyword, explanation)
        )

    return {"keyword": keyword, "explanation": explanation}
