"""
데이터베이스 초기화 및 연결 관리
SQLite 사용 (추후 PostgreSQL로 확장 가능하도록 설계)
"""

import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "trendlens.db")


def get_connection():
    """DB 연결 반환"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # dict처럼 컬럼명으로 접근 가능
    return conn


@contextmanager
def get_db():
    """DB 연결 컨텍스트 매니저"""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """테이블 생성 (최초 실행 시 1회)"""
    with get_db() as conn:
        conn.executescript("""
            -- 기사 테이블
            CREATE TABLE IF NOT EXISTS articles (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                title_original  TEXT NOT NULL,
                title_ko        TEXT,
                summary_ko      TEXT,
                url             TEXT UNIQUE NOT NULL,
                source          TEXT NOT NULL,
                category        TEXT DEFAULT 'AI',
                score           INTEGER DEFAULT 0,
                comment_count   INTEGER DEFAULT 0,
                view_count      INTEGER DEFAULT 0,
                keywords        TEXT DEFAULT '[]',
                crawled_at      DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            -- 오늘의 핵심 이슈 테이블
            CREATE TABLE IF NOT EXISTS daily_summary (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                date        DATE UNIQUE NOT NULL,
                summary     TEXT NOT NULL,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            -- 크롤링 소스 테이블
            CREATE TABLE IF NOT EXISTS sources (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                url         TEXT UNIQUE NOT NULL,
                source_type TEXT DEFAULT 'html',
                is_default  INTEGER DEFAULT 0,
                is_active   INTEGER DEFAULT 1
            );

            -- 키워드 툴팁 캐시 테이블 (동일 키워드 반복 API 호출 방지)
            CREATE TABLE IF NOT EXISTS keyword_tooltips (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword     TEXT UNIQUE NOT NULL,
                explanation TEXT NOT NULL,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            -- 추후 유저 기능 확장을 위한 users 테이블 (MVP에서는 미사용)
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                email       TEXT UNIQUE,
                nickname    TEXT,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 기본 소스 목록 삽입 (중복 방지)
        default_sources = [
            ("Reddit - MachineLearning", "https://www.reddit.com/r/MachineLearning/hot.json", "reddit"),
            ("Reddit - artificial",      "https://www.reddit.com/r/artificial/hot.json",      "reddit"),
            ("Reddit - technology",      "https://www.reddit.com/r/technology/hot.json",      "reddit"),
            ("Geeknews",                 "https://news.hada.io",                               "html"),
            ("Anthropic Blog",           "https://www.anthropic.com/news",                     "html"),
        ]
        conn.executemany(
            """INSERT OR IGNORE INTO sources (name, url, source_type, is_default, is_active)
               VALUES (?, ?, ?, 1, 1)""",
            default_sources
        )

    print("✅ DB 초기화 완료")
