"""
크롤러 기본 클래스 - 모든 크롤러가 공통으로 상속
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List


@dataclass
class RawArticle:
    """크롤러에서 수집한 원시 기사 데이터"""
    title: str
    url: str
    source: str
    score: int = 0
    comment_count: int = 0
    view_count: int = 0
    crawled_at: datetime = field(default_factory=datetime.now)


class BaseCrawler:
    """크롤러 기본 클래스"""

    source_name: str = "unknown"

    def fetch(self) -> List[RawArticle]:
        """기사 목록 수집 - 각 크롤러에서 구현"""
        raise NotImplementedError
