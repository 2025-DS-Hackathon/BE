# app/routers/messages.py
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, or_, desc

from app import models, schemas
from app.deps import get_db, get_active_user

router = APIRouter()

@router.get("/ping")
def ping_messages():
    return {"area": "messages", "status": "ok"}

#쪽지 목록
@router.get("/rooms", response_model=List[schemas.ChatRoomSummary])
def get_chat_rooms(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_active_user)
):

    rooms = db.query(models.ChatRoom).filter(
        or_(
            models.ChatRoom.user_a_id == current_user.user_id,
            models.ChatRoom.user_b_id == current_user.user_id
        )
    ).order_by(desc(models.ChatRoom.last_message_at)).all()

    result = []

    for room in rooms:
        # 상대방 찾기
        partner_id = (
            room.user_a_id if room.user_a_id != current_user.user_id else room.user_b_id
        )
        partner = db.query(models.User).filter(models.User.user_id == partner_id).first()

        # 최근 메시지 가져오기
        last_msg = db.query(models.Message).filter(
            models.Message.room_id == room.room_id
        ).order_by(desc(models.Message.created_at)).first()

        result.append({
            "room_id": room.room_id,
            "partner_nickname": partner.nickname,
            "partner_profile_image": partner.profile_image,
            "last_message": last_msg.content if last_msg else "",
            "last_message_time": last_msg.created_at if last_msg else None,
        })

    return result

#쪽지 상세 페이지 API (대화창)
@router.get("/rooms/{room_id}", response_model=schemas.ChatRoomDetail)
def get_chat_room_detail(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_active_user)
):
    room = db.query(models.ChatRoom).filter(models.ChatRoom.room_id == room_id).first()

    if not room:
        raise HTTPException(status_code=404, detail="존재하지 않는 채팅방")

    # 접근 권한 체크
    if current_user.user_id not in [room.user_a_id, room.user_b_id]:
        raise HTTPException(status_code=403, detail="권한이 없습니다.")

    partner_id = (
        room.user_a_id if room.user_a_id != current_user.user_id else room.user_b_id
    )
    partner = db.query(models.User).get(partner_id)

    messages = db.query(models.Message).filter(
        models.Message.room_id == room_id
    ).order_by(models.Message.created_at).all()

    return {
        "room_id": room.room_id,
        "partner_nickname": partner.nickname,
        "partner_profile_image": partner.profile_image,
        "shared_category": room.shared_category,
        "messages": messages,
    }

#메세지 전송 API
@router.post("/rooms/{room_id}", response_model=schemas.MessageItem)
def send_message(
    room_id: int,
    request: schemas.SendMessageRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_active_user)
):

    room = db.query(models.ChatRoom).filter(models.ChatRoom.room_id == room_id).first()

    if not room:
        raise HTTPException(status_code=404, detail="채팅방을 찾을 수 없습니다.")

    if current_user.user_id not in [room.user_a_id, room.user_b_id]:
        raise HTTPException(status_code=403, detail="권한이 없습니다.")

    # 메시지 저장
    msg = models.Message(
        room_id=room_id,
        sender_id=current_user.user_id,
        content=request.content,
    )
    db.add(msg)

    # 최신 메시지 시간 반영
    room.last_message_at = datetime.utcnow()
    db.add(room)
    db.commit()
    db.refresh(msg)

    # 상대방에게 알림
    partner_id = (
        room.user_a_id if room.user_a_id != current_user.user_id else room.user_b_id
    )
    db.add(models.Notification(
        user_id=partner_id,
        type="NEW_MESSAGE",
        content=f"{current_user.nickname}님이 새 메시지를 보냈습니다.",
        is_read=False
    ))

    db.commit()

    return msg
