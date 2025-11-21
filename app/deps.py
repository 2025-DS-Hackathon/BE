from typing import Generator, Optional
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from .db import SessionLocal
from . import models

import os
from datetime import datetime, timedelta
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.db import SessionLocal
from app import models

# 환경변수 로드
load_dotenv()


SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")  # .env에 SECRET_KEY 설정 추천
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 토큰 유효기간 (예: 1일)


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)



def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """JWT Access Token 생성"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/kakao/callback")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="로그인이 필요합니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(models.User).get(int(user_id))
    if user is None:
        raise credentials_exception
    return user


def classify_user_type(birth_year: Optional[int]) -> str:
    """
    출생연도 기준으로 user_type 분류
    - 기준은 임의 예시이므로, 팀에서 정한 기준으로 수정 가능
    """
    if birth_year is None:
        return "UNKNOWN"

    if birth_year >= 1990:
        return "YOUNG"
    elif birth_year <= 1964:
        return "SENIOR"
    else:
        return "MIDDLE"


def get_active_user(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    """
    약관에 동의한 사용자만 접근 가능하게 하고 싶을 때 사용하는 의존성.
    예: 매칭 생성, 재능 등록 등의 보호된 API에 사용.
    """
    if not current_user.terms_agreed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="서비스를 이용하려면 약관에 동의해야 합니다.",
        )
    return current_user