"""
Reddit 크롤러
공개 JSON API를 이용해 인기 게시물 수집 (인증 불필요)
"""

import httpx
from typing import List
from .base import BaseCrawler, RawArticle


# 수집할 서브레딧 목록
SUBREDDITS = [
    "MachineLearning",
    "artificial",
    "technology",
    "LocalLLaMA",
    "singularity",
]


class RedditCrawler(BaseCrawler):
    source_name = "Reddit"

    def fetch(self) -> List[RawArticle]:
        articles = []

        headers = {
            "User-Agent": "TrendLens/1.0 (tech news aggregator)"
        }

        for subreddit in SUBREDDITS:
            url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=25"
            try:
                response = httpx.get(url, headers=headers, timeout=10, follow_redirects=True)
                response.raise_for_status()
                data = response.json()

                posts = data.get("data", {}).get("children", [])
                for post in posts:
                    p = post.get("data", {})

                    # 자기 홍보 게시물, 고정 게시물 제외
                    if p.get("stickied") or p.get("is_self") and p.get("score", 0) < 100:
                        continue

                    # 링크 기사만 수집 (self 포스트 중 점수 낮은 것 제외)
                    article_url = p.get("url", "")
                    if not article_url or article_url.startswith("https://www.reddit.com"):
                        continue

                    articles.append(RawArticle(
                        title=p.get("title", "").strip(),
                        url=article_url,
                        source=f"Reddit r/{subreddit}",
                        score=p.get("score", 0),
                        comment_count=p.get("num_comments", 0),
                        view_count=0,  # Reddit은 조회수 공개 안 함
                    ))

            except Exception as e:
                print(f"⚠️  Reddit r/{subreddit} 크롤링 실패: {e}")
                continue

        return articles
