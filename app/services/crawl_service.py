"""
크롤링 오케스트레이션 서비스
수집 → 소스별 점수 정규화 → 상위 15개 제목 일괄 번역
"""

import json
from datetime import date, datetime
from typing import List

from app.database import get_db
from app.crawlers.reddit import RedditCrawler
from app.crawlers.geeknews import GeeknewsCrawler
from app.crawlers.anthropic_blog import AnthropicBlogCrawler
from app.crawlers.base import RawArticle


def _normalize_scores(articles: List[RawArticle]) -> List[RawArticle]:
    """
    소스별 점수 정규화 (0~100점)
    각 소스 내에서 상대적 순위로 환산 → Reddit 독식 방지
    """
    from collections import defaultdict

    # 소스별 그룹핑
    by_source = defaultdict(list)
    for a in articles:
        by_source[a.source].append(a)

    normalized = []
    for source, group in by_source.items():
        scores = [a.score + a.comment_count * 3 for a in group]
        max_s = max(scores) if scores else 1
        min_s = min(scores) if scores else 0
        rng = max_s - min_s or 1

        for a, raw_score in zip(group, scores):
            a.score = int(((raw_score - min_s) / rng) * 100)
            normalized.append(a)

    return normalized


def run_crawling() -> dict:
    """
    전체 크롤링 실행
    1. 수집
    2. 소스별 점수 정규화
    3. 상위 15개 제목 일괄 번역 (Gemini 1회 호출)
    4. 오늘의 핵심 이슈 생성
    """
    print(f"\n[크롤링 시작] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    crawlers = [
        RedditCrawler(),
        GeeknewsCrawler(),
        AnthropicBlogCrawler(),
    ]

    all_articles: List[RawArticle] = []
    for crawler in crawlers:
        try:
            articles = crawler.fetch()
            print(f"  OK {crawler.source_name}: {len(articles)}개 수집")
            all_articles.extend(articles)
        except Exception as e:
            print(f"  FAIL {crawler.source_name}: {e}")

    if not all_articles:
        return {"status": "error", "message": "수집된 기사 없음"}

    # 소스별 정규화 후 전체 정렬
    all_articles = _normalize_scores(all_articles)
    all_articles.sort(key=lambda a: a.score, reverse=True)

    # DB 저장
    saved_count = 0
    with get_db() as conn:
        for article in all_articles:
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO articles
                        (title_original, url, source, score, comment_count, view_count)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    article.title,
                    article.url,
                    article.source,
                    article.score,
                    article.comment_count,
                    article.view_count,
                ))
                if conn.execute("SELECT changes()").fetchone()[0] > 0:
                    saved_count += 1
            except Exception:
                continue

    print(f"[저장 완료] 신규: {saved_count}개 / 수집: {len(all_articles)}개")

    # 상위 15개 제목 일괄 번역 (미번역 기사만)
    _translate_top_titles(limit=15)

    # 오늘의 핵심 이슈 생성
    _generate_daily_summary_if_needed()

    return {
        "status": "success",
        "total_fetched": len(all_articles),
        "saved": saved_count,
    }


def _translate_top_titles(limit: int = 15):
    """상위 N개 기사 제목 일괄 번역 (Gemini 1회 호출)"""
    from app.services.ai_service import batch_translate_titles

    with get_db() as conn:
        rows = conn.execute("""
            SELECT id, title_original FROM articles
            WHERE title_ko IS NULL OR title_ko = '' OR title_ko = title_original
            ORDER BY score DESC
            LIMIT ?
        """, (limit,)).fetchall()

        if not rows:
            print("[제목 번역] 번역할 기사 없음")
            return

        articles_to_translate = [{"id": r["id"], "title_original": r["title_original"]} for r in rows]
        print(f"[제목 번역] {len(articles_to_translate)}개 일괄 번역 중...")

        translated_titles = batch_translate_titles(articles_to_translate)

        for article, title_ko in zip(articles_to_translate, translated_titles):
            conn.execute(
                "UPDATE articles SET title_ko = ? WHERE id = ?",
                (title_ko, article["id"])
            )

    print("[제목 번역 완료]")


def _generate_daily_summary_if_needed():
    """오늘의 핵심 이슈 생성 (하루 1회)"""
    from app.services.ai_service import generate_daily_summary

    today = date.today().isoformat()
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM daily_summary WHERE date = ?", (today,)
        ).fetchone()
        if existing:
            return

        top_articles = conn.execute(
            "SELECT title_ko, title_original, source FROM articles ORDER BY score DESC LIMIT 15"
        ).fetchall()

        if not top_articles:
            return

        print("[핵심 이슈 생성 중...]")
        summary = generate_daily_summary([dict(r) for r in top_articles])
        conn.execute(
            "INSERT OR REPLACE INTO daily_summary (date, summary) VALUES (?, ?)",
            (today, summary)
        )
        print("[핵심 이슈 완료]")
