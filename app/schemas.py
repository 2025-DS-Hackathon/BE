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
