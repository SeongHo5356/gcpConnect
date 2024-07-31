from fastapi import FastAPI, HTTPException
import httpx
import redis
from pydantic import BaseModel
import asyncio
from tenacity import retry, stop_after_attempt, wait_fixed

app = FastAPI()
r = redis.Redis(host='localhost', port=6379, db=0)

class Data(BaseModel):
    data: str

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def send_to_modeling_server(client, url, data):
    response = await client.post(url, json=data, timeout=30.0)
    response.raise_for_status()
    return response.json()

@app.post("/process")
async def process(data: Data):
    available_server = r.rpop('available_servers')
    if not available_server:
        raise HTTPException(status_code=503, detail="No servers available")
    
    server_url = available_server.decode('utf-8')
    
    try:
        async with httpx.AsyncClient() as client:
            result = await send_to_modeling_server(client, f"{server_url}/model", data.dict())
    except httpx.ReadTimeout:
        r.lpush('available_servers', server_url)  # 서버를 다시 목록에 추가
        raise HTTPException(status_code=504, detail="Request to modeling server timed out")
    except httpx.HTTPStatusError as exc:
        r.lpush('available_servers', server_url)  # 서버를 다시 목록에 추가
        raise HTTPException(status_code=exc.response.status_code, detail=str(exc))
    except Exception as exc:
        r.lpush('available_servers', server_url)  # 서버를 다시 목록에 추가
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(exc)}")
    
    r.lpush('available_servers', server_url)
    return result