import sqlite3
import os

# 현재 파일(db.py)이 있는 위치를 기준으로 데이터베이스 파일 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "universities.db")

def get_conn():
    """
    데이터베이스 연결 객체를 생성하여 반환합니다.
    """
    try:
        # 데이터베이스 연결 (파일이 없으면 새로 생성됨)
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        
        # 결과를 딕셔너리처럼 다룰 수 있게 설정 (row['column_name'] 가능)
        # 이 설정이 있어야 원래 코드의 dict(row)가 정상 작동합니다.
        conn.row_factory = sqlite3.Row
        
        return conn
    except sqlite3.Error as e:
        print(f"데이터베이스 연결 에러: {e}")
        raise e
