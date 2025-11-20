from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
import os

from dotenv import load_dotenv
from app.db import SessionLocal
from app import models

# ====================
# 환경변수 로드
# ====================
load_dotenv()

# ====================
# JWT 설정
# ====================
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1일

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ====================
# 비밀번호 해시/검증
# ====================
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# ====================
# DB 세션
# ====================
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ====================
# JWT Access Token 생성
# ====================
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# ====================
# HTTP Bearer 스키마 (Swagger용)
# ====================
bearer_scheme = HTTPBearer()  # 🔥 OAuth2PasswordBearer → HTTPBearer 로 변경됨


# ====================
# 현재 로그인한 유저 가져오기
# ====================
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> models.User:

    token = credentials.credentials  # "Bearer xxx" 중 xxx 부분만 자동 추출됨

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="로그인이 필요합니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # JWT 디코드
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # DB 조회
    user = db.query(models.User).get(int(user_id))
    if user is None:
        raise credentials_exception

    return user


# ====================
# 세대 구분 유틸 함수
# ====================
def classify_user_type(birth_year: Optional[int]) -> str:
    if birth_year is None:
        return "UNKNOWN"

    if birth_year >= 1990:
        return "YOUNG"
    elif birth_year <= 1964:
        return "SENIOR"
    else:
        return "MIDDLE"


# ====================
# (선택) 약관 동의한 유저만 허용
# ====================
def get_active_user(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    if not current_user.terms_agreed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="서비스를 이용하려면 약관에 동의해야 합니다.",
        )
    return current_user
