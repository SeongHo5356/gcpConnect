# api_server.py
import os
from fastapi import FastAPI, HTTPException, BackgroundTasks
import httpx
import redis
import json
from pydantic import BaseModel

app = FastAPI()
r = redis.Redis(host=os.getenv('REDIS_HOST', 'localhost'), port=6379, db=0)

class Data(BaseModel):
    data: str

class Job(BaseModel):
    id: str
    status: str
    result: dict = None

async def process_job(job_id: str, data: dict):
    # 작업 상태를 '처리 중'으로 업데이트
    r.hset(f"job:{job_id}", "status", "processing")
    
    available_server = r.rpop('available_servers')
    if not available_server:
        # 사용 가능한 서버가 없으면 작업을 다시 큐에 넣음
        r.lpush('job_queue', job_id)
        r.hset(f"job:{job_id}", "status", "queued")
        return

    server_url = available_server.decode('utf-8')
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{server_url}/model", json=data, timeout=30.0)
            result = response.json()
        
        # 작업 결과 저장
        r.hset(f"job:{job_id}", mapping={
            "status": "completed",
            "result": json.dumps(result)
        })
    except Exception as exc:
        # 에러 발생 시 작업 상태 업데이트
        r.hset(f"job:{job_id}", mapping={
            "status": "failed",
            "result": json.dumps({"error": str(exc)})
        })
    finally:
        # 서버를 다시 사용 가능한 목록에 추가
        r.lpush('available_servers', server_url)

@app.post("/process", response_model=Job)
async def process(data: Data, background_tasks: BackgroundTasks):
    # 새 작업 ID 생성
    job_id = str(r.incr('job_id_counter'))
    
    # 작업 정보 저장
    r.hset(f"job:{job_id}", mapping={
        "id": job_id,
        "status": "queued",
        "data": json.dumps(data.dict())
    })
    
    # 작업을 큐에 추가
    r.lpush('job_queue', job_id)
    
    # 백그라운드에서 작업 처리 시작
    background_tasks.add_task(process_job, job_id, data.dict())
    
    return Job(id=job_id, status="queued")

@app.get("/job/{job_id}", response_model=Job)
async def get_job(job_id: str):
    job_data = r.hgetall(f"job:{job_id}")
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = Job(
        id=job_id,
        status=job_data[b'status'].decode('utf-8'),
        result=json.loads(job_data[b'result'].decode('utf-8')) if b'result' in job_data else None
    )
    return job
