from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models import Talent as DBTalent, User
from app import models, schemas

#재능 생성
def create_talent(db: Session, talent: schemas.TalentCreate, user_id: int):
    db_talent = models.Talent(
        user_id=user_id,
        type=talent.type,
        category=talent.category,
        title=talent.title,
        tags=talent.tags,
        description=talent.description
    )
    db.add(db_talent)
    db.commit()
    db.refresh(db_talent)
    return db_talent


#사용자별 재능 목록 조회
def get_talents_by_user(db: Session, user_id: int) -> list[DBTalent]:
    statement = select(DBTalent).where(DBTalent.user_id == user_id)
    talents = db.scalars(statement).all()
    return talents