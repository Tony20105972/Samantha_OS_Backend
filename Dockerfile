# Dockerfile
FROM python:3.10-slim

# 환경 변수 설정
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 작업 디렉토리 설정
WORKDIR /app

# 필요 파일 복사
COPY . /app

# 패키지 설치
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# 실행 명령 (FastAPI 기준)
CMD ["uvicorn", "agentlayer_api:app", "--host", "0.0.0.0", "--port", "8000"]
