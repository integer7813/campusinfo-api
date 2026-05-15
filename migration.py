import os
import re
import pandas as pd
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "universities.db")

# =========================
# 0. 처리할 파일 및 테이블 정보 정의
# =========================
target_files = [
    {"file_name": "universities-260219.csv", "table_name": "universities"},
    {"file_name": "majors-260219.csv", "table_name": "majors"},
]


# =========================
# 클리닝 함수 정의
# =========================
def clean_col(col):
    """컬럼명 클린 (완전 정규화)"""
    if isinstance(col, str):
        col = col.replace("\r", "").replace("\n", "")
        col = re.sub(r"\s+", "", col)  # 모든 공백 제거
        return col.strip()
    return col


def clean_text(x):
    """값 클린 (텍스트 전체 정리)"""
    if isinstance(x, str):
        x = x.replace("\r", " ").replace("\n", " ")
        x = re.sub(r"\s+", " ", x)  # 연속 공백 1개로
        return x.strip()
    return x


# =========================
# 메인 마이그레이션 루프
# =========================
# SQLite 연결 (루프 밖에서 한 번만 연결)
conn = sqlite3.connect(DB_PATH)

for target in target_files:
    file_path = os.path.join(BASE_DIR, "data", target["file_name"])
    table_name = target["table_name"]

    print(f"🔄 Processing: {target['file_name']} -> DB Table: {table_name}")

    if not os.path.exists(file_path):
        print(f"⚠️ Warning: 파일이 존재하지 않습니다. 건너뜁니다 -> {file_path}")
        continue

    # 1. CSV 로드
    df = pd.read_csv(
        file_path,
        encoding="utf-8-sig",
        engine="python",
        on_bad_lines="skip",
        sep=",",
        quotechar='"',
        skipinitialspace=True,
    )

    # 2. 컬럼명 클린
    df.columns = [clean_col(col) for col in df.columns]

    # 3. 값 클린
    df = df.apply(lambda col: col.map(clean_text))

    # 4. NaN → None (SQLite 안전)
    df = df.where(pd.notnull(df), None)

    # 5. SQLite 저장
    df.to_sql(table_name, conn, if_exists="replace", index=False)

    print(f"   ↳ ✅ Saved to '{table_name}' table successfully.")

# 연결 종료
conn.close()

print("\n🚀 Migration complete: ALL FULL CLEAN PIPELINE DONE")