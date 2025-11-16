# app/routers/users.py
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.deps import get_db, get_current_user, classify_user_type

router = APIRouter()


@router.get("/me", response_model=schemas.UserRead)
def read_me(
    current_user: models.User = Depends(get_current_user),
):
    """
    로그인한 내 정보 조회
    - 프론트는 여기서 birth_year / user_type / terms_agreed 보고
      추가 정보 입력 페이지로 보낼지 결정 가능
    """
    return current_user


@router.patch("/me/profile", response_model=schemas.UserRead)
def update_my_profile(
    profile_in: schemas.UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    LOGIN-1300 + 1410 + 1420
    - 출생연도 + 약관 동의 상태 저장
    - 세대 구분(user_type) 자동 계산
    """

    # 1) 출생연도 업데이트
    current_user.birth_year = profile_in.birth_year

    # 2) 세대 구분 (출생연도 기반)
    current_user.user_type = classify_user_type(profile_in.birth_year)

    # 3) 약관 동의 상태
    if profile_in.terms_agreed:
        current_user.terms_agreed = True
        current_user.terms_agreed_at = datetime.utcnow()
        current_user.terms_version = "v1"  # 약관 버전 관리용
    else:
        # 동의 해제하거나 미동의 상태로 둘 때
        current_user.terms_agreed = False
        current_user.terms_agreed_at = None
        # terms_version은 그대로 두거나, 필요하면 "none" 등으로 초기화할 수도 있음

    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    return current_user
