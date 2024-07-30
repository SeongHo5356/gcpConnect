# modeling_server.py
import os
from fastapi import FastAPI, BackgroundTasks
import redis
import asyncio
import json
from pydantic import BaseModel

app = FastAPI()
r = redis.Redis(host=os.getenv('REDIS_HOST', 'localhost'), port=6379, db=0)

SERVER_URL = os.getenv('SERVER_URL', 'http://localhost:8000')

class Data(BaseModel):
    data: str

async def process_queued_job():
    while True:
        # 큐에서 작업 가져오기
        job_id = r.rpop('job_queue')
        if job_id:
            job_id = job_id.decode('utf-8')
            job_data = r.hget(f"job:{job_id}", "data")
            if job_data:
                data = json.loads(job_data)
                await model(Data(**data))
                # 작업 완료 후 상태 업데이트
                r.hset(f"job:{job_id}", "status", "completed")
        await asyncio.sleep(1)  # 잠시 대기 후 다음 작업 확인

@app.post("/model")
async def model(data: Data):
    # 모델링 작업 시뮬레이션
    await asyncio.sleep(5)
    result = {"processed_data2": f"Processed: {data.data}"}
    return result

@app.on_event("startup")
async def startup_event():
    r.lpush('available_servers', SERVER_URL)
    # 백그라운드에서 대기 중인 작업 처리 시작
    asyncio.create_task(process_queued_job())

@app.on_event("shutdown")
async def shutdown_event():
    r.lrem('available_servers', 0, SERVER_URL)