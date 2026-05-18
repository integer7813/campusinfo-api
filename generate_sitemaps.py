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
    print("🚀 [분리 무결성 버전] 백엔드 동적 라우터 매칭 사이트맵 생성 시작...")
    
    # 혼선을 방지하기 위해 폴더를 비우고 새로 만듭니다.
    if os.path.exists(OUTPUT_DIR):
        import shutil
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # =========================================================================
    # [1] 오직 고정 정적 페이지 전용 ➡️ main.py의 /sitemap-static.xml 대응
    # =========================================================================
    base_routes = ['', '/about', '/contact', '/privacy', '/terms', '/future', '/univ/list']
    static_urls = [
        f"<url><loc>{BASE_URL}{route}</loc><changefreq>daily</changefreq><priority>{'1.0' if route == '' else '0.8'}</priority></url>"
        for route in base_routes
    ]
    with open(f"{OUTPUT_DIR}/sitemap-static.xml", "w", encoding="utf-8") as f:
        f.write(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{"".join(static_urls)}</urlset>')
    print(f"✅ sitemap-static.xml 생성 완료 ({len(base_routes)}개 정적 주소)")

    # =========================================================================
    # [2] 오직 전국 대학 상세 페이지 전용 ➡️ main.py의 /sitemap-univ.xml 대응
    # =========================================================================
    univ_urls = []
    try:
        cursor.execute("SELECT DISTINCT [학교명] FROM universities WHERE [학교명] NOT LIKE '%(폐교)%' AND [학교명] IS NOT NULL")
        univs = sorted(list(set([row[0].strip() for row in cursor.fetchall() if row[0]])))
        for u in univs:
            encoded_univ = urllib.parse.quote(u)
            univ_urls.append(
                f"<url><loc>{BASE_URL}/univ/{encoded_univ}</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>"
            )
    except Exception as e:
        print("❌ 대학 테이블 조회 실패:", e)

    with open(f"{OUTPUT_DIR}/sitemap-univ.xml", "w", encoding="utf-8") as f:
        f.write(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{"".join(univ_urls)}</urlset>')
    print(f"✅ sitemap-univ.xml 생성 완료 (총 {len(univ_urls)}개 대학 주소)")

    # =========================================================================
    # [3] 🎯 오직 전공명 리스트 전용 ➡️ main.py의 /sitemap-majors.xml 대응
    # =========================================================================
    major_urls = []
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
            major_urls.append(
                f"<url><loc>{BASE_URL}/major/list/name/{encoded_major}</loc>"
                f"<changefreq>weekly</changefreq><priority>0.6</priority></url>"
            )
    except Exception as e:
        print("❌ 학과 테이블 조회 실패:", e)
            
    with open(f"{OUTPUT_DIR}/sitemap-majors.xml", "w", encoding="utf-8") as f:
        f.write(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{"".join(major_urls)}</urlset>')
    print(f"✅ sitemap-majors.xml 생성 완료 (총 {len(major_urls)}개 전공 키워드 주소)")

    # =========================================================================
    # [4] 마스터 인덱스 지도 생성 ➡️ main.py의 /sitemap.xml 대응
    # =========================================================================
    index_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <sitemap><loc>{BASE_URL}/sitemap-static.xml</loc></sitemap>
        <sitemap><loc>{BASE_URL}/sitemap-univ.xml</loc></sitemap>
        <sitemap><loc>{BASE_URL}/sitemap-majors.xml</loc></sitemap>
    </sitemapindex>
    """
    with open(f"{OUTPUT_DIR}/sitemap.xml", "w", encoding="utf-8") as f:
        f.write(index_xml)
    
    conn.close()
    print("\n🎉 [연동 빌드 성공] ===============================================")
    print(" main.py 라우터 경로 규격에 맞게 각각의 독립형 XML 파일들이 완벽히 분리 생성되었습니다.")
    print("==================================================================")

if __name__ == "__main__":
    generate_sitemaps()