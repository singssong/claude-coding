"""
기사 본문 수집기
URL에서 실제 기사 내용을 추출해 AI 분석에 활용
"""

import httpx
from bs4 import BeautifulSoup


# 본문 추출 시 제거할 태그
SKIP_TAGS = ["script", "style", "nav", "header", "footer",
             "aside", "form", "button", "iframe", "noscript"]

# 본문일 가능성이 높은 태그
CONTENT_TAGS = ["article", "main", ".post-body", ".entry-content",
                ".article-body", ".content", "[role='main']"]


def fetch_article_content(url: str, max_chars: int = 3000) -> str:
    """
    URL에서 기사 본문 텍스트 추출
    실패 시 빈 문자열 반환
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = httpx.get(url, headers=headers, timeout=12, follow_redirects=True)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # 불필요한 태그 제거
        for tag in soup(SKIP_TAGS):
            tag.decompose()

        # 본문 영역 우선 탐색
        body_text = ""
        for selector in CONTENT_TAGS:
            el = soup.select_one(selector)
            if el:
                body_text = el.get_text(separator="\n", strip=True)
                if len(body_text) > 200:
                    break

        # 본문 영역 못 찾으면 body 전체
        if not body_text:
            body = soup.find("body")
            body_text = body.get_text(separator="\n", strip=True) if body else ""

        # 빈 줄 정리 및 글자 수 제한
        lines = [l.strip() for l in body_text.splitlines() if l.strip()]
        cleaned = "\n".join(lines)

        return cleaned[:max_chars]

    except Exception as e:
        print(f"  ⚠️  본문 수집 실패 ({url[:50]}...): {e}")
        return ""
