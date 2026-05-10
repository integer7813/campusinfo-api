# -*- coding: utf-8 -*-
import time
import logging
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from db import get_conn
from limiter import limiter  # limiter 객체 임포트 필수

# 로그 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get(
    "/random-university",
    summary="랜덤 대학교 정보 조회",
    description="전체 데이터베이스에서 무작위로 1개의 학교를 선택하여 상세 정보를 반환합니다.",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {
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
                    }
                }
            }
        },
        404: {
            "content": {
                "application/json": {
                    "example": {
                        "status": "error",
                        "message": "데이터베이스에 등록된 대학교가 없습니다."
                    }
                }
            }
        },
        500: {
            "content": {
                "application/json": {
                    "example": {
                        "status": "error",
                        "message": "서버 내부 오류가 발생했습니다."
                    }
                }
            }
        }
    }
)
@limiter.limit("60/minute") # 1분에 60회 제한 적용
def random_university(request: Request):
    """
    SQLite의 RANDOM() 함수와 OFFSET을 활용하여 
    전체 대학교 행 중 하나를 무작위로 추출합니다.
    """
    start = time.perf_counter()
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        # 랜덤하게 1개의 행을 가져오는 쿼리 (OFFSET 방식)
        cur.execute("""
            SELECT * FROM universities
            LIMIT 1 OFFSET (
                ABS(RANDOM()) % (SELECT COUNT(*) FROM universities)
            )
        """)

        row = cur.fetchone()

        # 성능 측정 및 로그 기록
        process_time = round((time.perf_counter() - start) * 1000, 3)
        logger.info(f"Random university fetch took {process_time}ms")

        if row is None:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": "데이터베이스에 등록된 대학교가 없습니다."
                }
            )

        # 결과 반환 (표준 규격: status, data)
        return JSONResponse(
            content={
                "status": "success",
                "data": dict(row)
            },
            media_type="application/json; charset=utf-8"
        )

    except Exception as e:
        logger.error(f"Random University API Error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "서버 내부 오류가 발생했습니다."
            }
        )
    finally:
        if conn:
            conn.close()