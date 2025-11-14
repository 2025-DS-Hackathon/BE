from fastapi import APIRouter

router = APIRouter()

@router.get("/ping")
def ping_matches():
    return {"area": "matches", "status": "ok"}
