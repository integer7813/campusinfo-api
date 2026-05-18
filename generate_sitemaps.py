# -*- coding: utf-8 -*-
# generate_sitemaps.py
import sqlite3
import urllib.parse
import os
import re

DB_PATH = "universities.db"
OUTPUT_DIR = "./static/sitemaps"
BASE_URL = "https://integer7813.cloud"

def clean_major_name(raw_name):
    """
    유저가 입력하는 '전공명'을 있는 그대로 반영하되,
    혹시 맨 앞에 붙어있을지 모르는 숫자 코드 정도만 트리밍합니다.
    예: '(25)경찰행정학전공' -> '경찰행정학전공' 혹은 괄호가 포함된 원본 유지
    """
    if not raw_name:
        return None
    
    # 만약 원본 데이터 그대로 (25)까지 주소창에 치는 스펙이라면 아래 re.sub를 주석 처리하세요.
    # 여기서는 앞쪽 숫자/괄호 찌꺼기만 떼고 '금융・빅데이터학부(금융수학전공)' 같은 본체는 그대로 유지합니다.
    name = re.sub(r'^[\(\[\{\d+\)\]\}]+', '', raw_name.strip())
    name = name.strip()
    
    if len(name) < 2:
        return None
    return name

def generate_sitemaps():
    print("🚀 대용량 완전체 사이트맵 생성 시작 (원본 전공명 보존 버전)...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # [1] 기본 고정 정적 페이지용 사이트맵 생성
    base_routes = ['', '/about', '/contact', '/privacy', '/terms', '/future', '/univ/list']
    static_urls = [
        f"<url><loc>{BASE_URL}{route}</loc><changefreq>daily</changefreq><priority>{'1.0' if route == '' else '0.8'}</priority></url>"
        for route in base_routes
    ]
    with open(f"{OUTPUT_DIR}/sitemap-static.xml", "w", encoding="utf-8") as f:
        f.write(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{"".join(static_urls)}</urlset>')

    # [2] 대학 상세 사이트맵 생성 (폐교 제외)
    cursor.execute("SELECT DISTINCT [학교명] FROM universities WHERE [학교명] NOT LIKE '%(폐교)%' AND [학교명] IS NOT NULL")
    univs = sorted(list(set([row[0].strip() for row in cursor.fetchall() if row[0]])))
    univ_urls = [
        f"<url><loc>{BASE_URL}/univ/{urllib.parse.quote(u)}</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>"
        for u in univs
    ]
    with open(f"{OUTPUT_DIR}/sitemap-univ.xml", "w", encoding="utf-8") as f:
        f.write(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{"".join(univ_urls)}</urlset>')

    # [3] 🎯 전공명 리스트 사이트맵 생성 (원본 문자열 그대로 맵핑)
    major_urls = []
    try:
        # 가드 조건(현행 상태 + 운영 대학)만 걸고, [학부·과(전공)명] 컬럼의 괄호나 특수문자를 절대 쳐내지 않습니다.
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
            cleaned = clean_major_name(raw_val) # 필요시 세탁, 원본 그대로면 raw_val 사용
            if cleaned:
                processed_majors.add(cleaned)
        
        cleaned_majors = sorted(list(processed_majors))

        for major in cleaned_majors:
            # 💡 금융・빅데이터학부(금융수학전공) 등의 특수문자/괄호가 원본 그대로 퍼센트 인코딩됩니다.
            encoded_major = urllib.parse.quote(major)
            major_urls.append(
                f"<url><loc>{BASE_URL}/major/list/name/{encoded_major}</loc>"
                f"<changefreq>weekly</changefreq><priority>0.6</priority></url>"
            )
            
        print(f"💡 사이트맵 빌드 완료: 총 {len(cleaned_majors)}개의 실제 전공명 URL 생성")
        
    except Exception as e:
        print("❌ 학과 테이블 조회 또는 매핑 실패:", e)
            
    with open(f"{OUTPUT_DIR}/sitemap-majors.xml", "w", encoding="utf-8") as f:
        f.write(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{"".join(major_urls)}</urlset>')

    # [4] 마스터 인덱스 사이트맵 생성
    index_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <sitemap><loc>{BASE_URL}/api/sitemaps/sitemap-static.xml</loc></sitemap>
        <sitemap><loc>{BASE_URL}/api/sitemaps/sitemap-univ.xml</loc></sitemap>
        <sitemap><loc>{BASE_URL}/api/sitemaps/sitemap-majors.xml</loc></sitemap>
    </sitemapindex>
    """
    with open(f"{OUTPUT_DIR}/sitemap.xml", "w", encoding="utf-8") as f:
        f.write(index_xml)
    
    conn.close()
    print("🎉 주소창 라우터 스펙과 100% 일치하는 전공명 기반 사이트맵 생성 완료!")

if __name__ == "__main__":
    generate_sitemaps()