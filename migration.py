import pandas as pd
import sqlite3
import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_PATH = os.path.join(BASE_DIR, "data", "universities.csv")
DB_PATH = os.path.join(BASE_DIR, "data", "universities.db")

# =========================
# 1. CSV 로드
# =========================
df = pd.read_csv(
    FILE_PATH,
    encoding="utf-8-sig",
    engine="python",
    on_bad_lines="skip",
    sep=",",
    quotechar='"',
    skipinitialspace=True
)

# =========================
# 2. 컬럼명 클린 (완전 정규화)
# =========================
def clean_col(col):
    if isinstance(col, str):
        col = col.replace("\r", "").replace("\n", "")
        col = re.sub(r"\s+", "", col)   # 모든 공백 제거
        return col.strip()
    return col

df.columns = [clean_col(col) for col in df.columns]

# =========================
# 3. 값 클린 (텍스트 전체 정리)
# =========================
def clean_text(x):
    if isinstance(x, str):
        x = x.replace("\r", " ").replace("\n", " ")
        x = re.sub(r"\s+", " ", x)  # 연속 공백 1개로
        return x.strip()
    return x

df = df.apply(lambda col: col.map(clean_text))

# =========================
# 4. NaN → None (SQLite 안전)
# =========================
df = df.where(pd.notnull(df), None)

# =========================
# 5. SQLite 저장
# =========================
conn = sqlite3.connect(DB_PATH)

df.to_sql(
    "universities",
    conn,
    if_exists="replace",
    index=False
)

conn.close()

print("✅ Migration complete: FULL CLEAN PIPELINE DONE")