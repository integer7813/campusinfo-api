import sqlite3

conn = sqlite3.connect("universities.db")
cursor = conn.cursor()

# majors 테이블의 정보(컬럼명 포함) 가져오기
cursor.execute("PRAGMA table_info(majors)")
columns = cursor.fetchall()

print("--- [majors] 테이블의 실제 컬럼명 목록 ---")
for col in columns:
    print(f"인덱스 {col[0]}: {col[1]}") # col[1]이 실제 컬럼 이름입니다.

conn.close()