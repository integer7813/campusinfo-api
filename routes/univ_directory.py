# -*- coding: utf-8 -*-
import time
import logging
from typing import Optional
from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse
from db import get_conn
from limiter import limiter  # 기존에 쓰시던 limiter 임포트

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get(
    "/univ-directory",
    summary="전국 대학교 전화번호부 (연락처/팩스/홈페이지)",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": [
                            {
                                "학교명": "강원대학교",
                                "지역": "강원",
                                "총장명": "김헌영",
                                "학교대표번호": "033-250-6114",
                                "학교대표팩스번호": "033-251-9556",
                                "학교홈페이지": "www.kangwon.ac.kr",
                                "주소": "강원특별자치도 춘천시 강원대학길 1"
                            }
                        ]
                    }
                }
            }
        }
    }
)
@limiter.limit("15/minute")  # 1분에 15번까지만 허용 (매크로 방지)
def get_univ_directory(
    request: Request,
    name: str = Query(..., min_length=2, description="학교명 키워드 (예: 강원, 상지)"),
    region: Optional[str] = Query(None, description="특정 지역 필터 (예: 서울, 강원)")
):
    """
    학교명으로 검색하여 대표번호, 팩스번호, 홈페이지를 빠르게 찾을 수 있는 '전화번호부' 서비스입니다.
    """
    start_time = time.perf_counter()
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        
        query = """
            SELECT "학교명", "지역", "총장명", "학교대표번호", "학교대표팩스번호", "학교홈페이지", "주소"
            FROM universities 
            WHERE "학교명" LIKE ?
        """
        params = [f"%{name}%"]
        
        if region:
            query += ' AND "지역" = ?'
            params.append(region)
            
        query += ' ORDER BY "학교명" ASC'
        
        cur.execute(query, params)
        rows = cur.fetchall()
        results = [dict(row) for row in rows]
        
        duration = round((time.perf_counter() - start_time) * 1000, 2)
        logger.info(f"[Directory] Search: '{name}' | Found: {len(results)} | {duration}ms")

        return JSONResponse(
            content={
                "status": "success",
                "data": results
            },
            media_type="application/json; charset=utf-8"
        )

    except Exception as e:
        logger.error(f"Directory API Error: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "서버 내부 오류"}
        )
    finally:
        if conn:
            conn.close()