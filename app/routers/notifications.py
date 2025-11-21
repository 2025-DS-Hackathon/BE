from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.deps import get_db, get_current_user

router = APIRouter()


# ------------------------------
# 내 알림 리스트 조회
# ------------------------------
@router.get("/", response_model=List[schemas.NotificationRead])
def list_notifications(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    notifications = (
        db.query(models.Notification)
        .filter(models.Notification.user_id == current_user.user_id)
        .order_by(models.Notification.timestamp.desc())
        .all()
    )
    return notifications


# ------------------------------
# 안 읽은 알림 개수 조회
# ------------------------------
@router.get("/unread-count", response_model=schemas.NotificationUnreadCount)
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    count = (
        db.query(models.Notification)
        .filter(
            models.Notification.user_id == current_user.user_id,
            models.Notification.is_read.is_(False),
        )
        .count()
    )
    return schemas.NotificationUnreadCount(unread_count=count)


# ------------------------------
# 알림 전체 읽음 처리 
# ------------------------------
@router.patch("/mark-all-read", response_model=schemas.NotificationUnreadCount)
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    (
        db.query(models.Notification)
        .filter(
            models.Notification.user_id == current_user.user_id,
            models.Notification.is_read.is_(False),
        )
        .update({models.Notification.is_read: True})
    )
    db.commit()
    return schemas.NotificationUnreadCount(unread_count=0)


# ------------------------------
# 단일 알림 읽음 처리 
# ------------------------------
@router.patch("/{notif_id}/read", response_model=schemas.NotificationRead)
def mark_notification_read(
    notif_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    notif = (
        db.query(models.Notification)
        .filter(
            models.Notification.notif_id == notif_id,
            models.Notification.user_id == current_user.user_id,
        )
        .first()
    )

    if not notif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="알림을 찾을 수 없습니다.",
        )

    if not notif.is_read:
        notif.is_read = True
        db.add(notif)
        db.commit()
        db.refresh(notif)

    return notif
