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
                            "school_types": ["대학교", "전문대학", "대학원"],
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
        founding_types = [row[0].strip() for row in cur.fetchall() if row[0]]

        cur.execute('SELECT DISTINCT "학제" FROM universities WHERE "학제" IS NOT NULL AND "학제" != \'\'')
        school_types = [row[0].strip() for row in cur.fetchall() if row[0]]

        cur.execute('SELECT DISTINCT "지역" FROM universities WHERE "지역" IS NOT NULL AND "지역" != \'\'')
        regions = sorted([row[0].strip() for row in cur.fetchall() if row[0]])

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
# 2. 다중 필터 대응 대학 통합 검색 API (수정 및 Docs 보강 완료)
# =========================================================================
@router.get(
    "/search-university",
    summary="학교명 키워드 및 다중 필터 검색 (페이지네이션 지원)",
    description="""
    학교 이름 키워드(선택) 및 설립구분, 학교구분(학제), 지역 등의 필터를 조합하여 검색합니다.
    
    - **페이지네이션 피드백 보정**: `page`와 `size` 파라미터가 누락되거나 빈 값으로 들어오더라도 시스템 기본값(1페이지, 15개)을 강제 적용하여 프론트엔드 페이지네이션이 고정되거나 깨지는 현상을 원천 방지합니다.
    - **HTTP 200 상태코드 일관성 유지**: 검색 결과가 0곳일 때 404 에러 리턴 대신, 200 OK와 함께 빈 배열(`[]`)을 반환하여 프론트엔드가 비정상 크래시(API Fetch Error) 없이 안정적으로 '결과가 없습니다' UI를 그리도록 처리합니다.
    """,
    responses={
        200: {
            "description": "검색 조회 성공 (데이터가 존재하지 않는 경우에도 빈 리스트와 함께 200 성공을 반환하여 클라이언트 연동 안정성 확보)",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {
                            "page": 1,
                            "request_size": 15,
                            "total_count": 145,
                            "items_count": 15,
                            "items": [
                                {
                                    "학교명": "서울대학교 대학원",
                                    "학제": "일반대학원",
                                    "설립구분": "국립대법인",
                                    "지역": "서울",
                                    "소재지": "서울특별시 관악구 관악로 1"
                                }
                            ]
                        }
                    }
                }
            }
        },
        500: {
            "description": "데이터베이스 조회 또는 서버 로직 수행 중 오류 발생",
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
    name: Optional[str] = Query(None, description="검색할 학교 이름 또는 학과 연관 키워드 (선택 항목)"),
    founding: Optional[str] = Query(None, description="설립구분 필터 (ex: 사립, 국립, 국립대법인 등)"),
    school_type: Optional[str] = Query(None, description="학교구분/학제 필터 (ex: 일반대학원, 전문대학원, 특수대학원 등)"),
    region: Optional[str] = Query(None, description="지역 필터 (ex: 서울, 경기, 부산, 강원 등)"),
    # 🎯 [Docs & 기능 수정] 프론트엔드 연동 안정성을 위해 디폴트 기본값을 명시적으로 강제 매핑합니다.
    page: int = Query(1, ge=1, description="페이지 번호 (디폴트: 1)"),
    size: int = Query(15, ge=1, le=100, description="한 페이지당 조회 개수 (디폴트: 15)")
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

        if school_type and school_type.strip():
            where_clauses.append('"학제" = ?')
            query_params.append(school_type.strip())

        if region and region.strip():
            where_clauses.append('"지역" = ?')
            query_params.append(region.strip())

        where_stmt = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        # 1. 전체 개수 조회
        count_query = f'SELECT COUNT(*) as total FROM universities{where_stmt}'
        cur.execute(count_query, tuple(query_params))
        total_result = cur.fetchone()
        total_count = total_result['total'] if total_result else 0

        # 🎯 [핵심 버그 수정 1] 
        # 검색 결과가 0개일 때 404 에러를 던지면 Next.js fetch가 res.ok=false 판정을 받아 화면 전체가 뻗습니다.
        # 정상적으로 데이터가 0개인 상태의 JSON 구조를 200 OK로 반환하여 프론트엔드가 '결과 없음' UI를 평화롭게 그리도록 유도합니다.
        if total_count == 0:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "data": {
                        "page": page,
                        "request_size": size,
                        "total_count": 0,
                        "items_count": 0,
                        "items": []
                    }
                }
            )

        # 2. 페이지네이션 데이터 조회
        # 🎯 [핵심 버그 수정 2] Optional 구조를 제거하고 page, size 무조건 보장 처리로 변경
        offset = (page - 1) * size
        data_query = f'SELECT * FROM universities{where_stmt} LIMIT ? OFFSET ?'
        data_params = tuple(query_params) + (size, offset)

        cur.execute(data_query, data_params)
        rows = cur.fetchall()
        results = [dict(row) for row in rows]
        
        process_time = round((time.perf_counter() - start) * 1000, 3)
        logger.info(f"Filtered Search (Total: {total_count}) took {process_time}ms")

        return JSONResponse(
            content={
                "status": "success",
                "data": {
                    "page": page,
                    "request_size": size,
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