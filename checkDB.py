import sqlite3

conn = sqlite3.connect("universities.db")
cursor = conn.cursor()

# 확인할 테이블 목록
tables = ["universities", "majors"]

for table in tables:
    print(f"=== Table: {table} ===")
    try:
        # 해당 테이블의 첫 번째 행 데이터 1개만 조회
        cursor.execute(f"SELECT * FROM {table} LIMIT 1")
        row = cursor.fetchone()  # 1개만 가져올 때는 fetchone()이 효율적입니다.

        if row:
            print(row)
        else:
            print(f"⚠️ '{table}' 테이블은 존재하지만 데이터가 없습니다.")

    except sqlite3.OperationalError:
        # 테이블 자체가 존재하지 않을 때 예외 처리
        print(f"❌ '{table}' 테이블이 데이터베이스에 존재하지 않습니다. 임포트 실패!")

    print("-" * 40)

conn.close()