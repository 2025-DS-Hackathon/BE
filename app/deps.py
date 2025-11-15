from typing import Generator, Optional
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from .db import SessionLocal
from . import models

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(x_user_id: Optional[str] = Header(None), db: Session = Depends(get_db)):
    """
    간단한 테스트용 current_user 의존성.
    실제 서비스에선 OAuth / JWT 등으로 대체합니다.
    x_user_id 헤더로 user_id(정수)를 전달받는다고 가정.
    """
    if x_user_id is None:
        raise HTTPException(status_code=401, detail="X-User-Id header required for auth in this dev setup")
    try:
        uid = int(x_user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid X-User-Id header")
    user = db.query(models.User).filter(models.User.user_id == uid).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
