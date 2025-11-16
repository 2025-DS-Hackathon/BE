# app/routers/notifications.py
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.deps import get_db, get_current_user

router = APIRouter()


# 1) 내 알림 리스트 조회
@router.get("/", response_model=List[schemas.NotificationRead])
def list_notifications(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    현재 로그인한 사용자의 알림 목록 조회
    - 기본: 최신 순 정렬
    - 추후: limit/offset 등 페이징 파라미터 추가 가능
    """
    notifications = (
        db.query(models.Notification)
        .filter(models.Notification.user_id == current_user.user_id)
        .order_by(models.Notification.timestamp.desc())
        .all()
    )
    return notifications


# 2) 안 읽은 알림 개수 조회
@router.get("/unread-count", response_model=schemas.NotificationUnreadCount)
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    헤더 뱃지 표시용: 읽지 않은(is_read=False) 알림 개수 반환
    """
    count = (
        db.query(models.Notification)
        .filter(
            models.Notification.user_id == current_user.user_id,
            models.Notification.is_read == False,  # noqa: E712
        )
        .count()
    )
    return schemas.NotificationUnreadCount(unread_count=count)


# 3) 단일 알림 읽음 처리 (선택 기능)
@router.patch("/{notif_id}/read", response_model=schemas.NotificationRead)
def mark_notification_read(
    notif_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    특정 알림을 읽음 상태로 변경
    - 사용자가 알림을 클릭했을 때 호출
    """
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
