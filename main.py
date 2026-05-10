from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from datetime import datetime
from zoneinfo import ZoneInfo

# 1. 리미터 정의 (여기서 정의해야 다른 route에서 import 가능)
limiter = Limiter(key_func=get_remote_address)

from routes.random_university import router as random_router
from routes.search_university import router as search_router
from routes.locate_university import router as locate_router
from routes.univ_directory import router as univ_directory



app = FastAPI()

# 2. 리미터 연결 및 핸들러 등록
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(random_router)
app.include_router(search_router)
app.include_router(locate_router)
app.include_router(univ_directory)


@app.get("/")
def root():
    kst_time = datetime.now(ZoneInfo("Asia/Seoul"))

    return {
        "status": "success",
        "message": "--* API Server is running normally *--",
        "server_time_kst": kst_time.strftime("%Y-%m-%d %H:%M:%S KST")
    }