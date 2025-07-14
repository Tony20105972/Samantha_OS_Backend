# Python 베이스 이미지
FROM python:3.10-slim

# 작업 디렉토리 설정
WORKDIR /app

# 종속성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 전체 코드 복사
COPY . .

# 포트 설정 (FastAPI 기본)
EXPOSE 8000

# 애플리케이션 실행 (agentlayer/api.py 내부의 app)
CMD ["uvicorn", "agentlayer.api:app", "--host", "0.0.0.0", "--port", "8000"]
