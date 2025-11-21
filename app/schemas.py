# app/schemas.py
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime


# ===========================
# USER 관련 스키마
# ===========================
class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    nickname: str
    birth_year: Optional[int] = None
    user_type: str  # 'YOUNG' / 'SENIOR' / 'MIDDLE' / 'UNKNOWN'


class UserRead(UserBase):
    user_id: int
    noshow_count: int
    user_status: str
    is_matching_available: bool

    social_provider: Optional[str] = None
    social_id: Optional[str] = None

    terms_agreed: bool
    terms_agreed_at: Optional[str] = None
    terms_version: str

    class Config:
        orm_mode = True


class Token(BaseModel):
    access_token: str
    token_type: str


class UserProfileUpdate(BaseModel):
    birth_year: int
    terms_agreed: bool


# ===========================
# NOTIFICATION 스키마
# ===========================
class NotificationType(str, Enum):
    NEW_MESSAGE = "NEW_MESSAGE"
    MATCH_FOUND = "MATCH_FOUND"
    MATCH_SUCCESS = "MATCH_SUCCESS"
    MATCH_FAIL = "MATCH_FAIL"
    MATCH_CANCELED = "MATCH_CANCELED"


class NotificationRead(BaseModel):
    notif_id: int
    type: str
    content: str
    link_path: Optional[str] = None
    is_read: bool
    timestamp: str

    class Config:
        orm_mode = True


class NotificationUnreadCount(BaseModel):
    unread_count: int


# ===========================
# TALENT 요약 (메인/마이페이지용)
# ===========================
class TalentSummary(BaseModel):
    talent_id: int
    type: str

# --- Talent ---
class TalentCreate(BaseModel):
    type: str  # 'Teach' or 'Learn'
    category: str
    title: str
    tags: Optional[str] = None
    description: Optional[str] = None

    class Config:
        orm_mode = True


class MyTalentSummaryResponse(BaseModel):
    learn: Optional[TalentSummary] = None
    teach: Optional[TalentSummary] = None


# ===========================
# MATCHING 관련 스키마
# ===========================
class MatchStartResult(str, Enum):
    QUEUED = "QUEUED"
    ALREADY_WAITING = "ALREADY_WAITING"
    MIDDLE_USER = "MIDDLE_USER"
    NO_TALENT = "NO_TALENT"
    MATCHED_IMMEDIATELY = "MATCHED_IMMEDIATELY"
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
    match_id: Optional[int] = None


class TodayMatchStats(BaseModel):
    date: str              # "YYYY-MM-DD"
    matched_pairs: int     # 오늘 CONFIRMED 된 매칭 수


class MatchAgreementRequest(BaseModel):
    is_agreed: bool  # O(동의) / X(거절)


class MatchAgreementResponse(BaseModel):
    status: str      # PENDING / CONFIRMED / SUCCESS / CANCELED
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
class TalentOut(TalentCreate):
    talent_id: int
    user_id: int

    class Config:
        orm_mode = True

# --- Matching ---
class MatchRequestIn(BaseModel):
    # 요청할 때 사용자의 'learn' 카테고리를 명시 (UI에선 사용자가 이미 등록한 값 사용)
    # 그러나 서버에서는 DB에서 확인; 이 필드는 선택적 보조용.
    desired_category: Optional[str] = None

class MatchAnswerIn(BaseModel):
    # 현재 사용자가 선택한 동의 여부 (O -> true, X -> false)
    consent: bool

# ----- 매칭 응답  ------        
class MatchOut(BaseModel):
    match_id: int
    user_a_id: int
    user_b_id: Optional[int]
    status: str
    requested_at: datetime
    a_consent: bool
    b_consent: bool
    a_consent: Optional[bool]
    b_consent: Optional[bool]
    shared_category: Optional[str]

    class Config:
        orm_mode = True

# ----- 매칭 성공/실패  ------
class ConsentChoice(str, Enum):
    YES = "O"
    NO = "X"    

class MatchConsentRequest(BaseModel):
    choice: ConsentChoice

class MatchConsentResponse(BaseModel):
    result: str
    message: str

class ChatSummary(BaseModel):
    match_id: int
    partner_id: int
    partner_nickname: str
    partner_profile_image: Optional[str] = None
    shared_category: Optional[str] = None
    last_message: Optional[str] = None
    last_message_time: Optional[datetime] = None
    unread_count: int = 0

    class Config:
        orm_mode = True

# --- Message ---
class MessageCreate(BaseModel):
    match_id: int
    content: str

class MessageOut(BaseModel):
    message_id: int
    match_id: int
    sender_id: int
    content: str
    is_read: bool
    timestamp: datetime

    class Config:
        orm_mode = True
        
class MessageItem(BaseModel):
    message_id: int
    sender_id: int
    content: str
    timestamp: datetime

    class Config:
        orm_mode = True

    
#---- 메세지 전송 요청 / 응답 -----
class SendMessageRequest(BaseModel):
    content: str
    
class SendMessageResponse(BaseModel):
    message: MessageOut

    class Config:
        orm_mode = True

# --- Notification ---
class NotificationOut(BaseModel):
    notif_id: int
    type: str
    content: str
    link_path: Optional[str]
    is_read: bool
    timestamp: datetime

    class Config:
        orm_mode = True

# ---- 신고 ----
class ReportCreate(BaseModel):
    reported_id: int
    match_id: int
    reason: str
    description: str | None = None

class ReportRequest(BaseModel):
    reason: str
    description: Optional[str] = None

# --- Block ---
class BlockResponse(BaseModel):
    result: str
    message: str

    class Config:
        orm_mode = True
