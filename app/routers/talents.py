from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.deps import get_db, get_current_user

router = APIRouter(prefix="/talents", tags=["Talents"])


# ---------------------------
# 1) Ping (라우터 확인용)
# ---------------------------
@router.get("/ping")
def ping_talents():
    return {"area": "talents", "status": "ok"}


# ---------------------------
# 2) 재능 생성
# ---------------------------
@router.post("/", response_model=schemas.TalentOut)
def create_my_talent(
    talent: schemas.TalentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not current_user.terms_agreed:
        raise HTTPException(status_code=403, detail="약관에 동의해야 재능 등록이 가능합니다.")

    new_talent = models.Talent(
        user_id=current_user.user_id,
        type=getattr(talent.type, "value", talent.type),        # Enum이든 문자열이든 대응
        category=getattr(talent.category, "value", talent.category),
        title=talent.title,
        tags=talent.tags,
        description=talent.description,
    )

    db.add(new_talent)
    db.commit()
    db.refresh(new_talent)
    return new_talent


# ---------------------------
# 3) 내 재능 요약 조회
# ---------------------------
@router.get("/my-summary", response_model=schemas.MyTalentSummaryResponse)
def get_my_talent_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    talents = (
        db.query(models.Talent)
        .filter(models.Talent.user_id == current_user.user_id)
        .all()
    )

    learn_talent: Optional[models.Talent] = None
    teach_talent: Optional[models.Talent] = None

    for t in talents:
        t_type = (t.type or "").lower()
        if t_type == "learn" and learn_talent is None:
            learn_talent = t
        elif t_type == "teach" and teach_talent is None:
            teach_talent = t

    return schemas.MyTalentSummaryResponse(
        learn=learn_talent,
        teach=teach_talent,
    )
