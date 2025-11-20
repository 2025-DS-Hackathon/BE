from typing import Generator, Optional
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from .db import SessionLocal
from . import models

<<<<<<< HEAD
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

# ====================
# 환경변수 로드
# ====================
load_dotenv()

# ====================
#  JWT 설정
#   - 위에서 env로 읽은 SECRET_KEY를 사용하고,
#     아래에서 다시 덮어쓰지 않도록 정리
# ====================
# 수정 포인트 ①: 하드코딩된 SECRET_KEY 삭제하고 env 기반으로 통일
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")  # .env에 SECRET_KEY 설정 추천
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 토큰 유효기간 (예: 1일)


# ====================
# 비밀번호 해시/검증
# ====================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# ====================
# DB 세션
# ====================

=======
>>>>>>> ebc8d29ebdaf42a934c93d916719e2fc48437fad
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

<<<<<<< HEAD
# ====================
# JWT Access Token 생성
# ====================
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


# ====================
# 현재 로그인한 유저 가져오기
# ====================

# tokenUrl을 실제 토큰 발급 엔드포인트에 맞게 변경 (카카오 단일 로그인 기준)
#   - Swagger UI의 "Authorize" 버튼에서 사용하는 값이라,
#     지금 구조라면 /auth/kakao/callback 이 더 의미에 맞음.
#   - 나중에 ID/PW 로그인용 /auth/login 만들 거면 다시 바꿔도 됨.
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


# ====================
# 세대 구분 유틸 함수
#   - users.py 의 update_my_profile() 에서 사용
# ====================
# 추가 포인트 ③: classify_user_type 구현
def classify_user_type(birth_year: Optional[int]) -> str:
    """
    출생연도 기준으로 user_type 분류
    - 기준은 임의 예시이므로, 팀에서 정한 기준으로 수정 가능
    """
    if birth_year is None:
        return "UNKNOWN"

    # 예시 기준:
    #  - 1990년 이후: YOUNG
    #  - 1964년 이전: SENIOR
    #  - 그 사이: MIDDLE
    if birth_year >= 1990:
        return "YOUNG"
    elif birth_year <= 1964:
        return "SENIOR"
    else:
        return "MIDDLE"


# ====================
# (선택) 약관 동의한 유저만 허용하는 의존성
#   - 필요한 엔드포인트에서 get_current_user 대신 이걸 써도 됨
# ====================
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
=======
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
>>>>>>> ebc8d29ebdaf42a934c93d916719e2fc48437fad
