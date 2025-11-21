# app/routers/auth.py  (카카오 단일 로그인 버전)

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
import os
import urllib.parse
import requests  # pip install requests

from fastapi.responses import RedirectResponse   # ★ 추가

from dotenv import load_dotenv
load_dotenv()

from app import models, schemas
from app.deps import get_db, create_access_token

router = APIRouter()

# 환경변수에서 카카오 앱 정보 가져오기
KAKAO_CLIENT_ID: str = os.getenv("KAKAO_CLIENT_ID", "")
KAKAO_REDIRECT_URI: str = os.getenv("KAKAO_REDIRECT_URI", "")

# 카카오 로그인 완료 후, 우리가 최종적으로 보내줄 프론트 주소
# 👉 프론트 라우팅에 맞게 경로만 바꿔도 됨 (예: /auth/kakao/success 등)
FRONTEND_LOGIN_SUCCESS_URL: str = os.getenv(
    "FRONTEND_LOGIN_SUCCESS_URL",
    "http://localhost:3000/login/success"  # 기본값
)

print("DEBUG KAKAO_CLIENT_ID:", KAKAO_CLIENT_ID)
print("DEBUG KAKAO_REDIRECT_URI:", KAKAO_REDIRECT_URI)

if not KAKAO_CLIENT_ID or not KAKAO_REDIRECT_URI:
    print("[WARN] KAKAO_CLIENT_ID 또는 KAKAO_REDIRECT_URI가 설정되지 않았습니다.")


# ---------- 1) 카카오 로그인 URL 제공 ----------
@router.get("/kakao/login")
def kakao_login_url():
    """
    프론트에게 카카오 인증 URL을 내려주는 엔드포인트.
    프론트는 이 URL로 사용자를 리다이렉트하면 됨.
    """
    base_url = "https://kauth.kakao.com/oauth/authorize"
    params = {
        "client_id": KAKAO_CLIENT_ID,
        "redirect_uri": KAKAO_REDIRECT_URI,   # ★ 이 주소는 '백엔드 콜백 URL'
        "response_type": "code",
        # "scope": "account_email"  # 필요 시 주석 해제
    }
    kakao_auth_url = f"{base_url}?{urllib.parse.urlencode(params)}"
    return {"auth_url": kakao_auth_url}


# ---------- 2) 카카오 콜백: 자동 회원가입 + 로그인 ----------
# ★ response_model 제거 (이제 RedirectResponse를 리턴함)
@router.get("/kakao/callback")
def kakao_callback(code: str, db: Session = Depends(get_db)):
    """
    카카오에서 redirect_uri로 넘겨주는 code를 받아서:
      1) access_token 발급
      2) 사용자 정보 조회
      3) 우리 DB에 사용자 생성 or 조회
      4) JWT(access_token) 발급 후 프론트로 리다이렉트
    """
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="인가 코드(code)가 없습니다.",
        )

    # 1) code -> access_token 교환
    token_url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "authorization_code",
        "client_id": KAKAO_CLIENT_ID,
        "redirect_uri": KAKAO_REDIRECT_URI,
        "code": code,
        # "client_secret": os.getenv("KAKAO_CLIENT_SECRET", "")
    }

    token_res = requests.post(token_url, data=data)
    if token_res.status_code != 200:
        print("[KAKAO TOKEN ERROR]", token_res.text)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="카카오 토큰 요청에 실패했습니다.",
        )

    token_json = token_res.json()
    kakao_access_token: Optional[str] = token_json.get("access_token")
    if not kakao_access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="카카오 액세스 토큰이 없습니다.",
        )

    # 2) access_token으로 사용자 정보 조회
    user_info_res = requests.get(
        "https://kapi.kakao.com/v2/user/me",
        headers={"Authorization": f"Bearer {kakao_access_token}"},
    )
    if user_info_res.status_code != 200:
        print("[KAKAO USER INFO ERROR]", user_info_res.text)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="카카오 사용자 정보 조회에 실패했습니다.",
        )

    kakao_user = user_info_res.json()
    kakao_id = str(kakao_user.get("id"))  # 카카오 고유 유저 ID
    if not kakao_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="카카오 사용자 ID를 가져오지 못했습니다.",
        )

    kakao_account = kakao_user.get("kakao_account", {}) or {}
    profile = kakao_account.get("profile", {}) or {}

    nickname = profile.get("nickname") or "카카오유저"
    birth_year = None  # 필요하면 나중에 확장

    # 3) DB에서 이 카카오 계정이 이미 존재하는지 확인
    user = (
        db.query(models.User)
        .filter(
            models.User.social_provider == "kakao",
            models.User.social_id == kakao_id,
        )
        .first()
    )

    # 3-1) 첫 로그인: 자동 회원가입
    if not user:
        user = models.User(
            social_provider="kakao",
            social_id=kakao_id,
            nickname=nickname,
            user_type="YOUNG",
            hashed_password=None,  # 소셜로그인 전용
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # 4) 우리 서비스용 JWT 발급
    access_token = create_access_token(data={"sub": str(user.user_id)})

    # 5) 프론트로 리다이렉트 (쿼리스트링으로 토큰 전달)
    redirect_url = f"{FRONTEND_LOGIN_SUCCESS_URL}?token={access_token}"
    return RedirectResponse(url=redirect_url, status_code=302)


# ---------- 3) 프론트가 카카오 정보를 직접 보내는 방식 (POST) ----------
# 이 방식은 '프론트에서 kakao JS SDK로 userInfo 까지 받고 보내는' 플로우용.
# 지금은 안 쓸 수도 있지만, 혹시 몰라 유지.
@router.post("/kakao/callback", response_model=schemas.Token)
def kakao_callback_direct(payload: dict, db: Session = Depends(get_db)):
    """
    프론트에서 kakaoLogin()으로 받아온 사용자 정보를 직접 전달하는 방식.
    code 없이 바로 회원 생성 + JWT 발급.
    """
    kakao_id = str(payload.get("kakao_id"))
    nickname = payload.get("nickname")

    if not kakao_id:
        raise HTTPException(
            status_code=400,
            detail="kakao_id가 전달되지 않았습니다."
        )

    # DB에서 유저 조회
    user = (
        db.query(models.User)
        .filter(
            models.User.social_provider == "kakao",
            models.User.social_id == kakao_id
        )
        .first()
    )

    # 없다면 자동 회원가입
    if not user:
        user = models.User(
            social_provider="kakao",
            social_id=kakao_id,
            nickname=nickname or "카카오유저",
            user_type="YOUNG"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # JWT 토큰 생성
    access_token = create_access_token(data={"sub": str(user.user_id)})

    return schemas.Token(
        access_token=access_token,
        token_type="bearer"
    )
