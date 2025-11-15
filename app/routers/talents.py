from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.deps import get_current_user
from app.schemas import TalentCreate, TalentResponse
from app.services.talents_service import (
    create_talent,
    get_talents_by_user
)

router = APIRouter(prefix="/talents", tags=["Talents"])

@router.get("/ping")
def ping_talents():
    return {"area": "talents", "status": "ok"}

# 재능 생성
@router.post("", response_model=TalentResponse)
def create_my_talent(
    talent: TalentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return create_talent(db, talent, current_user.id)

# 내 재능 조회
@router.get("/me", response_model=list[TalentResponse])
def read_my_talents(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return get_talents_by_user(db, current_user.id)