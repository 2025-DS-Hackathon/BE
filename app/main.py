from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import engine
from app.models import Base
from app.routers import auth, users, talents, matches, messages, notifications
from app.routers.matches import register_periodic_task
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
load_dotenv()

app = FastAPI(title="Talent Matching API")

# 🔥 CORS 설정 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "running"}

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(talents.router, prefix="/talents", tags=["talents"])
app.include_router(matches.router, prefix="/matches", tags=["matches"])
app.include_router(messages.router, prefix="/messages", tags=["messages"])
app.include_router(notifications.router, prefix="/notifications", tags=["notifications"])

register_periodic_task(app)
