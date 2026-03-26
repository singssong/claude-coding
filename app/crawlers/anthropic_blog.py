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

            seen_urls = set()

            # /news/slug 형태의 링크 중 heading이 있는 카드만 수집
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                if not href.startswith("/news/") or href == "/news/":
                    continue

                full_url = BASE_URL + href
                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)

                # 링크 또는 부모 블록에서 h2/h3 제목 찾기
                title = ""
                search_el = link if link.get_text(strip=True) else link.find_parent()
                for _ in range(4):
                    if search_el is None:
                        break
                    heading = search_el.find(["h2", "h3", "h4"])
                    if heading:
                        title = heading.get_text(strip=True)
                        break
                    search_el = search_el.find_parent()

                # heading 없으면 링크 텍스트에서 날짜/카테고리 제거
                if not title:
                    raw = link.get_text(separator=" ", strip=True)
                    # "Product Feb 17, 2026 제목 본문..." 형태에서 제목만 추출
                    # 날짜 패턴(숫자 4자리) 이후 첫 문장
                    import re
                    match = re.split(r'\d{4}\s+', raw, maxsplit=1)
                    title = match[-1].strip() if match else raw

                if not title or len(title) < 8:
                    continue

                articles.append(RawArticle(
                    title=title,
                    url=full_url,
                    source="Anthropic Blog",
                    score=50,
                    comment_count=0,
                    view_count=0,
                ))

        except Exception as e:
            print(f"⚠️  Anthropic Blog 크롤링 실패: {e}")

        return articles
