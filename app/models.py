# app/models.py
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime

from .db import Base


# ===========================
# USER TABLE
# ===========================
class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)

    # 소셜 + 기본 정보
    email = Column(String, nullable=True, unique=True)
    nickname = Column(String, nullable=False)

    # 소셜 로그인 정보 (카카오)
    social_provider = Column(String, nullable=True)
    social_id = Column(String, nullable=True, unique=True)

    # (ID/PW 로그인 확장 대비)
    hashed_password = Column(String, nullable=True)

    # 출생연도 (서비스에서 직접 입력받음)
    birth_year = Column(Integer, nullable=True)

    # 세대 구분: YOUNG / SENIOR / MIDDLE / UNKNOWN
    user_type = Column(String, nullable=False, default="UNKNOWN")

    # 약관 관련
    terms_agreed = Column(Boolean, default=False)
    terms_agreed_at = Column(DateTime, nullable=True)
    terms_version = Column(String, default="v1")

    # 기타 상태
    noshow_count = Column(Integer, default=0)
    user_status = Column(String, default="NORMAL")  # NORMAL / SUSPENDED / DELETED
    is_matching_available = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # 관계
    talents = relationship(
        "Talent", back_populates="user", cascade="all, delete-orphan"
    )
    sent_messages = relationship("Message", back_populates="sender")
    notifications = relationship("Notification", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.user_id}, nickname={self.nickname})>"


# ===========================
# TALENT TABLE
# ===========================
class Talent(Base):
    __tablename__ = "talents"

    talent_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)

    type = Column(String, nullable=False)       # "Teach" / "Learn"
    category = Column(String, nullable=False)
    title = Column(String, nullable=False)
    tags = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="talents")

    def __repr__(self):
        return f"<Talent(id={self.talent_id}, user_id={self.user_id}, title={self.title})>"


# ===========================
# MATCHING TABLE (Queue)
# ===========================

class Match(Base):
    __tablename__ = "matches"

    match_id = Column(Integer, primary_key=True, index=True)
    user_a_id = Column(Integer, ForeignKey("users.user_id"))
    user_b_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)

    status = Column(String, default="대기")  # 대기 / 합의 / 확정 / 취소
    requested_at = Column(DateTime, default=datetime.utcnow)

    a_consent = Column(Boolean, default=None)  # True / False / None
    b_consent = Column(Boolean, default=None)

    shared_category = Column(String, nullable=True)


class MatchingQueue(Base):
    __tablename__ = "matching_queue"

    match_id = Column(Integer, primary_key=True, index=True)
    user_a_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    user_b_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)

    # PENDING(대기) / CONFIRMED(짝 찾음, 합의 대기) /
    # SUCCESS(양쪽 O, 최종 매칭) / CANCELED(만료/취소)
    status = Column(String, default="PENDING")
    a_consent = Column(Boolean, nullable=True)
    b_consent = Column(Boolean, nullable=True)
    shared_category = Column(String, nullable=True)

    requested_at = Column(DateTime, server_default=func.now())
    confirmed_at = Column(DateTime, nullable=True)
    canceled_at = Column(DateTime, nullable=True)

    # 관계
    user_a = relationship("User", foreign_keys=[user_a_id], backref="matches_as_a")
    user_b = relationship("User", foreign_keys=[user_b_id], backref="matches_as_b")
    messages = relationship(
        "Message", back_populates="match", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Match(id={self.match_id}, status={self.status})>"


# ===========================
# MESSAGE TABLE
# ===========================
class ChatRoom(Base):
    __tablename__ = "chat_rooms"

    room_id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matching_queue.match_id"), unique=True)
    user_a_id = Column(Integer, ForeignKey("users.user_id"))
    user_b_id = Column(Integer, ForeignKey("users.user_id"))
    shared_category = Column(String)
    last_message_at = Column(DateTime)

    # 관계 설정
    messages = relationship("Message", back_populates="chat_room")


class Message(Base):
    __tablename__ = "messages"

    message_id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("chat_rooms.room_id"))
    sender_id = Column(Integer, ForeignKey("users.user_id"))
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    chat_room = relationship("ChatRoom", back_populates="messages")
    sender = relationship("User")


#class Message(Base):
#    __tablename__ = "messages"

#    message_id = Column(Integer, primary_key=True, index=True)
#    match_id = Column(Integer, ForeignKey("matching_queue.match_id"), nullable=False)
#    sender_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)

#    content = Column(Text, nullable=False)
#    is_read = Column(Boolean, default=False)
#    timestamp = Column(DateTime, server_default=func.now())
#
#    match = relationship("MatchingQueue", back_populates="messages")
#    sender = relationship("User", back_populates="sent_messages")
#
#    def __repr__(self):
#        return f"<Message(id={self.message_id}, match_id={self.match_id})>"

# ===========================
# NOTIFICATION TABLE
# ===========================
class Notification(Base):
    __tablename__ = "notifications"

    notif_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)

    # type 예시:
    #  - NEW_MESSAGE      : 새 쪽지
    #  - MATCH_FOUND      : 대기열에서 짝을 찾았을 때 (합의 대기)
    #  - MATCH_SUCCESS    : 양쪽 O, 최종 매칭 확정
    #  - MATCH_FAIL       : 24시간 만료로 매칭 실패
    #  - MATCH_CANCELED   : X 눌러서 매칭 취소
    type = Column(String, nullable=False)

    content = Column(String, nullable=False)
    # 클릭 시 프론트에서 이동할 경로 (예: "/messages/123")
    link_path = Column(String, nullable=True)

    is_read = Column(Boolean, default=False)
    timestamp = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="notifications")

    def __repr__(self):
        return f"<Notification(id={self.notif_id}, user_id={self.user_id}, type={self.type})>"
