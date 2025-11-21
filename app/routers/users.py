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
    return current_user


@router.patch("/me/profile", response_model=schemas.UserRead)
def update_my_profile(
    profile_in: schemas.UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):

    current_user.birth_year = profile_in.birth_year
    current_user.user_type = classify_user_type(profile_in.birth_year)


    from datetime import datetime
    current_year = datetime.now().year
    if current_user.birth_year:
        age = current_year - current_user.birth_year
        current_user.user_type = "young" if age < 40 else "senior"
    else:
        current_user.user_type = "UNKNOWN"
    # 약관 동의 상태
    if profile_in.terms_agreed:
        current_user.terms_agreed = True
        current_user.terms_agreed_at = datetime.utcnow()
        current_user.terms_version = "v1"  
    else:
        # 동의 해제하거나 미동의 상태로 둘 때
        current_user.terms_agreed = False
        current_user.terms_agreed_at = None
        # terms_version은 그대로 두거나, 필요하면 "none" 등으로 초기화할 수도 있음

    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    return current_user
