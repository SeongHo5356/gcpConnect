from fastapi import FastAPI, File, UploadFile, Form, BackgroundTasks, Request, Header
from fastapi.responses import JSONResponse
from modeling import upload
import asyncio
import os
import uvicorn
import torch
import httpx
import base64
import multiprocessing as mp

app = FastAPI()

async def send_request_to_new_endpoint(training_result: str, user_id: str, user_name: str, room_name: str):
    
    encoded_user_name = base64.b64encode(user_name.encode('utf-8')).decode('utf-8')
    encoded_room = base64.b64encode(room_name.encode('utf-8')).decode('utf-8')

    data = {
         "user_name": encoded_user_name,
         "user_id": user_id,
         "room": encoded_room,
         "reply_list": str(training_result)
    }

    print(f"Result Sent to DB | user_name : {encoded_user_name}")
    print(f"Result Sent to DB | user_id : {user_id}")
    print(f"Result Sent to DB | encoded_room : {encoded_room}")
    print(f"Result Sent to DB | reply_list : {training_result}")  
    async with httpx.AsyncClient() as client:
        response = await client.post( "https://itsmeweb.site/api/model_result", json=data)
    
    return response.status_code

@app.post("/test")
async def upload_file(
    background_tasks:BackgroundTasks,
    user_name: str = Form(...),
    user_id: str = Form(...),
    file: UploadFile = File(...)):

    ## bast64 인코딩 된 내용을 디코딩
    user_name_decoded = base64.b64decode(user_name).decode('utf-8')
    
    file_content = await file.read()

    # 벡그라운드 작업으로 처리
    background_tasks.add_task(process_file, file_content, file.filename, user_name_decoded, user_id)

    return {"filename": file.filename, "user_name": user_name_decoded, "user_id": user_id}

async def process_file(file_content: bytes, filename: str, user_name: str, user_id: str):

    print(f"User Upload : Received file from request: {filename}")
    print(f"User Upload : User Name from decoded from request: {user_name}")
    print(f"User Upload : User ID from request: {user_id}")

    # 임시 파일로 저장
    temp_file = f"temp_{filename}"
    with open(temp_file, "wb") as buffer:
        buffer.write(file_content)

    # 여기에 모델 학습 코드
    room_name, group, users, result = upload(temp_file, user_name)
    
    print(f"Model Learned | result : {result}")
    print(f"Model Learned | room_name : {room_name}")
    print(f"Model Learned | user_id : {user_id}")
    print(f"Model learned | user_name : {user_name}")

    # 임시 파일 제거
    os.remove(temp_file)

    # DB로 request를 보낸다
    status_code = await send_request_to_new_endpoint(result, user_id, user_name, room_name)

    print(f"Send Request to New EndPoint | Status code: {status_code}")

@app.get("/")
def read_root():
    return {"Welcome to Model Server Served By fastApi, GCP GPU instance"}

@app.post("/upload")
async def upload_filee(file: UploadFile = File(...), user_name: str = Form(...), user_id: str = Form(...)):
    # 임시 파일로 저장
    temp_file = f"temp_{file.filename}"
    with open(temp_file, "wb") as buffer:
        buffer.write(await file.read())
    
    try:
        # upload 함수 호출
        room_name, group, users, result = upload(temp_file, user_name)
        print("room_name : ", room_name)
        print("group : ", group)
        print("users : ", users)
        print("result : ", result)
        
        # 임시 파일 삭제
        os.remove(temp_file)
        
        return JSONResponse(content={
            "user_id": user_id,
            "user_name": user_name,
            "room": room_name,
            "reply_list": result })
        
    except Exception as e:
        # 오류 발생 시 임시 파일 삭제 확인
        if os.path.exists(temp_file):
            os.remove(temp_file)
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/gpu-info")
def get_gpu_info():
    return {
        "pytorch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "gpu_count": torch.cuda.device_count(),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "cuda_version": torch.version.cuda if torch.cuda.is_available() else None
    }

if __name__ == "__main__":
    mp.set_start_method('spawn')
    uvicorn.run(
        "api_server:app", 
        host="0.0.0.0",
        port=443, 
        ssl_keyfile="/etc/letsencrypt/live/itsmeweb.net/privkey.pem", 
        ssl_certfile="/etc/letsencrypt/live/itsmeweb.net/fullchain.pem"
        )

