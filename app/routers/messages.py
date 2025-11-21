from fastapi import APIRouter

router = APIRouter()

@router.get("/ping")
def ping_messages():
    return {"area": "messages", "status": "ok"}
