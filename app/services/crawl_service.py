"""
크롤링 오케스트레이션 서비스
수집만 담당 - AI 번역/요약은 사용자가 기사 클릭 시 온디맨드로 처리
"""

import json
from datetime import date, datetime
from typing import List

from app.database import get_db
from app.crawlers.reddit import RedditCrawler
from app.crawlers.geeknews import GeeknewsCrawler
from app.crawlers.anthropic_blog import AnthropicBlogCrawler
from app.crawlers.base import RawArticle


def calculate_score(article: RawArticle) -> int:
    """인기도 점수 계산 (업보트 + 댓글 가중치)"""
    return article.score + (article.comment_count * 3)


def run_crawling() -> dict:
    """
    전체 크롤링 실행 - 빠르게 수집만 수행
    AI 번역/요약은 사용자가 기사 클릭 시 온디맨드로 처리
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

    # 인기도 점수 계산 후 정렬
    all_articles.sort(key=calculate_score, reverse=True)

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
                    calculate_score(article),
                    article.comment_count,
                    article.view_count,
                ))
                if conn.execute("SELECT changes()").fetchone()[0] > 0:
                    saved_count += 1
            except Exception:
                continue

    print(f"[크롤링 완료] 신규 저장: {saved_count}개 / 전체 수집: {len(all_articles)}개")

    # 오늘의 핵심 이슈는 DB에 기사가 충분할 때 별도 생성
    _generate_daily_summary_if_needed()

    return {
        "status": "success",
        "total_fetched": len(all_articles),
        "saved": saved_count,
    }


def _generate_daily_summary_if_needed():
    """DB 상위 기사 기반으로 오늘의 핵심 이슈 생성 (하루 1회)"""
    from app.services.ai_service import generate_daily_summary

    today = date.today().isoformat()
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM daily_summary WHERE date = ?", (today,)
        ).fetchone()
        if existing:
            return

        top_articles = conn.execute(
            "SELECT title_original, source FROM articles ORDER BY score DESC LIMIT 15"
        ).fetchall()

        if not top_articles:
            return

        articles_for_summary = [dict(row) for row in top_articles]
        print("[핵심 이슈 생성 중...]")
        summary = generate_daily_summary(articles_for_summary)
        conn.execute(
            "INSERT OR REPLACE INTO daily_summary (date, summary) VALUES (?, ?)",
            (today, summary)
        )
        print("[핵심 이슈 저장 완료]")
