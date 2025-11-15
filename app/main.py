# main.py
from fastapi import FastAPI
from app.db import engine
from app.models import Base
from app.routers import auth, users, talents, matches, messages, notifications

app = FastAPI(title="Talent Matching API")

#  서버 실행 시 SQLite 테이블 자동 생성
Base.metadata.create_all(bind=engine)

#  라우터 등록
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(talents.router, prefix="/talents", tags=["talents"])
app.include_router(matches.router, prefix="/matches", tags=["matches"])
app.include_router(messages.router, prefix="/messages", tags=["messages"])
app.include_router(notifications.router, prefix="/notifications", tags=["notifications"])