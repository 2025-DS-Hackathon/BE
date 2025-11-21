# app/routers/talents.py
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.deps import get_db, get_current_user

<<<<<<< Updated upstream
router = APIRouter(prefix="/talents", tags=["Talents"])
=======
# 팀원 코드까지 합쳐서 prefix / tags 넣은 버전
router = APIRouter(prefix="/talents", tags=["talents"])
>>>>>>> Stashed changes


@router.get("/ping")
def ping_talents():
    return {"area": "talents", "status": "ok"}


# 재능 생성
@router.post("", response_model=schemas.TalentOut, status_code=status.HTTP_201_CREATED)
def create_my_talent(
    talent: schemas.TalentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    현재 로그인한 사용자의 재능(Teach/Learn) 1건 생성
    """
    if not current_user.terms_agreed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="약관에 동의해야 재능 등록이 가능합니다.",
        )

    new_talent = models.Talent(
        user_id=current_user.user_id,
        type=talent.type.value,         # Enum → 문자열
        category=talent.category.value, # Enum → 문자열
        title=talent.title,
        tags=talent.tags,               # 쉼표 처리 등은 Pydantic validator에서
        description=talent.description,
    )
    db.add(new_talent)
    db.commit()
    db.refresh(new_talent)
    return new_talent


# 내 재능 요약 (메인 카드용)
@router.get("/my-summary", response_model=schemas.MyTalentSummaryResponse)
def get_my_talent_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    메인 페이지용 재능 카드 요약 조회
    - Learn(내가 배우고 싶은 것)
    - Teach(내가 가르쳐줄 수 있는 것)
    """
    talents = (
        db.query(models.Talent)
        .filter(models.Talent.user_id == current_user.user_id)
        .all()
    )

    learn_talent: Optional[models.Talent] = None
    teach_talent: Optional[models.Talent] = None

    for t in talents:
        t_type = (t.type or "").lower()  # "Learn"/"Teach" 가정
        if t_type == "learn" and learn_talent is None:
            learn_talent = t
        elif t_type == "teach" and teach_talent is None:
            teach_talent = t

    return schemas.MyTalentSummaryResponse(
        learn=learn_talent,
        teach=teach_talent,
    )
