# 베이스 이미지 설정
FROM python:3.9-slim

# 작업 디렉토리 설정
WORKDIR /app

# 필요한 파일 복사
COPY requirements.txt requirements.txt
COPY api_server.py api_server.py
COPY modeling.py modeling.py
COPY hug.py hug.py
COPY text_preprocessing.py text_preprocessing.py
COPY user_speech_modeling.py user_speech_modeling.py

# 라이브러리 설치
RUN pip install --no-cache-dir -r requirements.txt

# FastAPI 서버 실행
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]