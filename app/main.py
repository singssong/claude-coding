"""
TrendLens - FastAPI 메인 앱
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import os

from app.database import init_db
from app.routers import articles, settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서버 시작 시 DB 초기화
    init_db()
    yield


app = FastAPI(
    title="TrendLens",
    description="AI 기술 트렌드 뉴스 집약 서비스",
    version="0.1.0",
    lifespan=lifespan,
)

# API 라우터 등록
app.include_router(articles.router)
app.include_router(settings.router)

# 정적 파일 서빙
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def index():
    return FileResponse(os.path.join(static_dir, "index.html"))


@app.get("/settings")
def settings_page():
    return FileResponse(os.path.join(static_dir, "settings.html"))
