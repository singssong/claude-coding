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
    conn.row_factory = sqlite3.Row
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
    """테이블 생성 및 컬럼 마이그레이션"""
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
                is_translated   INTEGER DEFAULT 0,
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

            -- 단어장 테이블 (키워드 툴팁 + 이미지)
            CREATE TABLE IF NOT EXISTS keyword_tooltips (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword     TEXT UNIQUE NOT NULL,
                explanation TEXT NOT NULL,
                image_url   TEXT,
                source      TEXT DEFAULT 'ai',
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

        # 기존 테이블에 누락된 컬럼 추가 (마이그레이션)
        _migrate(conn)

        # 기본 소스 목록 삽입
        default_sources = [
            ("Reddit - MachineLearning", "https://www.reddit.com/r/MachineLearning/hot.json", "reddit"),
            ("Reddit - artificial",      "https://www.reddit.com/r/artificial/hot.json",      "reddit"),
            ("Reddit - technology",      "https://www.reddit.com/r/technology/hot.json",      "reddit"),
            ("Geeknews",                 "https://news.hada.io",                               "html"),
            ("Anthropic Blog",           "https://www.anthropic.com/news",                     "html"),
        ]
        conn.executemany(
            "INSERT OR IGNORE INTO sources (name, url, source_type, is_default, is_active) VALUES (?, ?, ?, 1, 1)",
            default_sources
        )

    print("DB 초기화 완료")


def _migrate(conn):
    """기존 DB에 새 컬럼 추가 (없을 때만)"""
    existing = {row[1] for row in conn.execute("PRAGMA table_info(articles)").fetchall()}
    if "is_translated" not in existing:
        conn.execute("ALTER TABLE articles ADD COLUMN is_translated INTEGER DEFAULT 0")
    if "why_for_user" not in existing:
        conn.execute("ALTER TABLE articles ADD COLUMN why_for_user TEXT")

    existing_kt = {row[1] for row in conn.execute("PRAGMA table_info(keyword_tooltips)").fetchall()}
    if "image_url" not in existing_kt:
        conn.execute("ALTER TABLE keyword_tooltips ADD COLUMN image_url TEXT")
    if "source" not in existing_kt:
        conn.execute("ALTER TABLE keyword_tooltips ADD COLUMN source TEXT DEFAULT 'ai'")

    existing_ds = {row[1] for row in conn.execute("PRAGMA table_info(daily_summary)").fetchall()}
    if "format_version" not in existing_ds:
        conn.execute("ALTER TABLE daily_summary ADD COLUMN format_version TEXT DEFAULT 'v1'")
