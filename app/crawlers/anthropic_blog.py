"""
Anthropic Blog 크롤러
https://www.anthropic.com/news 에서 최신 기사 수집
"""

import httpx
from bs4 import BeautifulSoup
from typing import List
from .base import BaseCrawler, RawArticle

BASE_URL = "https://www.anthropic.com"
NEWS_URL = f"{BASE_URL}/news"


class AnthropicBlogCrawler(BaseCrawler):
    source_name = "Anthropic Blog"

    def fetch(self) -> List[RawArticle]:
        articles = []

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = httpx.get(NEWS_URL, headers=headers, timeout=15, follow_redirects=True)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # Anthropic 뉴스 카드 파싱
            # 링크 태그 중 /news/ 경로를 가진 것들 수집
            seen_urls = set()
            links = soup.find_all("a", href=True)

            for link in links:
                href = link.get("href", "")

                # /news/로 시작하는 개별 기사 링크만
                if not href.startswith("/news/") or href == "/news":
                    continue

                full_url = BASE_URL + href
                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)

                # 제목 추출 (링크 내부 텍스트 또는 부모 요소)
                title = link.get_text(strip=True)
                if not title or len(title) < 10:
                    # 부모 요소에서 제목 찾기
                    parent = link.find_parent(["div", "article", "section"])
                    if parent:
                        heading = parent.find(["h1", "h2", "h3", "h4"])
                        if heading:
                            title = heading.get_text(strip=True)

                if not title or len(title) < 10:
                    continue

                articles.append(RawArticle(
                    title=title,
                    url=full_url,
                    source="Anthropic Blog",
                    score=50,          # 공식 블로그는 기본 점수 부여
                    comment_count=0,
                    view_count=0,
                ))

        except Exception as e:
            print(f"⚠️  Anthropic Blog 크롤링 실패: {e}")

        return articles
