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


# ===========================
# USER TABLE
# ===========================
class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    nickname = Column(String, nullable=False)
    birth_year = Column(Integer, nullable=False)
    user_type = Column(String, nullable=False)  # "YOUNG" / "SENIOR"
    noshow_count = Column(Integer, default=0)
    user_status = Column(String, default="NORMAL")  # NORMAL / SUSPENDED / DELETED
    is_matching_available = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 선택: 편의를 위한 관계 설정 (필수는 아님)
    talents = relationship("Talent", back_populates="user", cascade="all, delete-orphan")
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
class MatchingQueue(Base):
    __tablename__ = "matching_queue"

    match_id = Column(Integer, primary_key=True, index=True)
    user_a_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    user_b_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)

    status = Column(String, default="PENDING")  # PENDING / CONFIRMED / CANCELED
    a_consent = Column(Boolean, nullable=True)
    b_consent = Column(Boolean, nullable=True)
    shared_category = Column(String, nullable=True)

    requested_at = Column(DateTime, server_default=func.now())
    confirmed_at = Column(DateTime, nullable=True)
    canceled_at = Column(DateTime, nullable=True)

    # 관계 (필요하면 사용, 안 써도 상관 없음)
    user_a = relationship("User", foreign_keys=[user_a_id], backref="matches_as_a")
    user_b = relationship("User", foreign_keys=[user_b_id], backref="matches_as_b")
    messages = relationship("Message", back_populates="match", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Match(id={self.match_id}, status={self.status})>"


# ===========================
# MESSAGE TABLE
# ===========================
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


# ===========================
# NOTIFICATION TABLE
# ===========================
class Notification(Base):
    __tablename__ = "notifications"

    notif_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)

    type = Column(String, nullable=False)       # MATCH_SUCCESS / MESSAGE / SYSTEM / MATCH_FAIL ...
    content = Column(String, nullable=False)
    link_path = Column(String, nullable=True)
    is_read = Column(Boolean, default=False)
    timestamp = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="notifications")

    def __repr__(self):
        return f"<Notification(id={self.notif_id}, user_id={self.user_id}, type={self.type})>"
