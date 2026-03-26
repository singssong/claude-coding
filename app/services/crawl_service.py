"""
크롤링 오케스트레이션 서비스
모든 크롤러를 실행하고 결과를 DB에 저장
"""

import json
from datetime import date, datetime
from typing import List

from app.database import get_db
from app.crawlers.reddit import RedditCrawler
from app.crawlers.geeknews import GeeknewsCrawler
from app.crawlers.anthropic_blog import AnthropicBlogCrawler
from app.crawlers.base import RawArticle
from app.services.ai_service import translate_and_summarize, generate_daily_summary, generate_keyword_tooltip
from app.services.content_fetcher import fetch_article_content


def calculate_score(article: RawArticle) -> int:
    """인기도 점수 계산 (업보트 + 댓글 가중치)"""
    return article.score + (article.comment_count * 3)


def run_crawling() -> dict:
    """
    전체 크롤링 실행
    1. 모든 소스에서 기사 수집
    2. 기사 본문 수집
    3. AI로 번역/요약/키워드 추출
    4. DB 저장
    5. 오늘의 핵심 이슈 생성 (항상 갱신)
    """
    print(f"\n🚀 크롤링 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    crawlers = [
        RedditCrawler(),
        GeeknewsCrawler(),
        AnthropicBlogCrawler(),
    ]

    all_articles: List[RawArticle] = []
    for crawler in crawlers:
        try:
            articles = crawler.fetch()
            print(f"  ✅ {crawler.source_name}: {len(articles)}개 수집")
            all_articles.extend(articles)
        except Exception as e:
            print(f"  ❌ {crawler.source_name} 실패: {e}")

    if not all_articles:
        return {"status": "error", "message": "수집된 기사 없음"}

    # 인기도 점수 계산 후 정렬
    all_articles.sort(key=calculate_score, reverse=True)

    saved_count = 0

    print(f"\n🤖 AI 처리 시작 (총 {len(all_articles)}개)...")

    with get_db() as conn:
        for article in all_articles:
            # 이미 저장된 URL이면 스킵
            existing = conn.execute(
                "SELECT id FROM articles WHERE url = ?", (article.url,)
            ).fetchone()
            if existing:
                continue

            # 기사 본문 수집
            print(f"  🔄 처리 중: {article.title[:50]}...")
            content = fetch_article_content(article.url)

            # AI 번역 + 요약 + 키워드 추출 (본문 포함)
            ai_result = translate_and_summarize(article.title, article.url, content)

            # 키워드 툴팁 캐싱
            for keyword in ai_result.get("keywords", []):
                existing_tooltip = conn.execute(
                    "SELECT id FROM keyword_tooltips WHERE keyword = ?", (keyword,)
                ).fetchone()
                if not existing_tooltip:
                    tooltip = generate_keyword_tooltip(keyword)
                    conn.execute(
                        "INSERT INTO keyword_tooltips (keyword, explanation) VALUES (?, ?)",
                        (keyword, tooltip)
                    )

            # DB 저장
            conn.execute("""
                INSERT OR IGNORE INTO articles
                    (title_original, title_ko, summary_ko, url, source,
                     score, comment_count, view_count, keywords)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                article.title,
                ai_result.get("title_ko", article.title),
                ai_result.get("summary_ko", ""),
                article.url,
                article.source,
                calculate_score(article),
                article.comment_count,
                article.view_count,
                json.dumps(ai_result.get("keywords", []), ensure_ascii=False),
            ))

            saved_count += 1

        print(f"\n💾 DB 저장 완료: {saved_count}개")

        # 오늘의 핵심 이슈 생성 - 신규 기사가 없어도 항상 갱신
        today = date.today().isoformat()
        print("📝 오늘의 핵심 이슈 생성 중...")

        top_articles = conn.execute(
            "SELECT title_ko, title_original, source FROM articles ORDER BY score DESC LIMIT 15"
        ).fetchall()

        if top_articles:
            articles_for_summary = [dict(row) for row in top_articles]
            summary = generate_daily_summary(articles_for_summary)
            conn.execute(
                "INSERT OR REPLACE INTO daily_summary (date, summary) VALUES (?, ?)",
                (today, summary)
            )
            print("✅ 오늘의 핵심 이슈 저장 완료")

    return {
        "status": "success",
        "total_fetched": len(all_articles),
        "saved": saved_count,
    }
