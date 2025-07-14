# Python 3.10 slim 버전 사용
FROM python:3.10-slim

# 작업 디렉토리 설정
WORKDIR /app

# 종속성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 전체 프로젝트 복사
COPY . .

# FastAPI 앱 실행 (agentlayer_api.py 안에 app 객체가 있어야 함)
CMD ["uvicorn", "agentlayer_api:app", "--host", "0.0.0.0", "--port", "8000"]
