from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
import os
import urllib.parse
import requests

from dotenv import load_dotenv
load_dotenv()

from fastapi.responses import RedirectResponse
from app import models, schemas
from app.deps import get_db, create_access_token

router = APIRouter()

# 환경변수에서 카카오 앱 정보 가져오기
KAKAO_CLIENT_ID: str = os.getenv("KAKAO_CLIENT_ID", "")
KAKAO_REDIRECT_URI: str = os.getenv("KAKAO_REDIRECT_URI", "")

print("DEBUG KAKAO_CLIENT_ID:", KAKAO_CLIENT_ID)
print("DEBUG KAKAO_REDIRECT_URI:", KAKAO_REDIRECT_URI)


# 카카오 로그인 URL
@router.get("/kakao/login")
def kakao_login_url():
    base_url = "https://kauth.kakao.com/oauth/authorize"
    params = {
        "client_id": KAKAO_CLIENT_ID,
        "redirect_uri": KAKAO_REDIRECT_URI,
        "response_type": "code",
        "prompt": "login" 
    }
    kakao_auth_url = f"{base_url}?{urllib.parse.urlencode(params)}"
    return {"auth_url": kakao_auth_url}


# 카카오 콜백
@router.get("/kakao/callback")
def kakao_callback(code: Optional[str] = None,  
    db: Session = Depends(get_db)):

    if not code:
        raise HTTPException(
            status_code=400,
            detail="인가 코드(code)가 없습니다.",
        )

    # access_token
    token_url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "authorization_code",
        "client_id": KAKAO_CLIENT_ID,
        "redirect_uri": KAKAO_REDIRECT_URI,
        "code": code,
    }

    token_res = requests.post(token_url, data=data)
    if token_res.status_code != 200:
        print("[KAKAO TOKEN ERROR]", token_res.text)
        raise HTTPException(status_code=400, detail="카카오 토큰 요청 실패")

    token_json = token_res.json()
    kakao_access_token = token_json.get("access_token")
    if not kakao_access_token:
        raise HTTPException(status_code=400, detail="카카오 액세스 토큰 없음")

    # 사용자 정보 조회
    user_info_res = requests.get(
        "https://kapi.kakao.com/v2/user/me",
        headers={"Authorization": f"Bearer {kakao_access_token}"},
    )

    if user_info_res.status_code != 200:
        print("[KAKAO USER INFO ERROR]", user_info_res.text)
        raise HTTPException(status_code=400, detail="사용자 정보 조회 실패")

    kakao_user = user_info_res.json()
    kakao_id = str(kakao_user.get("id"))

    kakao_account = kakao_user.get("kakao_account", {}) or {}
    profile = kakao_account.get("profile", {}) or {}

    email = kakao_account.get("email")
    nickname = profile.get("nickname") or "카카오유저"

    # DB
    user = (
        db.query(models.User)
        .filter(
            models.User.social_provider == "kakao",
            models.User.social_id == kakao_id,
        )
        .first()
    )

    if not user:
        user = models.User(
            social_provider="kakao",
            social_id=kakao_id,
            nickname=nickname,
            email=email,
            birth_year=None,
            hashed_password=None,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # JWT 발급
    service_token = create_access_token(data={"sub": str(user.user_id)})

    # React 리다이렉트
    redirect_url = f"http://localhost:3000/auth/kakao/callback?token={service_token}"
    return RedirectResponse(url=redirect_url)
