# main.py
from fastapi import FastAPI
from app.db import engine
from app.models import Base
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, users, talents, matches, messages, notifications
from app.routers.matches import register_periodic_task
from dotenv import load_dotenv
load_dotenv()

app = FastAPI(title="Talent Matching API")


origins = [
   "http://localhost:3000",
    "https://localhost:3000",
    "http://127.0.0.1:3000",
    "https://127.0.0.1:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


#  서버 실행 시 SQLite 테이블 자동 생성
Base.metadata.create_all(bind=engine)

@app.get("/")
def read_root():
    return{"status":"ok","message":"runnning"}

#  라우터 등록
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(talents.router, prefix="/talents", tags=["talents"])
app.include_router(matches.router, prefix="/matches", tags=["matches"])
app.include_router(messages.router, prefix="/messages", tags=["messages"])
app.include_router(notifications.router, prefix="/notifications", tags=["notifications"])

#워커 등록
register_periodic_task(app)