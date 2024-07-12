from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from modeling import upload
import os
import uvicorn

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/upload")
async def upload_filee(file: UploadFile = File(...), username: str = Form(...)):
    # 임시 파일로 저장
    temp_file = f"temp_{file.filename}"
    with open(temp_file, "wb") as buffer:
        buffer.write(await file.read())
    
    try:
        # upload 함수 호출
        room_name, group, users, result = upload(temp_file, username)
        print("room_name : ", room_name)
        print("group : ", group)
        print("users : ", users)
        print("result : ", result)
        
        # 임시 파일 삭제
        os.remove(temp_file)
        
        return JSONResponse(content={
            "room_name": room_name,
            "group": group,
            "users": users,
            "result": result })
        
    except Exception as e:
        # 오류 발생 시 임시 파일 삭제 확인
        if os.path.exists(temp_file):
            os.remove(temp_file)
        return JSONResponse(content={"error": str(e)}, status_code=500)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)