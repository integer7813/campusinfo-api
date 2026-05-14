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

# --- 1. [검증 완료] 설립구분 Enum ---
class FoundingType(str, Enum):
    NATIONAL = "국립"
    NAT_CORP = "국립대법인"
    PUBLIC = "공립"
    PRIVATE = "사립"
    SPECIAL_CORP = "특별법법인"
    SPECIAL_NAT = "특별법국립"
    ETC = "기타"

# --- 2. [검증 완료] 학교구분 Enum ---
class SchoolType(str, Enum):
    UNIVERSITY = "대학"
    COLLEGE = "전문대학"
    GRAD_UNIV = "대학원대학"
    GRAD_SCHOOL = "대학원"

# --- 3. [검증 완료] 학제 Enum ---
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

# --- 4. 라우터 로직 ---
@router.get(
    "/locate-university",
    summary="대학교 검색 (주소/설립/구분/학제)", 
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {
                            "count": 1,
                            "page": 1,
                            "size": 10,
                            "items": [
                                {
                                    "학교구분": "대학",
                                    "학교코드": 3,
                                    "학교명": "강원대학교",
                                    "본분교": "본교",
                                    "학제": "대학교",
                                    "지역": "강원",
                                    "설립구분": "국립",
                                    "관련법령": "고등교육법",
                                    "법인명": "해당없음",
                                    "학교상태": "기존",
                                    "학교명(한자)": "江原大學校",
                                    "학교명(영문)": "Kangwon National University",
                                    "주소": "강원특별자치도 춘천시 강원대학길 1",
                                    "영문주소": "1, Gangwondaehak-gil, Chuncheon-si, Gangwon-do",
                                    "중문주소": "1, Gangwondaehak-gil, Chuncheon-si, Gangwon-do",
                                    "우편번호": 24341,
                                    "학교개교일": "1947-06-14",
                                    "학교홈페이지": "www.kangwon.ac.kr",
                                    "총장명": "김헌영",
                                    "학교대표번호": "033-250-6114",
                                    "학교대표팩스번호": "033-251-9556"
                                }
                            ]
                        }
                    }
                }
            }
        }
    }
)
@limiter.limit("20/minute")
def locate_university(
    request: Request,
    q: Optional[str] = Query(None, min_length=2),
    founding: Optional[FoundingType] = Query(None),
    school_type: Optional[SchoolType] = Query(None),
    program: Optional[ProgramType] = Query(None),
    size: int = Query(10, ge=1, le=100),
    page: int = Query(1, ge=1)
):
    start_time = time.perf_counter()
    
    # 1. 아무 조건 없을 때
    if not any([q, founding, school_type, program]):
        return JSONResponse(
            content={
                "status": "success",
                "data": {"count": 0, "items": []}
            },
            media_type="application/json; charset=utf-8"
        )

    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        # 조건절 생성
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

        # 2. 전체 개수(Total Count) 조회
        count_query = f'SELECT COUNT(*) FROM universities WHERE {where_str}'
        cur.execute(count_query, params)
        total_count = cur.fetchone()[0]

        # 3. 데이터 조회 (LIMIT & OFFSET 적용)
        offset = (page - 1) * size
        data_query = f'''
            SELECT * FROM universities 
            WHERE {where_str} 
            ORDER BY "학교명" ASC 
            LIMIT ? OFFSET ?
        '''
        
        cur.execute(data_query, params + [size, offset])
        rows = cur.fetchall()
        results = [dict(row) for row in rows]
        
        # 4. 결과 반환
        return JSONResponse(
            content={
                "status": "success", 
                "data": {
                    "count": total_count,
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