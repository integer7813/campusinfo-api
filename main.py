from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # 1. 미들웨어 임포트
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from datetime import datetime
from zoneinfo import ZoneInfo

# 리미터 정의
limiter = Limiter(key_func=get_remote_address)

from routes.random_university import router as random_router
from routes.search_university import router as search_router
from routes.locate_university import router as locate_router
from routes.univ_directory import router as univ_directory
from routes.majors import router as majors

app = FastAPI()

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

@app.get("/")
def root():
    kst_time = datetime.now(ZoneInfo("Asia/Seoul"))
    return {
        "status": "success",
        "message": "--* API Server is running normally *--",
        "server_time_kst": kst_time.strftime("%Y-%m-%d %H:%M:%S KST")
    }