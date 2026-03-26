"""
설정 관련 API 라우터
크롤링 소스 관리 및 수동 크롤링 실행
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.database import get_db

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SourceCreate(BaseModel):
    name: str
    url: str


@router.get("/sources")
def get_sources():
    """크롤링 소스 목록 반환"""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, name, url, is_default, is_active FROM sources ORDER BY is_default DESC, id"
        ).fetchall()
    return {"sources": [dict(row) for row in rows]}


@router.post("/sources")
def add_source(body: SourceCreate):
    """크롤링 소스 추가"""
    if not body.url.startswith("http"):
        raise HTTPException(status_code=400, detail="올바른 URL을 입력해주세요.")

    with get_db() as conn:
        try:
            conn.execute(
                "INSERT INTO sources (name, url, is_default, is_active) VALUES (?, ?, 0, 1)",
                (body.name.strip(), body.url.strip())
            )
        except Exception:
            raise HTTPException(status_code=400, detail="이미 등록된 URL입니다.")

    return {"status": "ok", "message": f"'{body.name}' 소스가 추가되었습니다."}


@router.delete("/sources/{source_id}")
def delete_source(source_id: int):
    """크롤링 소스 삭제 (기본 소스는 삭제 불가)"""
    with get_db() as conn:
        row = conn.execute(
            "SELECT is_default FROM sources WHERE id = ?", (source_id,)
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="소스를 찾을 수 없습니다.")
        if row["is_default"]:
            raise HTTPException(status_code=400, detail="기본 소스는 삭제할 수 없습니다.")

        conn.execute("DELETE FROM sources WHERE id = ?", (source_id,))

    return {"status": "ok", "message": "소스가 삭제되었습니다."}


@router.post("/crawl-now")
def crawl_now():
    """수동 크롤링 실행"""
    from app.services.crawl_service import run_crawling
    result = run_crawling()
    return result


@router.post("/reset-articles")
def reset_articles():
    """기사 데이터 전체 초기화 (번역 오류 데이터 삭제 후 재수집 용도)"""
    with get_db() as conn:
        conn.execute("DELETE FROM articles")
        conn.execute("DELETE FROM daily_summary")
        conn.execute("DELETE FROM keyword_tooltips")
    return {"status": "ok", "message": "기사 데이터가 초기화되었습니다. 다시 수집을 실행해주세요."}
