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
    description="학교 이름을 키워드로 검색합니다. 전체 결과 개수와 페이지네이션 데이터를 반환합니다.",
    responses={
        200: {
            "description": "검색 성공",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success", 
                        "data": {
                            "page": 1, 
                            "request_size": 10, 
                            "total_count": 450, # ✅ 추가된 필드
                            "items_count": 10, 
                            "items": []
                        }
                    }
                }
            }
        }
    }
)
@limiter.limit("10/minute")
def search_university(
    request: Request, 
    name: str = Query(..., min_length=2, description="검색할 학교 이름"),
    page: Optional[int] = Query(None, ge=1, description="페이지 번호"),
    size: Optional[int] = Query(None, ge=1, le=100, description="조회 개수")
):
    start = time.perf_counter()
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        clean_name = name.strip()
        search_term = f"%{clean_name}%"

        # ✅ 1. 전체 개수 조회 (Total Count)
        # LIMIT에 상관없이 검색 조건에 맞는 모든 데이터의 수를 가져옵니다.
        count_query = 'SELECT COUNT(*) as total FROM universities WHERE "학교명" LIKE ?'
        cur.execute(count_query, (search_term,))
        total_result = cur.fetchone()
        total_count = total_result['total'] if total_result else 0

        # 결과가 아예 없으면 조기 리턴
        if total_count == 0:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": f"'{clean_name}'에 대한 검색 결과가 없습니다.",
                    "data": {"total_count": 0, "items": []}
                }
            )

        # ✅ 2. 페이지네이션 데이터 조회
        is_pagination = page is not None and size is not None
        
        if is_pagination:
            offset = (page - 1) * size
            query = 'SELECT * FROM universities WHERE "학교명" LIKE ? LIMIT ? OFFSET ?'
            params = (search_term, size, offset)
        else:
            # 페이지네이션 정보가 없으면 안전하게 최대 500개만 반환
            query = 'SELECT * FROM universities WHERE "학교명" LIKE ? LIMIT ?'
            params = (search_term, 500) 

        cur.execute(query, params)
        rows = cur.fetchall()
        results = [dict(row) for row in rows]
        
        process_time = round((time.perf_counter() - start) * 1000, 3)
        logger.info(f"Search for '{clean_name}' (Total: {total_count}) took {process_time}ms")

        # ✅ 3. 성공 응답 (total_count 포함)
        return JSONResponse(
            content={
                "status": "success",
                "data": {
                    "page": page if is_pagination else 1,
                    "request_size": size if is_pagination else len(results),
                    "total_count": total_count, # 전체 검색 결과 총합
                    "items_count": len(results), # 현재 페이지 아이템 개수
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