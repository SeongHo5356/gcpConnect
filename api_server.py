from fastapi import FastAPI, File, UploadFile, Form, BackgroundTasks, Request, Header
from fastapi.responses import JSONResponse
from modeling import upload
import asyncio
import os
import uvicorn
import torch
import httpx
import base64
import shutil
import multiprocessing as mp
from fastapi.encoders import jsonable_encoder
from enum import Enum
from typing import Dict
from multiprocessing import Manager

app = FastAPI()

class TrainingStatus(Enum):
    PROCESSING = "processing"
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"

# 학습 상태를 저장할 딕셔너리
training_status: Dict[str, TrainingStatus] = {}

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
        response = await client.post("https://itsmeweb.site/api/model_result/", json=data)
    
    return response.status_code

def process_file_sync(file_content: bytes, filename: str, user_name: str, user_id: str):
    try :
        # 학습 시작 -> 학습 상태 update
        training_status[user_id] = TrainingStatus.PROCESSING.value
        print("training_status After process_file_start: ", training_status)

        print(f"User Upload : Received file from request: {filename}")
        print(f"User Upload : User Name from decoded from request: {user_name}")
        print(f"User Upload : User ID from request: {user_id}")

        # Save to temporary file
        temp_file = f"temp_{filename}"
        with open(temp_file, "wb") as buffer:
            buffer.write(file_content)

        # Model training code
        room_name, group, users, result = upload(temp_file, user_name)
    
        print(f"Model Learned | result : {result}")
        print(f"Model Learned | room_name : {room_name}")
        print(f"Model Learned | user_id : {user_id}")
        print(f"Model learned | user_name : {user_name}")

        # Remove temporary file
        os.remove(temp_file)

        # Send request to DB
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        status_code = loop.run_until_complete(send_request_to_new_endpoint(result, user_id, user_name, room_name))
        loop.close()
        
        # 학습이 완료됨
        training_status[user_id] = TrainingStatus.COMPLETED.value
        print("training_status After Send to DB: ", training_status)
        print("training_status After Send to DB: ", training_status)


        print(f"Send Request to New EndPoint | Status code: {status_code}")

    except Exception as e :
        print(f"Error in processing: {str(e)}")
        training_status[user_id] = TrainingStatus.FAILED.value


@app.post("/test")
async def upload_file(
    user_name: str = Form(...),
    user_id: str = Form(...),
    file: UploadFile = File(...)):

    # Decode base64 encoded user_name
    user_name_decoded = base64.b64decode(user_name).decode('utf-8')

    file_content = await file.read()
    if len(file_content) == 0:
        print("Empty file content")
        print(f"User Upload : Received file from request: {file.filename}")
        print(f"User Upload : User Name decoded from request: {user_name_decoded}")
        print(f"User Upload : User ID from request: {user_id}")
        return JSONResponse(content={"error": "빈 파일이 업로드되었습니다."}, status_code=400)
    
    decoded_content = file_content.decode('utf-8')
    # print(decoded_content)

    training_status[user_id] = TrainingStatus.PENDING

    print("training_status After Upload: ", training_status)

    print("Starting background process")
    process = mp.Process(target=process_file_sync, args=(file_content, file.filename, user_name_decoded, user_id))
    process.start()
    print("Background process started")
    
    response_data = {
        "filename": file.filename,
        "user_name": user_name_decoded,
        "user_id": user_id,
        "message": "File received and processing started",
        "status": training_status[user_id]
    }

    print("Returning response")
    return JSONResponse(content=jsonable_encoder(response_data), status_code=202)

@app.get("/training-status/{user_id}")
async def get_training_status(user_id: str):
    print("training_status : ", training_status)
    status = training_status.get(user_id, TrainingStatus.PENDING.value)
    return {"user_id": user_id, "status": status}

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

