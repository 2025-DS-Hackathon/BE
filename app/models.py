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

from .db import Base


# USER TABLE
class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)

    # 기본 정보
    email = Column(String, nullable=True, unique=True)
    nickname = Column(String, nullable=False)

    # 로그인 정보 (카카오)
    social_provider = Column(String, nullable=True)
    social_id = Column(String, nullable=True, unique=True)

    # (로그인 확장 대비)
    hashed_password = Column(String, nullable=True)

    # 출생연도 
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


    talents = relationship(
        "Talent", back_populates="user", cascade="all, delete-orphan"
    )
    sent_messages = relationship("Message", back_populates="sender")
    notifications = relationship("Notification", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.user_id}, nickname={self.nickname})>"


# TALENT TABLE
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


# MATCHING TABLE (Queue)
class MatchingQueue(Base):
    __tablename__ = "matching_queue"

    match_id = Column(Integer, primary_key=True, index=True)
    user_a_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    user_b_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)

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


# MESSAGE TABLE
class Message(Base):
    __tablename__ = "messages"

    message_id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matching_queue.match_id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)

    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    timestamp = Column(DateTime, server_default=func.now())

    match = relationship("MatchingQueue", back_populates="messages")
    sender = relationship("User", back_populates="sent_messages")

    def __repr__(self):
        return f"<Message(id={self.message_id}, match_id={self.match_id})>"


# NOTIFICATION TABLE
class Notification(Base):
    __tablename__ = "notifications"

    notif_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    type = Column(String, nullable=False)

    content = Column(String, nullable=False)
    link_path = Column(String, nullable=True)

    is_read = Column(Boolean, default=False)
    timestamp = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="notifications")

    def __repr__(self):
        return f"<Notification(id={self.notif_id}, user_id={self.user_id}, type={self.type})>"
