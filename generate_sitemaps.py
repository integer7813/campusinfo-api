# -*- coding: utf-8 -*-
# generate_sitemaps.py
import sqlite3
import urllib.parse
import os

DB_PATH = "universities.db"
OUTPUT_DIR = "./static/sitemaps"
BASE_URL = "https://integer7813.cloud"

def clean_major_name(raw_name):
    """
    디비에서 주는 대로 안 만들어서 깨지는 문제를 원천 차단하기 위해
    글자 수정 없이 100% 원본 그대로 리턴합니다.
    """
    if not raw_name:
        return None
    
    name = raw_name.strip()
    
    if len(name) < 2:
        return None
    return name

def generate_sitemaps():
    print("🚀 [완전체 통합] sitemap-static.xml 파일 하나에 모든 URL 빌드 시작...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 단 한 장의 사이트맵에 다 쑤셔 넣을 거대한 주머니
    all_urls = []

    # =========================================================================
    # [1] 기본 고정 정적 페이지용 URL 수집
    # =========================================================================
    base_routes = ['', '/about', '/contact', '/privacy', '/terms', '/future', '/univ/list']
    for route in base_routes:
        priority = '1.0' if route == '' else '0.8'
        all_urls.append(
            f"<url><loc>{BASE_URL}{route}</loc><changefreq>daily</changefreq><priority>{priority}</priority></url>"
        )
    print(f"✅ 1. 기본 정적 페이지 URL 수집 완료 ({len(base_routes)}개)")

    # DB 연결
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # =========================================================================
    # [2] 전국 대학 상세 페이지용 URL 수집 (폐교 제외)
    # =========================================================================
    try:
        cursor.execute("SELECT DISTINCT [학교명] FROM universities WHERE [학교명] NOT LIKE '%(폐교)%' AND [학교명] IS NOT NULL")
        univs = sorted(list(set([row[0].strip() for row in cursor.fetchall() if row[0]])))
        
        for u in univs:
            encoded_univ = urllib.parse.quote(u)
            all_urls.append(
                f"<url><loc>{BASE_URL}/univ/{encoded_univ}</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>"
            )
        print(f"✅ 2. 전국 대학 상세 페이지 URL 수집 완료 (총 {len(univs)}개 대학)")
    except Exception as e:
        print("❌ 대학 테이블([universities]) 조회 실패:", e)

    # =========================================================================
    # [3] 🎯 전공명 키워드 리스트용 URL 수집 (괄호, 특수문자 원본 100% 보존)
    # =========================================================================
    try:
        cursor.execute("""
            SELECT DISTINCT [학부·과(전공)명] 
            FROM majors 
            WHERE [학과상태] IN ('기존', '신설', '변경[기존]', '통합[기존]', '분리[기존]')
              AND [학교명] NOT LIKE '%(폐교)%'
              AND [학부·과(전공)명] IS NOT NULL
        """)
        
        processed_majors = set()
        for row in cursor.fetchall():
            raw_val = row[0]
            cleaned = clean_major_name(raw_val)
            if cleaned:
                processed_majors.add(cleaned)
        
        cleaned_majors = sorted(list(processed_majors))

        for major in cleaned_majors:
            encoded_major = urllib.parse.quote(major)
            all_urls.append(
                f"<url><loc>{BASE_URL}/major/list/name/{encoded_major}</loc>"
                f"<changefreq>weekly</changefreq><priority>0.6</priority></url>"
            )
        print(f"✅ 3. 전공명 키워드 리스트 URL 수집 완료 (총 {len(cleaned_majors)}개 전공)")
        
    except Exception as e:
        print("❌ 학과 테이블([majors]) 조회 실패:", e)
        
    conn.close()

    # =========================================================================
    # [4] 🚨 현재 서버가 실제로 바라보고 있는 `sitemap-static.xml` 파일로 출력 및 덮어쓰기
    # =========================================================================
    with open(f"{OUTPUT_DIR}/sitemap-static.xml", "w", encoding="utf-8") as f:
        f.write(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{"".join(all_urls)}</urlset>')
        
    print("\n🎉 [빌드 완료] ===================================================")
    print(f" 총 {len(all_urls)}개의 모든 주소가 현재 서버 실서빙 파일인 `sitemap-static.xml`에 오차 없이 덮어써졌습니다.")
    print("==================================================================")

if __name__ == "__main__":
    generate_sitemaps()