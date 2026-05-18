import os  # 💡 파일 경로 존재 여부 체크를 위해 추가
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse          # 💡 사이트맵 XML 파일 직접 반환을 위해 추가
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
    "*",  # 테스트 및 운영 단계에서 모든 접속 허용
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
# 🚨 [핵심 추가] 루트 주소로 들어오는 사이트맵 요청 동적 가로채기 라우터
# =========================================================================
# 브라우저가 /sitemap-static.xml 또는 /sitemap-majors.xml 로 직접 들어올 때
# 프론트엔드/Nginx의 우회 규칙과 상관없이 백엔드가 해당 이름의 실제 XML 파일을 1:1로 정확히 반환합니다.
@app.get("/sitemap-{filename}.xml")
def route_sitemap_by_name(filename: str):
    target_path = f"static/sitemaps/sitemap-{filename}.xml"
    
    # 해당 파일이 서버 디스크에 물리적으로 존재하면 그대로 서빙
    if os.path.exists(target_path):
        return FileResponse(target_path, media_type="application/xml")
    
    # 엣지 케이스 안전장치: 만약 파일이 없으면 기본 파일이라도 반환
    return FileResponse("static/sitemaps/sitemap-static.xml", media_type="application/xml")


# 마스터 인덱스 지도용 라우터 (https://integer7813.cloud/sitemap.xml 대응)
@app.get("/sitemap.xml")
def route_sitemap_index():
    target_path = "static/sitemaps/sitemap.xml"
    if os.path.exists(target_path):
        return FileResponse(target_path, media_type="application/xml")
    return FileResponse("static/sitemaps/sitemap-static.xml", media_type="application/xml")
# =========================================================================


# 생성된 사이트맵 XML 파일 고속 서빙을 위한 정적 라우트 매핑 (기존 유지)
app.mount("/api/sitemaps", StaticFiles(directory="static/sitemaps"), name="sitemaps")


@app.get("/")
def root():
    kst_time = datetime.now(ZoneInfo("Asia/Seoul"))
    return {
        "status": "success",
        "message": "--* API Server is running normally *--",
        "server_time_kst": kst_time.strftime("%Y-%m-%d %H:%M:%S KST")
    }