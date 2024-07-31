# modeling_server.py
from fastapi import FastAPI
import redis
import asyncio
from pydantic import BaseModel

app = FastAPI()
r = redis.Redis(host='localhost', port=6379, db=0)

SERVER_URL = 'http://localhost:8002'  # 또는 8002

class Data(BaseModel):
    data: str

@app.post("/model")
async def model(data: Data):
    # 모델링 작업 시뮬레이션
    await asyncio.sleep(5)
    result = {"processed_data2": f"Processed: {data.data}"}
    
    return result

@app.post("/register")
async def register():
    r.lpush('available_servers', SERVER_URL)
    return {"message": "Registered"}

@app.post("/unregister")
async def unregister():
    r.lrem('available_servers', 0, SERVER_URL)
    return {"message": "Unregistered"}

@app.on_event("startup")
async def startup_event():
    # 시작할 때 서버 등록
    r.lpush('available_servers', SERVER_URL)

@app.on_event("shutdown")
async def shutdown_event():
    # 종료할 때 서버 등록 해제
    r.lrem('available_servers', 0, SERVER_URL)