import os  # 파일 경로 존재 여부 체크를 위해 필수
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse          # 사이트맵 XML 파일 직접 반환용
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from datetime import datetime
from zoneinfo import ZoneInfo
from contextlib import asynccontextmanager

# 사이트맵 빌드 스크립트 기능 임포트
from generate_sitemaps import generate_sitemaps

# 리미터 정의
limiter = Limiter(key_func=get_remote_address)

from routes.random_university import router as random_router
from routes.search_university import router as search_router
from routes.locate_university import router as locate_router
from routes.univ_directory import router as univ_directory
from routes.majors import router as majors

# FastAPI 서버가 켜질 때 자동으로 사이트맵을 새로 생성하는 수명 주기(lifespan) 설정
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        generate_sitemaps()
    except Exception as e:
        print(f"❌ 서버 시작 중 사이트맵 생성 실패: {e}")
    yield

# lifespan 환경을 FastAPI 인스턴스에 주입
app = FastAPI(lifespan=lifespan)

# CORS 설정
origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 리미터 연결 및 핸들러 등록
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 라우터 등록
app.include_router(random_router)
app.include_router(search_router)
app.include_router(locate_router)
app.include_router(univ_directory)
app.include_router(majors)


# =========================================================================
# 🚨 [버그 원천 차단] 루트 주소 사이트맵 동적 라우터
# =========================================================================

# 1. 마스터 인덱스 지도 전용 라우터 (https://integer7813.cloud/sitemap.xml 대응)
# 💡 유저가 sitemap.xml을 치면 어떤 예외 상황에서도 무조건 진짜 마스터 인덱스 파일만 리턴합니다.
@app.get("/sitemap.xml")
def route_sitemap_index():
    target_path = "static/sitemaps/sitemap.xml"
    if os.path.exists(target_path):
        return FileResponse(target_path, media_type="application/xml")
    
    # 만약 빌드가 덜 끝났거나 파일이 물리적으로 없으면 404 에러를 내서 로봇이 재수집하게 유도합니다.
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Sitemap Index Not Found. Please wait for generation.")


# 2. 서브 사이트맵 파일명 매칭 라우터 (/sitemap-static.xml, /sitemap-majors.xml 등)
@app.get("/sitemap-{filename}.xml")
def route_sitemap_by_name(filename: str):
    target_path = f"static/sitemaps/sitemap-{filename}.xml"
    
    if os.path.exists(target_path):
        return FileResponse(target_path, media_type="application/xml")
    
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Sub Sitemap Not Found.")
# =========================================================================


# 정적 파일 서빙 백업 매핑 (기존 유지)
app.mount("/api/sitemaps", StaticFiles(directory="static/sitemaps"), name="sitemaps")


@app.get("/")
def root():
    kst_time = datetime.now(ZoneInfo("Asia/Seoul"))
    return {
        "status": "success",
        "message": "--* API Server is running normally *--",
        "server_time_kst": kst_time.strftime("%Y-%m-%d %H:%M:%S KST")
    }