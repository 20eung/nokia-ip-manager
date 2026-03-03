FROM python:3.11-slim

WORKDIR /app

# 의존성 먼저 설치 (레이어 캐시 활용)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 앱 소스 복사
COPY app.py .
COPY parser/ ./parser/
COPY templates/ ./templates/

ENV CONFIG_DIR=/config

EXPOSE 5001

CMD ["python", "app.py"]
