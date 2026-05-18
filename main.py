from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # 1. 미들웨어 임포트
from fastapi.staticfiles import StaticFiles          # 💡 정적 파일 서빙을 위해 추가
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from datetime import datetime
from zoneinfo import ZoneInfo
from contextlib import asynccontextmanager           # 💡 서버 기동 이벤트 바인딩을 위해 추가

# 💡 방금 전 만든 사이트맵 빌드 스크립트 기능 임포트
from generate_sitemaps import generate_sitemaps

# 리미터 정의
limiter = Limiter(key_func=get_remote_address)

from routes.random_university import router as random_router
from routes.search_university import router as search_router
from routes.locate_university import router as locate_router
from routes.univ_directory import router as univ_directory
from routes.majors import router as majors

# 💡 [핵심 추가] FastAPI 서버가 켜질 때 SQLite를 뒤져서 9만 개 사이트맵 파일을 구워내는 수명 주기(lifespan) 설정
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        generate_sitemaps()
    except Exception as e:
        print(f"❌ 서버 시작 중 사이트맵 생성 실패: {e}")
    yield

# 💡 lifespan 환경을 FastAPI 인스턴스에 주입합니다.
app = FastAPI(lifespan=lifespan)

# 2. CORS 설정 추가
# 특정 도메인만 허용하고 싶다면 ["http://localhost:3000"] 처럼 주소를 넣으세요.
origins = [
    "*",  # 모든 도메인에서의 접속을 허용 (테스트 단계에서 편리함)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,           # 허용할 도메인 리스트
    allow_credentials=True,          # 쿠키 포함 여부
    allow_methods=["*"],             # 모든 HTTP 메서드 허용 (GET, POST 등)
    allow_headers=["*"],             # 모든 HTTP 헤더 허용
)

# 리미터 연결 및 핸들러 등록
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(random_router)
app.include_router(search_router)
app.include_router(locate_router)
app.include_router(univ_directory)
app.include_router(majors)

# 💡 [핵심 추가] 생성된 사이트맵 XML 파일들을 고속 서빙하기 위한 정적 라우트 설정
# 이제 https://api.integer7813.cloud/api/sitemaps/sitemap.xml 주소로 마스터 지도를 받아볼 수 있습니다.
app.mount("/api/sitemaps", StaticFiles(directory="static/sitemaps"), name="sitemaps")

@app.get("/")
def root():
    kst_time = datetime.now(ZoneInfo("Asia/Seoul"))
    return {
        "status": "success",
        "message": "--* API Server is running normally *--",
        "server_time_kst": kst_time.strftime("%Y-%m-%d %H:%M:%S KST")
    }