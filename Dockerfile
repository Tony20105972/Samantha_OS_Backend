# Python 3.11 경량 이미지 사용
FROM python:3.11-slim

# 시스템 패키지 설치 (optional: pip 관련 오류 방지용)
RUN apt-get update && apt-get install -y build-essential

# 작업 디렉토리 설정
WORKDIR /app

# requirements 먼저 복사 후 설치 (Docker 캐시 최적화)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 전체 프로젝트 복사
COPY . .

# Fly.io는 반드시 0.0.0.0:8080 포트로 리스닝해야 함
EXPOSE 8080

# FastAPI 앱 실행 (agentlayer/api.py 기준 경로)
CMD ["uvicorn", "agentlayer.api:app", "--host", "0.0.0.0", "--port", "8080"]
