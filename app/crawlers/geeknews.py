"""
Geeknews (news.hada.io) 크롤러
한국 기술 커뮤니티 - 포인트 및 댓글 수 기반 인기 기사 수집
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

            # Geeknews 기사 목록 파싱
            # 각 기사는 .topic-row 또는 li 형태로 구성
            topic_items = soup.select("li.topic-row") or soup.select(".topic_row") or soup.select("li")

            for item in topic_items[:30]:
                try:
                    # 제목 및 링크
                    title_tag = item.select_one("a.topic-title") or item.select_one(".title a") or item.select_one("a")
                    if not title_tag:
                        continue

                    title = title_tag.get_text(strip=True)
                    url = title_tag.get("href", "")
                    if not url or not title:
                        continue

                    # 상대 경로 처리
                    if url.startswith("/"):
                        url = BASE_URL + url

                    # 포인트(점수) 파싱
                    score = 0
                    score_tag = item.select_one(".score") or item.select_one(".point") or item.select_one(".votes")
                    if score_tag:
                        score_text = score_tag.get_text(strip=True).replace(",", "")
                        try:
                            score = int("".join(filter(str.isdigit, score_text)))
                        except ValueError:
                            score = 0

                    # 댓글 수 파싱
                    comment_count = 0
                    comment_tag = item.select_one(".comments") or item.select_one(".comment-count")
                    if comment_tag:
                        comment_text = comment_tag.get_text(strip=True).replace(",", "")
                        try:
                            comment_count = int("".join(filter(str.isdigit, comment_text)))
                        except ValueError:
                            comment_count = 0

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
