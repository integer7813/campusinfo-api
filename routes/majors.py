import time
import logging
from enum import Enum
from typing import Optional
from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse
from db import get_conn
from limiter import limiter

logger = logging.getLogger(__name__)
router = APIRouter()

# --- [Enum 정의 영역] ---
class FoundingType(str, Enum):
    NATIONAL = "국립"
    NAT_CORP = "국립대법인"
    PUBLIC = "공립"
    PRIVATE = "사립"
    SPECIAL_CORP = "특별법법인"
    SPECIAL_NAT = "특별법국립"
    ETC = "기타"

class SchoolType(str, Enum):
    UNIVERSITY = "대학"
    COLLEGE = "전문대학"
    GRAD_UNIV = "대학원대학"
    GRAD_SCHOOL = "대학원"

class ProgramType(str, Enum):
    UNIV = "대학교"
    EDU_UNIV = "교육대학"
    IND_UNIV = "산업대학"
    BROADCAST = "방송통신대학"
    TECH_UNIV = "기술대학"
    MISC_UNIV = "각종학교(대학)"
    CYBER_UNIV = "사이버대학(대학)"
    COLLEGE = "전문대학"
    CYBER_COLLEGE = "사이버대학(전문)"
    POLYTECHNIC = "기능대학"
    GRAD_PROF = "전문대학원"
    GRAD_SPEC = "특수대학원"
    GRAD_GEN = "일반대학원"


# =========================================================================
# 1. 학과 통합 검색 API (지역 필터 완벽 연동)
# =========================================================================
@router.get(
    "/locate-major",
    summary="학과 검색 (학과명/설립/구분/학제/지역 정교화)", 
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {
                            "total_count": 1,
                            "page": 1,
                            "size": 10,
                            "items": []
                        }
                    }
                }
            }
        }
    }
)
@limiter.limit("20/minute")
def locate_major(
    request: Request,
    q: Optional[str] = Query(None, min_length=2, description="검색할 학과명 (예: 컴퓨터)"),
    founding: Optional[FoundingType] = Query(None, description="설립구분 (국립/사립 등)"),
    school_type: Optional[SchoolType] = Query(None, description="학교구분 (대학/전문대학 등)"),
    program: Optional[ProgramType] = Query(None, description="학제 (일반대학원/특수대학원 등)"),
    region: Optional[str] = Query(None, description="소재지 지역 필터 (예: 서울, 강원, 경기)"),  
    size: int = Query(10, ge=1, le=100),
    page: int = Query(1, ge=1)
):
    start_time = time.perf_counter()
    
    # 가드 조건 체크 대상 확장
    if not any([q, founding, school_type, program, region]):
        return JSONResponse(
            content={
                "status": "success",
                "data": {"total_count": 0, "page": page, "size": size, "items": []}
            },
            media_type="application/json; charset=utf-8"
        )

    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        # 원본 데이터 기준 운영 중인 학과 상태만 필터링
        where_clauses = ['"학과상태" = \'기존\'']
        params = []

        # 1. 학부·과(전공)명 조건 추가
        if q and q.strip():
            where_clauses.append('"학부·과(전공)명" LIKE ?')
            params.append(f"%{q.strip()}%")
            
        # 2. 설립구분 조건 추가
        if founding:
            where_clauses.append('"설립구분" = ?')
            params.append(founding.value)
            
        # 3. 학교구분 조건 추가
        if school_type:
            where_clauses.append('"학교구분" = ?')
            params.append(school_type.value)
            
        # 4. 학제 조건 추가
        if program:
            where_clauses.append('"학제" = ?')
            params.append(program.value)

        # 5. 🎯 정교화된 소재지(지역) 조건 추가
        # 데이터 적재 환경에 따라 공백이 남아있을 수 있으므로 TRIM 처리하여 칼럼 바인딩
        if region and region.strip():
            where_clauses.append('TRIM("소재지") = ?')
            params.append(region.strip())

        where_str = " AND ".join(where_clauses)

        # 📊 전체 개수 카운트 쿼리 실행
        count_query = f'SELECT COUNT(*) FROM majors WHERE {where_str}'
        cur.execute(count_query, params)
        total_count = cur.fetchone()[0]

        # 📑 페이징 및 정렬 조건 결합하여 조회
        offset = (page - 1) * size
        data_query = f'''
            SELECT * FROM majors 
            WHERE {where_str} 
            ORDER BY "학교명" ASC, "학부·과(전공)명" ASC
            LIMIT ? OFFSET ?
        '''
        
        cur.execute(data_query, params + [size, offset])
        rows = cur.fetchall()
        results = [dict(row) for row in rows]
        
        process_time = round((time.perf_counter() - start_time) * 1000, 3)
        logger.info(f"Major Search (Region: {region} | Total: {total_count}) took {process_time}ms")

        return JSONResponse(
            content={
                "status": "success", 
                "data": {
                    "total_count": total_count,
                    "page": page,
                    "size": size,
                    "items": results
                }
            },
            media_type="application/json; charset=utf-8"
        )

    except Exception as e:
        logger.error(f"Major search error: {str(e)}")
        return JSONResponse(
            status_code=500, 
            content={"status": "error", "message": "서버 내부 오류"}
        )
    finally:
        if conn: conn.close()


# =========================================================================
# 2. 학과 검색용 드롭다운 메타데이터 조회 API (소재지 중복제거 정렬 반영)
# =========================================================================
@router.get(
    "/major-metadata",
    summary="학과 검색용 드롭다운 메타데이터 조회",
    description="DB에 실제로 존재하는 '설립구분', '학교구분', '학제', '소재지(지역)' 목록을 제공합니다.",
)
def get_major_metadata():
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        # 1. 설립구분 리스트 추출
        cur.execute('SELECT DISTINCT "설립구분" FROM majors WHERE "학과상태" = \'기존\' AND "설립구분" IS NOT NULL AND "설립구분" != \'\' ORDER BY "설립구분" ASC')
        founding_list = [row[0].strip() for row in cur.fetchall() if row[0]]

        # 2. 학교구분 리스트 추출
        cur.execute('SELECT DISTINCT "학교구분" FROM majors WHERE "학과상태" = \'기존\' AND "학교구분" IS NOT NULL AND "학교구분" != \'\' ORDER BY "학교구분" ASC')
        school_type_list = [row[0].strip() for row in cur.fetchall() if row[0]]

        # 3. 학제 리스트 추출
        cur.execute('SELECT DISTINCT "학제" FROM majors WHERE "학과상태" = \'기존\' AND "학제" IS NOT NULL AND "학제" != \'\' ORDER BY "학제" ASC')
        program_list = [row[0].strip() for row in cur.fetchall() if row[0]]

        # 4. 🎯 소재지 리스트 정교화 추출
        # 공백이나 특수 가공 문제 방지를 위해 데이터 클렌징 쿼리 적용
        cur.execute('''
            SELECT DISTINCT TRIM("소재지") 
            FROM majors 
            WHERE "학과상태" = '기존' 
              AND "소재지" IS NOT NULL 
              AND "소재지" != '' 
            ORDER BY TRIM("소재지") ASC
        ''')
        region_list = [row[0].strip() for row in cur.fetchall() if row[0]]

        return JSONResponse(
            content={
                "status": "success",
                "data": {
                    "founding_options": founding_list,     
                    "school_type_options": school_type_list, 
                    "program_options": program_list,
                    "region_options": region_list  
                }
            },
            media_type="application/json; charset=utf-8"
        )
    except Exception as e:
        logger.error(f"Major metadata fetch error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "서버 내부 오류"}
        )
    finally:
        if conn: conn.close()