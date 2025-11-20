<<<<<<< HEAD
# app/routers/talents.py
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.deps import get_db, get_current_user
=======
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.deps import get_current_user
from app.schemas import TalentCreate, TalentResponse
from app.models import User as DBUser
from .talents import create_talent, get_talents_by_user
>>>>>>> ebc8d29ebdaf42a934c93d916719e2fc48437fad

router = APIRouter(prefix="/talents", tags=["Talents"])


@router.get("/ping")
def ping_talents():
<<<<<<< HEAD
    return {"area": "talents", "status": "ok"}@router.post("", response_model=schemas.TalentOut)

@router.post("", response_model=schemas.TalentOut)
def create_my_talent(
    talent: schemas.TalentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not current_user.terms_agreed:
        raise HTTPException(status_code=403, detail="약관에 동의해야 재능 등록이 가능합니다.")

    new_talent = models.Talent(
        user_id=current_user.user_id,
        type=talent.type.value,
        category=talent.category.value,
        title=talent.title,
        tags=talent.tags,          # validator에서 쉼표 처리됨
        description=talent.description
    )
    db.add(new_talent)
    db.commit()
    db.refresh(new_talent)
    return new_talent

@router.get("/my-summary", response_model=schemas.MyTalentSummaryResponse)
def get_my_talent_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    메인 페이지용 재능 카드 요약 조회
    - Learn(내가 배우고 싶은 것)
    - Teach(내가 가르쳐줄 수 있는 것)
    두 종류 중, 현재 로그인한 사용자가 등록한 것이 있다면
    각각 1개씩 요약 정보를 반환한다.
    """

    # 현재 유저의 모든 Talent 조회
    talents = (
        db.query(models.Talent)
        .filter(models.Talent.user_id == current_user.user_id)
        .all()
    )

    learn_talent: Optional[models.Talent] = None
    teach_talent: Optional[models.Talent] = None

    for t in talents:
        # type 필드에 "Learn" / "Teach" 저장된다고 가정
        t_type = (t.type or "").lower()
        if t_type == "learn" and learn_talent is None:
            learn_talent = t
        elif t_type == "teach" and teach_talent is None:
            teach_talent = t

    # Pydantic이 orm_mode 덕분에 SQLAlchemy 객체를 그대로 받아 변환해준다.
    return schemas.MyTalentSummaryResponse(
        learn=learn_talent,
        teach=teach_talent,
    )
=======
    return {"area": "talents", "status": "ok"}

# 재능 생성
@router.post("", response_model=TalentResponse)
def create_my_talent(
    talent: TalentCreate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    return create_talent(db, talent, current_user.id)

# 내 재능 목록 조회
@router.get("/me", response_model=list[TalentResponse])
def read_my_talents(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    return get_talents_by_user(db, current_user.id)
>>>>>>> ebc8d29ebdaf42a934c93d916719e2fc48437fad
