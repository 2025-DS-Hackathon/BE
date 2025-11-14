from fastapi import APIRouter

router = APIRouter()

@router.get("/ping")
def ping_talents():
    return {"area": "talents", "status": "ok"}
