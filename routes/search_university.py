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
    summary="학교명 키워드 검색",
    description="학교 이름을 키워드로 검색합니다. 결과는 실제 DB의 모든 상세 정보를 포함합니다.",
    response_description="검색어에 매칭되는 대학교 리스트 (전체 컬럼 포함)",
    responses={
        200: {
            "description": "검색 성공",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {
                            "request_size": 10,
                            "count": 1,
                            "items": [
                                {
                                    "학교구분": "대학원",
                                    "학교코드": 1568,
                                    "학교명": "상지대학교 대학원",
                                    "본분교": "본교",
                                    "학제": "일반대학원",
                                    "지역": "강원",
                                    "설립구분": "사립",
                                    "관련법령": "고등교육법",
                                    "법인명": "상지학원",
                                    "학교상태": "기존",
                                    "학교명(한자)": "尚志大学 大学院",
                                    "학교명(영문)": "Graduate School Sangji University",
                                    "주소": "강원특별자치도 원주시 상지대길 83 (우산동)",
                                    "영문주소": "83 Sangjidae-gil, Wonju-si, Gangwon-do",
                                    "중문주소": "83 Sangjidae-gil, Wonju-si, Gangwon-do",
                                    "우편번호": 26339,
                                    "학교개교일": "1955-06-10",
                                    "학교홈페이지": "www.sangji.ac.kr/grad/index.do",
                                    "총장명": "노병철",
                                    "학교대표번호": "033-730-0682",
                                    "학교대표팩스번호": "033-730-0684"
                                }
                            ]
                        }
                    }
                }
            }
        },
        404: {
            "description": "검색 결과 없음",
            "content": {
                "application/json": {
                    "example": {
                        "status": "error",
                        "message": "검색 결과가 없습니다.",
                        "data": {"count": 0, "items": []}
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
    size: Optional[int] = Query(10, ge=1, le=50, description="조회 개수") 
):
    start = time.perf_counter()
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        clean_name = name.strip()
        search_term = f"%{clean_name}%"

        # 실제 모든 컬럼을 가져오도록 쿼리 유지
        query = 'SELECT * FROM universities WHERE "학교명" LIKE ? LIMIT ?'
        cur.execute(query, (search_term, size))
        
        rows = cur.fetchall()
        
        process_time = round((time.perf_counter() - start) * 1000, 3)
        logger.info(f"Search for '{clean_name}' took {process_time}ms")

        # row 객체를 딕셔너리로 변환 (모든 컬럼 포함됨)
        results = [dict(row) for row in rows]
        
        if not results:
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
                    "request_size": size,
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