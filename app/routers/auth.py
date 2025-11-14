from fastapi import APIRouter

router = APIRouter()

@router.get("/ping")
def ping_auth():
    return {"area": "auth", "status": "ok"}
