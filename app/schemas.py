# app/schemas.py
from enum import Enum
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime


# ---- User 관련 스키마 ----
class UserBase(BaseModel):
    # 카카오에서 이메일 제공에 동의하면 채워짐, 아니면 None
    email: Optional[EmailStr] = None
    nickname: str
    birth_year: Optional[int] = None
    user_type: str


class UserRead(UserBase):
    user_id: int
    noshow_count: int
    user_status: str
    is_matching_available: bool

    # 카카오 단일 로그인이라 항상 "kakao" + 카카오 user id
    social_provider: Optional[str] = None
    social_id: Optional[str] = None

    # 약관 관련 필드 추가
    terms_agreed: bool
    terms_agreed_at: Optional[str] = None  # ISO 문자열로 자동 변환됨
    terms_version: str

    class Config:
        orm_mode = True  # SQLAlchemy 객체 -> Pydantic 변환 허용


# ---- 토큰 응답 스키마 ----
class Token(BaseModel):
    access_token: str
    token_type: str


# ------ 프로필/약관 업데이트 스키마 ------
class UserProfileUpdate(BaseModel):
    birth_year: int
    terms_agreed: bool


# ------ 알림(Notification) 관련 스키마 ------
class NotificationRead(BaseModel):
    notif_id: int
    type: str
    content: str
    link_path: Optional[str] = None
    is_read: bool
    timestamp: str  # DateTime이 ISO 문자열로 직렬화됨

    class Config:
        orm_mode = True


class NotificationUnreadCount(BaseModel):
    unread_count: int

# ------ 재능(Talent) 요약 스키마 (메인 카드용) ------
class TalentSummary(BaseModel):
    talent_id: int
    type: str
    category: str
    title: str
    tags: Optional[str] = None
    description: Optional[str] = None

    class Config:
        orm_mode = True


class MyTalentSummaryResponse(BaseModel):
    # Learn / Teach 카드가 없으면 None
    learn: Optional[TalentSummary] = None
    teach: Optional[TalentSummary] = None

# ------ 매칭 시작 응답 스키마 (MAIN-2310 ~ 2320) ------
class MatchStartResult(str, Enum):
    QUEUED = "QUEUED"                      # 대기열에 정상 등록
    ALREADY_WAITING = "ALREADY_WAITING"   # 이미 대기 중
    MIDDLE_USER = "MIDDLE_USER"           # 중년(서비스 대상 아님)
    NO_TALENT = "NO_TALENT"               # 재능 카드 미등록
    MATCHED_IMMEDIATELY = "MATCHED_IMMEDIATELY"  # 바로 매칭 성사


class MatchStartResponse(BaseModel):
    result: MatchStartResult
    message: str
    match_id: Optional[int] = None   # 바로 매칭 성사되었거나, 대기열 row id


# ------ 매칭 통계 (MAIN-2400: 오늘 몇 팀 매칭됐는지) ------
class TodayMatchStats(BaseModel):
    date: str              # "YYYY-MM-DD"
    matched_pairs: int     # 오늘 CONFIRMED 된 매칭 수
    
# ------ 재능 카테고리 ------
class TalentCategory(str, Enum):
    DIGITAL_IT = "디지털/IT"
    COOKING = "요리/생활"
    HOBBY = "취미/예술"
    JOB_EXPERIENCE = "직무/경험"
    HEALTH_SPORT = "건강/운동"

# ------ 재능 타입 ------
class TalentType(str, Enum):
    TEACH = "Teach"
    LEARN = "Learn"

# ------ 재능 생성 요청 ------
class TalentCreate(BaseModel):
    type: TalentType
    category: TalentCategory
    title: str = Field(..., min_length=1)
    tags: Optional[str] = None  # 쉼표로 구분된 최대 3개 키워드
    description: Optional[str] = Field(default=None, max_length=300)

    @validator("tags")
    def check_tags(cls, v):
        if not v:
            return v
        tag_list = [t.strip() for t in v.split(",") if t.strip()]
        if len(tag_list) > 3:
            raise ValueError("태그는 최대 3개까지 입력 가능합니다.")
        return ",".join(tag_list)

# ------ 재능 생성 응답 ------
class TalentOut(BaseModel):
    talent_id: int
    user_id: int
    type: TalentType
    category: TalentCategory
    title: str
    tags: Optional[str]
    description: Optional[str]

    class Config:
        orm_mode = True

# ----- 매칭 응답  ------        
class MatchOut(BaseModel):
    match_id: int
    user_a_id: int
    user_b_id: Optional[int]
    status: str
    requested_at: datetime
    a_consent: Optional[bool]
    b_consent: Optional[bool]
    shared_category: Optional[str]

    class Config:
        orm_mode = True

# -----   ------
class ConsentChoice(str, Enum):
    YES = "O"
    NO = "X"

class MatchConsentRequest(BaseModel):
    choice: ConsentChoice

class MatchConsentResponse(BaseModel):
    result: str
    message: str
    
#--- 쪽지 ---
class ChatRoomSummary(BaseModel):
    room_id: int
    partner_nickname: str
    partner_profile_image: Optional[str]
    last_message: str
    last_message_time: Optional[datetime]

    class Config:
        from_attributes = True

class MessageItem(BaseModel):
    message_id: int
    sender_id: int
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatRoomDetail(BaseModel):
    room_id: int
    partner_nickname: str
    partner_profile_image: Optional[str]
    shared_category: str
    messages: List[MessageItem]
    
#---- 전송 요청 -----
class SendMessageRequest(BaseModel):
    content: str