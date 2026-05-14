import time
import logging
from typing import Optional
from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse
from db import get_conn
from limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get(
    "/search-university",
    summary="학교명 키워드 검색 (페이지네이션 지원)",
    description="학교 이름을 키워드로 검색합니다. page와 size 파라미터를 통해 페이지네이션이 가능합니다.",
    responses={
        200: {
            "description": "검색 성공",
            "content": {"application/json": {"example": {"status": "success", "data": {"page": 1, "size": 10, "count": 1, "items": []}}}}
        },
        404: {
            "description": "검색 결과 없음",
            "content": {"application/json": {"example": {"status": "error", "message": "검색 결과가 없습니다.", "data": {"count": 0, "items": []}}}}
        }
    }
)
@limiter.limit("10/minute")
def search_university(
    request: Request, 
    name: str = Query(..., min_length=2, description="검색할 학교 이름"),
    page: Optional[int] = Query(None, ge=1, description="페이지 번호"), # None 허용
    size: Optional[int] = Query(None, ge=1, le=100, description="조회 개수") # None 허용
):
    start = time.perf_counter()
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        clean_name = name.strip()
        search_term = f"%{clean_name}%"

        # 1. 페이지네이션 로직 처리
        # page나 size가 하나라도 없으면 전체 검색(혹은 매우 큰 제한)으로 간주
        is_pagination = page is not None and size is not None
        
        if is_pagination:
            offset = (page - 1) * size
            # LIMIT와 OFFSET을 사용하는 쿼리
            query = 'SELECT * FROM universities WHERE "학교명" LIKE ? LIMIT ? OFFSET ?'
            params = (search_term, size, offset)
        else:
            # 페이지네이션 정보가 없으면 전체(최대 500개로 안전제한)를 가져옴
            query = 'SELECT * FROM universities WHERE "학교명" LIKE ? LIMIT ?'
            params = (search_term, 500) 

        cur.execute(query, params)
        rows = cur.fetchall()
        
        process_time = round((time.perf_counter() - start) * 1000, 3)
        logger.info(f"Search for '{clean_name}' (Page: {page}, Size: {size}) took {process_time}ms")

        results = [dict(row) for row in rows]
        
        if not results:
            # 클라이언트 요구사항에 따라 404 대신 유연하게 200에 빈 배열을 줄 수도 있지만, 
            # 기존 로직을 유지하여 404를 반환합니다.
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": f"'{clean_name}'에 대한 검색 결과가 없습니다.",
                    "data": {"count": 0, "items": []}
                }
            )

        return JSONResponse(
            content={
                "status": "success",
                "data": {
                    "page": page if is_pagination else 1,
                    "request_size": size if is_pagination else len(results),
                    "count": len(results),
                    "items": results
                }
            },
            media_type="application/json; charset=utf-8"
        )

    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "서버 내부 오류"}
        )
    finally:
        if conn:
            conn.close()