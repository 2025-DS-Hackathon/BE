# app/routers/notifications.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def list_notifications():
    return []
