# app/schemas.py
from enum import Enum
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, validator

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
    terms_agreed_at: Optional[datetime] = None  
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
    category: str   
    title: str     
    tags: Optional[str] = None 
    description: str
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# --- Talent ---
class TalentCreate(BaseModel):
    type: str  # 'Teach' or 'Learn'
    category: str
    title: str
    tags: Optional[str] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True


class MyTalentSummaryResponse(BaseModel):
    learn: Optional[TalentSummary] = None
    teach: Optional[TalentSummary] = None



# MATCHING 관련 스키마
class MatchStartResult(str, Enum):
    QUEUED = "QUEUED"
    ALREADY_WAITING = "ALREADY_WAITING"
    MIDDLE_USER = "MIDDLE_USER"
    NO_TALENT = "NO_TALENT"
    MATCHED_IMMEDIATELY = "MATCHED_IMMEDIATELY"


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
    tags: Optional[str] = None 
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
    desired_category: Optional[str] = None

class MatchAnswerIn(BaseModel):
    consent: bool

class MatchOut(BaseModel):
    match_id: int
    user_a_id: int
    user_b_id: Optional[int]
    status: str
    requested_at: datetime
    a_consent: bool
    b_consent: bool
    shared_category: Optional[str]

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


class MatchDetailResponse(BaseModel):
    match_id: int
    # 내 재능 (내가 줄 것)
    my_talent: Optional[TalentSummary] = None
    # 상대방 재능 (내가 받을 것)
    partner_talent: Optional[TalentSummary] = None
    
    status: str     # 매칭 상태 (WAITING, ACTIVE 등)
    partner_nickname: str # 상대방 닉네임