"""
Geeknews (news.hada.io) 크롤러
포인트 및 댓글 수 기반 인기 기사 수집
"""

import httpx
from bs4 import BeautifulSoup
from typing import List
from .base import BaseCrawler, RawArticle

BASE_URL = "https://news.hada.io"


class GeeknewsCrawler(BaseCrawler):
    source_name = "Geeknews"

    def fetch(self) -> List[RawArticle]:
        articles = []

        try:
            response = httpx.get(BASE_URL, timeout=10, follow_redirects=True)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            topic_items = soup.select("div.topic_row")

            for item in topic_items[:30]:
                try:
                    # 실제 기사 링크 (.topictitle > a)
                    title_tag = item.select_one(".topictitle a")
                    if not title_tag:
                        continue

                    url = title_tag.get("href", "")
                    # javascript: 링크 제외
                    if not url or url.startswith("javascript"):
                        continue

                    # 제목: h1 태그 우선, 없으면 링크 텍스트
                    h1 = title_tag.select_one("h1")
                    title = h1.get_text(strip=True) if h1 else title_tag.get_text(strip=True)
                    if not title:
                        continue

                    # 포인트 파싱 (span[id^="tp"])
                    score = 0
                    score_tag = item.select_one("span[id^='tp']")
                    if score_tag:
                        try:
                            score = int(score_tag.get_text(strip=True))
                        except ValueError:
                            score = 0

                    # 댓글 수 파싱 (a[href*="go=comments"])
                    comment_count = 0
                    comment_tag = item.select_one("a[href*='go=comments']")
                    if comment_tag:
                        comment_text = comment_tag.get_text(strip=True)
                        digits = "".join(filter(str.isdigit, comment_text))
                        comment_count = int(digits) if digits else 0

                    articles.append(RawArticle(
                        title=title,
                        url=url,
                        source="Geeknews",
                        score=score,
                        comment_count=comment_count,
                        view_count=0,
                    ))

                except Exception:
                    continue

        except Exception as e:
            print(f"⚠️  Geeknews 크롤링 실패: {e}")

        return articles
