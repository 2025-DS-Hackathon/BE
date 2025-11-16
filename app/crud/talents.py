from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models import Talent as DBTalent, User as DBUser
from app.schemas import TalentCreate

#재능 생성
def create_talent(db: Session, talent: TalentCreate, user_id: int) -> DBTalent:
    db_talent = DBTalent(
        user_id=user_id,
        title=talent.title,
        description=talent.description,
        category=talent.category,
        talent_type=talent.talent_type,
        tags=talent.tags
    )
    db.add(db_talent)
    db.commit()
    db.refresh()
    return db_talent

#사용자별 재능 목록 조회
def get_talents_by_user(db: Session, user_id: int) -> list[DBTalent]:
    statement = select(DBTalent).where(DBTalent.user_id == user_id)
    talents = db.scalars(statement).all()
    return talents