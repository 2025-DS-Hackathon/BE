from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db import get_db
from app.deps import get_current_user
<<<<<<< Updated upstream
from app.schemas import TalentCreate, TalentResponse
from app.services.talents_service import (
    create_talent,
    get_talents_by_user
)
=======
from app.schemas import TalentCreate, TalentOut
from app.models import User as DBUser
from app.crud.talents import create_talent, get_talents_by_user

router = APIRouter()
>>>>>>> Stashed changes


@router.get("/ping")
def ping_talents():
    return {"area": "talents", "status": "ok"}


# --- 재능 생성 ---
@router.post("", response_model=TalentOut, summary="내 재능 등록")
def create_my_talent(
    talent: TalentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    try:
        return create_talent(db, talent, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

<<<<<<< Updated upstream
# 내 재능 조회
@router.get("/me", response_model=list[TalentResponse])
=======

# --- 내 재능 목록 조회 ---
@router.get("/me", response_model=List[TalentOut], summary="내 재능 목록 조회")
>>>>>>> Stashed changes
def read_my_talents(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return get_talents_by_user(db, current_user.id)
