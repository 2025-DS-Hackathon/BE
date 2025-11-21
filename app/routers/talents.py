from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.deps import get_db, get_current_user

router = APIRouter(tags=["talents"])


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

def to_summary(t):
    if not t:
        return None
    return schemas.TalentSummary(
        talent_id=t.talent_id,
        title=t.title,
        category=t.category,
        tags=t.tags,
        description=t.description,
        type=t.type,
    )

# 내 재능 요약 (메인 카드용)
@router.get("/my-summary", response_model=schemas.MyTalentSummaryResponse)
def get_my_talent_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    메인 페이지용 재능 카드 요약 조회
    """
    talents = (
        db.query(models.Talent)
        .filter(models.Talent.user_id == current_user.user_id)
        .all()
    )

    # 🔥 [핵심 수정] ID 기준 내림차순 정렬 (최신이 맨 앞으로 오도록)
    talents.sort(key=lambda x: x.talent_id, reverse=True)

    learn_talent: Optional[models.Talent] = None
    teach_talent: Optional[models.Talent] = None

    for t in talents:
        t_type = (t.type or "").lower() # t.talent_type 일 수도 있으니 모델 확인 필요
        
        # 이제 리스트 앞에 최신 데이터가 있으므로, 
        # 'is None' 체크를 해도 '최신 데이터'가 먼저 선점하게 됩니다.
        if "learn" in t_type and learn_talent is None:
            learn_talent = t
        elif "teach" in t_type and teach_talent is None:
            teach_talent = t

    return schemas.MyTalentSummaryResponse(
        learn=to_summary(learn_talent), # to_summary 함수가 있다고 가정
        teach=to_summary(teach_talent),
    )