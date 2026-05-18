import os  # 파일 경로 존재 여부 체크를 위해 필수
from fastapi import FastAPI, Request
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

# 🚨 [수정 완료] 모든 라우터 일괄 캐싱 미들웨어 (랜덤 라우터 제외 로직 추가)
@app.middleware("http")
async def add_cache_control_header(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    
    # 💡 캐싱에서 완전히 제외할 정확한 경로들을 정의합니다.
    # (여기에 실제 random_router의 엔드포인트 주소를 적어주세요. 예: "/university/random")
    bypass_paths = ["/", "/sitemap.xml", "/university/random"]
    
    # 안전장치: 경로에 'random'이라는 단어가 포함되어 있거나, bypass 목록에 있으면 캐싱 안 함
    if (
        path not in bypass_paths 
        and "random" not in path.lower()  # 💡 URL에 'random'이 들어가면 무조건 패스
        and not path.startswith("/sitemap-") 
        and not path.startswith("/static/")
        and response.status_code == 200
    ):
        # 1시간(3600초) 동안 브라우저/클라이언트단 캐싱 적용
        response.headers["Cache-Control"] = "public, max-age=3600"
    else:
        # 💡 랜덤이나 예외 경로에는 캐싱을 명시적으로 금지하는 헤더를 붙여서 사파리/크롬의 오작동을 원천 차단합니다.
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        
    return response

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

# 1. 마스터 인덱스 지도 전용 라우터 (https://api.integer7813.cloud/sitemap.xml 직접 대응용)
@app.get("/sitemap.xml")
def route_sitemap_index():
    target_path = "static/sitemaps/sitemap.xml"
    if os.path.exists(target_path):
        return FileResponse(target_path, media_type="application/xml")
    
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Sitemap Index Not Found. Please wait for generation.")


# 2. 서브 사이트맵 파일명 매칭 라우터 (https://api.integer7813.cloud/sitemap-static.xml 직접 대응용)
@app.get("/sitemap-{filename}.xml")
def route_sitemap_by_name(filename: str):
    target_path = f"static/sitemaps/sitemap-{filename}.xml"
    
    if os.path.exists(target_path):
        return FileResponse(target_path, media_type="application/xml")
    
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Sub Sitemap Not Found.")
# =========================================================================


# 🔥 정적 파일 서빙 매핑 주소 변경
app.mount("/static/sitemaps", StaticFiles(directory="static/sitemaps"), name="sitemaps")


@app.get("/")
def root():
    kst_time = datetime.now(ZoneInfo("Asia/Seoul"))
    return {
        "status": "success",
        "message": "--* API Server is running normally *--",
        "server_time_kst": kst_time.strftime("%Y-%m-%d %H:%M:%S KST")
    }