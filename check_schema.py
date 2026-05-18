import sqlite3
from db import get_conn

def check_majors_schema():
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        
        # 1. 테이블 컬럼 정보 조회
        cur.execute("PRAGMA table_info(majors);")
        columns = cur.fetchall()
        
        print("\n=== [majors 테이블 컬럼 목록] ===")
        for col in columns:
            # col[1]: 컬럼명, col[2]: 데이터 타입
            print(f"- 컬럼명: {col[1]} ({col[2]})")
            
        # 2. 데이터 샘플을 통해 어떤 상태 값들이 들어있는지 확인
        print("\n=== [학과상태 데이터 종류] ===")
        try:
            cur.execute('SELECT DISTINCT "학과상태" FROM majors')
            print([row[0] for row in cur.fetchall() if row[0]])
        except Exception:
            print("학과상태 컬럼이 없거나 조회 실패")

        print("\n=== [학교/운영 상태 관련 예상 컬럼 값 확인] ===")
        # 학교 상태나 폐교 여부를 유추할 수 있는 컬럼이 있는지 샘플 상위 1개 출력
        cur.execute('SELECT * FROM majors LIMIT 1')
        row = cur.fetchone()
        if row:
            print("샘플 데이터 컬럼 key 목록:")
            print(list(dict(row).keys()))
            
    except Exception as e:
        print(f"오류 발생: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    check_majors_schema()