FROM python:3.11-slim

WORKDIR /app

# 의존성 먼저 설치 (레이어 캐시 활용)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 앱 소스 및 정적 라이브러리 복사 (내부망 환경 — CDN 없이 로컬 파일 사용)
COPY app.py .
COPY parser/ ./parser/
COPY templates/ ./templates/
COPY static/ ./static/

ENV CONFIG_DIR=/config

EXPOSE 5001

CMD ["python", "app.py"]
