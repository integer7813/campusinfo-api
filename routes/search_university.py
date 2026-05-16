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
# 1. 대학 필터 메타데이터 조회 API (수정 완료)
# =========================================================================
@router.get(
    "/university/metadata",
    summary="대학 필터 메타데이터 조회",
    description="설립구분, 학교구분(학제), 지역 목록 등 프론트엔드 드롭다운을 구성하기 위한 고유(DISTINCT) 리스트를 반환합니다.",
    responses={
        200: {
            "description": "메타데이터 조회 성공",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {
                            "founding_types": ["국립", "공립", "사립", "국립대법인"],
                            "school_types": ["대학교", "전문대학", "대학원"],  # 학제 컬럼 데이터 기반
                            "regions": ["강원", "경기", "서울", "인천"]        # 지역 컬럼 데이터 기반
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

        # 1. 설립구분 DISTINCT 추출
        cur.execute('SELECT DISTINCT "설립구분" FROM universities WHERE "설립구분" IS NOT NULL AND "설립구분" != \'\'')
        founding_types = [row[0].strip() for row in cur.fetchall() if row[0]]

        # 2. 학교구분 DISTINCT 추출 (DB의 '학제' 컬럼 매핑)
        cur.execute('SELECT DISTINCT "학제" FROM universities WHERE "학제" IS NOT NULL AND "학제" != \'\'')
        school_types = [row[0].strip() for row in cur.fetchall() if row[0]]

        # 3. 지역 DISTINCT 추출 (DB의 '지역' 컬럼을 바로 사용하도록 수정)
        cur.execute('SELECT DISTINCT "지역" FROM universities WHERE "지역" IS NOT NULL AND "지역" != \'\'')
        regions = sorted([row[0].strip() for row in cur.fetchall() if row[0]])

        return JSONResponse(
            content={
                "status": "success",
                "data": {
                    "founding_types": founding_types,
                    "school_types": school_types,  # 프론트엔드 key 유지를 위해 변수명은 유지
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
# 2. 다중 필터 대응 대학 통합 검색 API (수정 완료)
# =========================================================================
@router.get(
    "/search-university",
    summary="학교명 키워드 및 다중 필터 검색 (페이지네이션 지원)",
    description="학교 이름 키워드(선택) 및 설립구분, 학교구분(학제), 지역 등의 필터를 조합하여 범위를 좁혀 검색합니다.",
)
@limiter.limit("10/minute")
def search_university(
    request: Request, 
    name: Optional[str] = Query(None, description="검색할 학교 이름 (선택 항목)"),
    founding: Optional[str] = Query(None, description="설립구분 필터 (ex: 사립, 국립)"),
    school_type: Optional[str] = Query(None, description="학교구분 필터 (ex: 대학교, 전문대학)"), # 학제 필터로 매핑됨
    region: Optional[str] = Query(None, description="지역 필터 (ex: 강원, 서울, 경기)"),
    page: Optional[int] = Query(None, ge=1, description="페이지 번호"),
    size: Optional[int] = Query(None, ge=1, le=100, description="조회 개수")
):
    start = time.perf_counter()
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        where_clauses = []
        query_params = []

        if name and name.strip():
            clean_name = name.strip()
            where_clauses.append('"학교명" LIKE ?')
            query_params.append(f"%{clean_name}%")
        
        if founding and founding.strip():
            where_clauses.append('"설립구분" = ?')
            query_params.append(founding.strip())

        # 학교구분 검색 시 실제 DB 컬럼인 "학제"로 검색하도록 변경
        if school_type and school_type.strip():
            where_clauses.append('"학제" = ?')
            query_params.append(school_type.strip())

        # 지역 검색 시 주소 LIKE 대신 "지역" 컬럼으로 정확하게 매칭하도록 변경
        if region and region.strip():
            where_clauses.append('"지역" = ?')
            query_params.append(region.strip())

        where_stmt = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        # 1. 전체 개수 조회
        count_query = f'SELECT COUNT(*) as total FROM universities{where_stmt}'
        cur.execute(count_query, tuple(query_params))
        total_result = cur.fetchone()
        total_count = total_result['total'] if total_result else 0

        if total_count == 0:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": "요청하신 조건에 합치하는 대학 검색 결과가 없습니다.",
                    "data": {"total_count": 0, "items": []}
                }
            )

        # 2. 페이지네이션 데이터 조회
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