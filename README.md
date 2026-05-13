# 🏛️ CampusInfo API Server

우분투(Ubuntu) 서버 환경에서 운영되는 대학 정보 제공 API 서비스입니다.  
FastAPI를 사용하여 고성능 API를 제공하며, Docker와 GitHub Actions를 이용한 **완전 자동화 배포 파이프라인(CI/CD)**을 구축하였습니다.

---

## 🚀 Tech Stack
* **Framework:** FastAPI (Python 3.x)
* **Container:** Docker, Docker Compose
* **CI/CD:** GitHub Actions (Self-hosted Runner)
* **Network:** Cloudflare Tunnel (Argo Tunnel)

## 🏗️ Architecture & Deployment
이 프로젝트는 **Git Push** 한 번으로 실제 운영 서버에 소스가 즉시 반영되도록 설계되었습니다.

1. **Auto-Deployment:** GitHub에 소스 푸시 시, 서버에 설치된 Runner가 이를 감지하여 자동으로 빌드 및 배포를 수행합니다.
2. **Containerization:** API 서버와 Cloudflare Tunnel을 개별 컨테이너로 격리하여 관리하며, 서버 재부팅 시에도 자동으로 복구됩니다.
3. **Secure Access:** 고정 IP나 포트 포워딩 없이 Cloudflare Tunnel을 사용하여 보안성을 극대화하였으며, `https://api.integer7813.cloud`를 통해 안전하게 서빙됩니다.

---

## 📖 API 사용자 가이드 (Docs & Endpoint)

사용자는 아래 링크를 통해 실시간으로 API 명세를 확인하고 테스트할 수 있습니다.

### 1. API 문서 확인 (추천)
* **Swagger UI:** [https://api.integer7813.cloud/docs](https://api.integer7813.cloud/docs) (실시간 테스트 가능)
* **Redoc:** [https://api.integer7813.cloud/redoc](https://api.integer7813.cloud/redoc) (깔끔한 문서 열람)

### 2. 주요 엔드포인트 예시
모든 API 호출은 `https://api.integer7813.cloud` 베이스 주소를 사용합니다.

* **랜덤 대학교 정보 조회**
  * **Method:** `GET`
  * **Endpoint:** `/random-university`
  * **Description:** 전체 데이터베이스에서 무작위로 1개의 학교 상세 정보를 반환합니다.
  * **Example Response:**
    ```json
    {
      "status": "success",
      "data": {
        "학교구분": "대학원",
        "학교코드": 1568,
        "학교명": "상지대학교 대학원",
        "본분교": "본교",
        "학제": "일반대학원",
        "지역": "강원",
        "설립구분": "사립",
        "관련법령": "고등교육법",
        "법인명": "상지학원",
        "학교상태": "기존",
        "학교명(한자)": "尚志大学 大学院",
        "학교명(영문)": "Graduate School Sangji University",
        "주소": "강원특별자치도 원주시 상지대길 83 (우산동)",
        "영문주소": "83 Sangjidae-gil, Wonju-si, Gangwon-do",
        "중문주소": "83 Sangjidae-gil, Wonju-si, Gangwon-do",
        "우편번호": 26339,
        "학교개교일": "1955-06-10",
        "학교홈페이지": "www.sangji.ac.kr/grad/index.do",
        "총장명": "노병철",
        "학교대표번호": "033-730-0682",
        "학교대표팩스번호": "033-730-0684"
      }
    }
    ```

---

## 🔑 환경 변수 설정 (Secrets)
배포 자동화를 위해 GitHub Repository의 **Settings > Secrets > Actions**에 아래 항목이 등록되어야 합니다.
* `TUNNEL_TOKEN`: Cloudflare Zero Trust 대시보드에서 발급받은 터널 커넥터 토큰

## 🛠️ 서버 수동 관리 (참고용)
자동 배포가 아닌 서버 내에서 직접 컨테이너를 제어할 경우 아래 명령어를 사용합니다.

```bash
# 환경 변수 주입과 함께 빌드 및 백그라운드 실행
TUNNEL_TOKEN=your_token_here docker-compose up -d --build

# 컨테이너 상태 확인
docker ps

# 터널 연결 로그 실시간 확인
docker logs -f cloudflared

© 2026 integer7813. All rights reserved.
```

## 26-05-13 대학알리미 학교 개황 정보(2026.2.19.기준)
   (https://www.academyinfo.go.kr/brd/brd0520/selectDetail.do?ntce_sntc_sno=186&bbs_gubun=rfbr&no=21)
상기 데이터로 DB 최신화
