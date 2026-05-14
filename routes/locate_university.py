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

# --- Enum 정의 (기존과 동일) ---
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

@router.get("/locate-university")
@limiter.limit("60/minute") # 테스트를 위해 제한을 살짝 완화했습니다
def locate_university(
    request: Request,
    q: Optional[str] = Query(None, min_length=2),
    founding: Optional[FoundingType] = Query(None),
    school_type: Optional[SchoolType] = Query(None),
    program: Optional[ProgramType] = Query(None),
    size: int = Query(10), # 기본값 10
    page: int = Query(1)   # 페이지 파라미터 추가
):
    # 1. 조건이 하나도 없으면 빈 결과 반환
    if not any([q, founding, school_type, program]):
        return JSONResponse(
            content={"status": "success", "data": {"count": 0, "items": []}},
            media_type="application/json; charset=utf-8"
        )

    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        # 2. 기본 WHERE 절 및 파라미터 구성
        where_clauses = ["1=1"]
        params = []

        if q:
            where_clauses.append('"주소" LIKE ?')
            params.append(f"%{q}%")
        if founding:
            where_clauses.append('"설립구분" = ?')
            params.append(founding.value)
        if school_type:
            where_clauses.append('"학교구분" = ?')
            params.append(school_type.value)
        if program:
            where_clauses.append('"학제" = ?')
            params.append(program.value)

        where_str = " AND ".join(where_clauses)

        # 3. 전체 개수(Total Count) 조회 - 페이지네이션의 핵심
        count_query = f'SELECT COUNT(*) FROM universities WHERE {where_str}'
        cur.execute(count_query, params)
        total_count = cur.fetchone()[0]

        # 4. 실제 데이터 조회 (LIMIT & OFFSET 적용)
        offset = (page - 1) * size
        data_query = f'''
            SELECT * FROM universities 
            WHERE {where_str} 
            ORDER BY "학교명" ASC 
            LIMIT ? OFFSET ?
        '''
        
        # 데이터 쿼리용 파라미터 (조건 파라미터 + LIMIT + OFFSET)
        cur.execute(data_query, params + [size, offset])
        rows = cur.fetchall()
        results = [dict(row) for row in rows]
        
        return JSONResponse(
            content={
                "status": "success", 
                "data": {
                    "count": total_count, # ← 검색 결과의 '전체' 개수
                    "page": page,
                    "size": size,
                    "items": results      # ← 현재 페이지의 데이터 (size만큼)
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