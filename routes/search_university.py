import time
import logging
from typing import Optional
from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse
from db import get_conn
from limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter()


# =========================================================================
# 1. 대학 필터 메타데이터 조회 API
# =========================================================================
@router.get(
    "/university/metadata",
    summary="대학 필터 메타데이터 조회",
    description="설립구분, 학교구분, 지역 목록 등 프론트엔드 드롭다운을 구성하기 위한 고유(DISTINCT) 리스트를 반환합니다.",
    responses={
        200: {
            "description": "메타데이터 조회 성공",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {
                            "founding_types": ["국립", "공립", "사립", "국립대법인"],
                            "school_types": ["대학", "전문대학", "대학원"],
                            "regions": ["강원", "경기", "서울", "인천"]
                        }
                    }
                }
            }
        },
        500: {
            "description": "서버 내부 오류",
            "content": {
                "application/json": {
                    "example": {"status": "error", "message": "메타데이터 로드 실패"}
                }
            }
        }
    }
)
def get_university_metadata():
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute('SELECT DISTINCT "설립구분" FROM universities WHERE "설립구분" IS NOT NULL AND "설립구분" != \'\'')
        founding_types = [row[0] for row in cur.fetchall()]

        cur.execute('SELECT DISTINCT "학교구분" FROM universities WHERE "학교구분" IS NOT NULL AND "학교구분" != \'\'')
        school_types = [row[0] for row in cur.fetchall()]

        cur.execute('SELECT DISTINCT "주소" FROM universities WHERE "주소" IS NOT NULL AND "주소" != \'\'')
        raw_addresses = cur.fetchall()
        
        region_set = set()
        for row in raw_addresses:
            addr = row[0].strip()
            if addr:
                first_word = addr.split()[0]
                refined_region = first_word[:2] if len(first_word) >= 2 else first_word
                region_set.add(refined_region)
        
        regions = sorted(list(region_set))

        return JSONResponse(
            content={
                "status": "success",
                "data": {
                    "founding_types": founding_types,
                    "school_types": school_types,
                    "regions": regions
                }
            }
        )
    except Exception as e:
        logger.error(f"Metadata fetch error: {str(e)}")
        return JSONResponse(status_code=500, content={"status": "error", "message": "메타데이터 로드 실패"})
    finally:
        if conn:
            conn.close()


# =========================================================================
# 2. 다중 필터 대응 대학 통합 검색 API
# =========================================================================
@router.get(
    "/search-university",
    summary="학교명 키워드 및 다중 필터 검색 (페이지네이션 지원)",
    description="학교 이름 키워드(선택) 및 설립구분, 학교구분, 지역 등의 필터를 조합하여 범위를 좁혀 검색합니다.",
    responses={
        200: {
            "description": "검색 성공 (데이터가 한 개 이상 존재할 때)",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success", 
                        "data": {
                            "page": 1, 
                            "request_size": 10, 
                            "total_count": 1, 
                            "items_count": 1, 
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
            "description": "일치하는 검색 결과 없음",
            "content": {
                "application/json": {
                    "example": {
                        "status": "error",
                        "message": "요청하신 조건에 합치하는 대학 검색 결과가 없습니다.",
                        "data": {
                            "total_count": 0,
                            "items": []
                        }
                    }
                }
            }
        },
        500: {
            "description": "서버 내부 오류",
            "content": {
                "application/json": {
                    "example": {"status": "error", "message": "서버 내부 오류"}
                }
            }
        }
    }
)
@limiter.limit("10/minute")
def search_university(
    request: Request, 
    name: Optional[str] = Query(None, description="검색할 학교 이름 (선택 항목)"),
    founding: Optional[str] = Query(None, description="설립구분 필터 (ex: 사립, 국립)"),
    school_type: Optional[str] = Query(None, description="학교구분 필터 (ex: 대학, 대학원)"),
    region: Optional[str] = Query(None, description="지역 필터 (ex: 강원, 서울, 경기)"),
    page: Optional[int] = Query(None, ge=1, description="페이지 번호"),
    size: Optional[int] = Query(None, ge=1, le=100, description="조회 개수")
):
    start = time.perf_counter()
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        # [동적 쿼리 조건 조립]
        where_clauses = []
        query_params = []

        if name and name.strip():
            clean_name = name.strip()
            where_clauses.append('"학교명" LIKE ?')
            query_params.append(f"%{clean_name}%")
        
        if founding and founding.strip():
            where_clauses.append('"설립구분" = ?')
            query_params.append(founding.strip())

        if school_type and school_type.strip():
            where_clauses.append('"학교구분" = ?')
            query_params.append(school_type.strip())

        if region and region.strip():
            where_clauses.append('"주소" LIKE ?')
            query_params.append(f"{region.strip()}%")

        where_stmt = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        # ✅ 1. 전체 개수 조회 (Total Count)
        count_query = f'SELECT COUNT(*) as total FROM universities{where_stmt}'
        cur.execute(count_query, tuple(query_params))
        total_result = cur.fetchone()
        total_count = total_result['total'] if total_result else 0

        # 결과가 아예 없으면 명세에 정의된 404 응답 양식으로 리턴
        if total_count == 0:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": "요청하신 조건에 합치하는 대학 검색 결과가 없습니다.",
                    "data": {"total_count": 0, "items": []}
                }
            )

        # ✅ 2. 페이지네이션 데이터 조회
        is_pagination = page is not None and size is not None
        
        if is_pagination:
            offset = (page - 1) * size
            data_query = f'SELECT * FROM universities{where_stmt} LIMIT ? OFFSET ?'
            data_params = tuple(query_params) + (size, offset)
        else:
            data_query = f'SELECT * FROM universities{where_stmt} LIMIT ?'
            data_params = tuple(query_params) + (500,)

        cur.execute(data_query, data_params)
        rows = cur.fetchall()
        results = [dict(row) for row in rows]
        
        process_time = round((time.perf_counter() - start) * 1000, 3)
        logger.info(f"Filtered Search (Total: {total_count}) took {process_time}ms")

        # ✅ 3. 성공 응답
        return JSONResponse(
            content={
                "status": "success",
                "data": {
                    "page": page if is_pagination else 1,
                    "request_size": size if is_pagination else len(results),
                    "total_count": total_count,
                    "items_count": len(results),
                    "items": results
                }
            },
            media_type="application/json; charset=utf-8"
        )

    except Exception as e:
        logger.error(f"Database error during filtered search: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "서버 내부 오류"}
        )
    finally:
        if conn:
            conn.close()