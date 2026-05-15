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

@router.get(
    "/locate-major",
    summary="학과 검색 (학과명/설립/구분/학제)", 
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
    size: int = Query(10, ge=1, le=100),
    page: int = Query(1, ge=1)
):
    start_time = time.perf_counter()
    
    if not any([q, founding, school_type, program]):
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

        where_clauses = ["1=1"]
        params = []

        # 1. 학과명 검색 -> 실제 컬럼명인 "학부·과(전공)명"으로 변경
        if q:
            where_clauses.append('"학부·과(전공)명" LIKE ?')
            params.append(f"%{q}%")
            
        # 2. 설립구분 필터 -> "설립구분"
        if founding:
            where_clauses.append('"설립구분" = ?')
            params.append(founding.value)
            
        # 3. 학교구분 필터 -> "학교구분"
        if school_type:
            where_clauses.append('"학교구분" = ?')
            params.append(school_type.value)
            
        # 4. 학제 필터 -> "학제"
        if program:
            where_clauses.append('"학제" = ?')
            params.append(program.value)

        where_str = " AND ".join(where_clauses)

        # 전체 개수 쿼리
        count_query = f'SELECT COUNT(*) FROM majors WHERE {where_str}'
        cur.execute(count_query, params)
        total_count = cur.fetchone()[0]

        # 데이터 페이징 조회 -> 실제 컬럼명인 "학교명" 및 "학부·과(전공)명"으로 정렬
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
        logger.error(f"Error: {str(e)}")
        return JSONResponse(
            status_code=500, 
            content={"status": "error", "message": "서버 내부 오류"}
        )
    finally:
        if conn: conn.close()

@router.get(
    "/major-metadata",
    summary="학과 검색용 드롭다운 메타데이터 조회",
    description="DB에 실제로 존재하는 '설립구분', '학교구분', '학제'의 목록을 중복 없이 추출하여 프론트엔드 드롭다운 컴포넌트 생성용으로 제공합니다.",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {
                            "founding_options": ["사립", "국립", "공립"],
                            "school_type_options": ["전문대학", "대학", "대학원"],
                            "program_options": ["기능대학", "대학교", "일반대학원", "특수대학원"]
                        }
                    }
                }
            }
        }
    }
)
def get_major_metadata():
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        # 1. DB에 실제로 존재하는 설립구분 중복 없이 추출
        cur.execute('SELECT DISTINCT "설립구분" FROM majors WHERE "설립구분" IS NOT NULL ORDER BY "설립구분" ASC')
        founding_list = [row[0] for row in cur.fetchall() if row[0]]

        # 2. DB에 실제로 존재하는 학교구분 중복 없이 추출
        cur.execute('SELECT DISTINCT "학교구분" FROM majors WHERE "학교구분" IS NOT NULL ORDER BY "학교구분" ASC')
        school_type_list = [row[0] for row in cur.fetchall() if row[0]]

        # 3. DB에 실제로 존재하는 학제 중복 없이 추출
        cur.execute('SELECT DISTINCT "학제" FROM majors WHERE "학제" IS NOT NULL ORDER BY "학제" ASC')
        program_list = [row[0] for row in cur.fetchall() if row[0]]

        return {
            "status": "success",
            "data": {
                "founding_options": founding_list,     
                "school_type_options": school_type_list, 
                "program_options": program_list         
            }
        }
    except Exception as e:
        logger.error(f"Metadata fetch error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "서버 내부 오류"}
        )
    finally:
        if conn: conn.close()