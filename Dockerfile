# 1. 파이썬 환경 설정
FROM python:3.11-slim

# 2. 컨테이너 내부 작업 디렉토리
WORKDIR /app

# 3. 라이브러리 설치를 위해 목록 복사
COPY requirements.txt .

# 4. 라이브러리 설치
RUN pip install --no-cache-dir -r requirements.txt

# 5. 나머지 소스 코드 전부 복사
COPY . .

# 6. 외부에서 접속할 포트 개방
EXPOSE 8000

# 7. 서버 실행 명령어
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]