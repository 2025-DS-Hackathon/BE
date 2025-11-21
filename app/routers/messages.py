# app/routers/messages.py
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from app import models, schemas
from app.deps import get_db, get_active_user

router = APIRouter(prefix="/messages", tags=["messages"])

@router.get("/ping")
def ping_messages():
    return {"area": "messages", "status": "ok"}

#쪽지 목록
@router.get("", response_model=List[schemas.ChatSummary])
def list_chats(db: Session = Depends(get_db), current_user: models.User = Depends(get_active_user)):
    """
    반환: 사용자와 CONFIRMED 상태인 매칭들에 대해, 상대방 정보 + 최근 메시지 + 읽지 않은 개수
    최신순 정렬(가장 최근 메시지 기준).
    차단된 상대는 목록에서 제외.
    """
    matches = (
        db.query(models.MatchingQueue)
        .filter(
            models.MatchingQueue.status == "CONFIRMED",
            ((models.MatchingQueue.user_a_id == current_user.user_id) | (models.MatchingQueue.user_b_id == current_user.user_id))
        )
        .all()
    )

    results: List[schemas.ChatSummary] = []
    for m in matches:
        partner_id = m.user_b_id if m.user_a_id == current_user.user_id else m.user_a_id
        partner = db.query(models.User).get(partner_id)
        if not partner:
            continue

        # 차단 검사
        blocked = db.query(models.Block).filter(
            ((models.Block.blocker_id == current_user.user_id) & (models.Block.blocked_id == partner_id)) |
            ((models.Block.blocker_id == partner_id) & (models.Block.blocked_id == current_user.user_id))
        ).first()
        if blocked:
            continue

        # 최근 메시지
        last_msg = (
            db.query(models.Message)
            .filter(models.Message.match_id == m.match_id)
            .order_by(models.Message.timestamp.desc())
            .first()
        )

        # unread count (messages where recipient is current_user and is_read = False)
        unread_count = db.query(models.Message).filter(
            models.Message.match_id == m.match_id,
            models.Message.sender_id != current_user.user_id,
            models.Message.is_read == False
        ).count()

        results.append(
            schemas.ChatSummary(
                match_id=m.match_id,
                partner_id=partner.user_id,
                partner_nickname=partner.nickname,
                partner_profile_image=getattr(partner, "profile_image", None),
                shared_category=m.shared_category,
                last_message=last_msg.content if last_msg else None,
                last_message_time=last_msg.timestamp if last_msg else None,
                unread_count=unread_count,
            )
        )

    # 정렬: 최신 메시지 시간 기준 내림차순
    results.sort(key=lambda x: x.last_message_time or datetime.min, reverse=True)
    return results


# --- 쪽지 상세 ---
@router.get("/{match_id}", response_model=List[schemas.MessageItem])
def get_chat_detail(match_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_active_user)):
    """
    대화 상세: match_id 기준 메시지 전체를 시간순으로 반환.
    수신자 측에서 메시지를 읽으면 is_read=True로 변경.
    """
    match = db.query(models.MatchingQueue).filter(models.MatchingQueue.match_id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="매칭 정보를 찾을 수 없습니다.")

    # 당사자 확인
    if current_user.user_id not in (match.user_a_id, match.user_b_id):
        raise HTTPException(status_code=403, detail="이 대화의 당사자가 아닙니다.")

    # 차단 확인 (전송 제한은 send endpoint에서 처리)
    partner_id = match.user_b_id if current_user.user_id == match.user_a_id else match.user_a_id
    # blocked 변수는 안내문구용으로 프론트에 전달하고 싶으면 반환 포맷을 확장하면 됨.
    blocked = db.query(models.Block).filter(
        ((models.Block.blocker_id == current_user.user_id) & (models.Block.blocked_id == partner_id)) |
        ((models.Block.blocker_id == partner_id) & (models.Block.blocked_id == current_user.user_id))
    ).first()

    msgs = db.query(models.Message).filter(models.Message.match_id == match_id).order_by(models.Message.timestamp.asc()).all()

    # 읽음 처리: 현재 사용자가 '수신자'인 메시지 중 is_read=False -> True로 변경
    changed = False
    for m in msgs:
        if m.sender_id != current_user.user_id and not m.is_read:
            m.is_read = True
            db.add(m)
            changed = True

    if changed:
        db.commit()

    return msgs


# --- 쪽지 전송 API ---
@router.post("/{match_id}", response_model=schemas.SendMessageResponse)
def send_message(match_id: int, req: schemas.SendMessageRequest, db: Session = Depends(get_db), current_user: models.User = Depends(get_active_user)):
    """
    - 차단 여부 검사
    - 메시지 저장 (commit 포함)
    - recipient 에 Notification 생성 (뱃지)
    """
    match = db.query(models.MatchingQueue).filter(models.MatchingQueue.match_id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="매칭 정보를 찾을 수 없습니다.")

    # 당사자 확인
    if current_user.user_id not in (match.user_a_id, match.user_b_id):
        raise HTTPException(status_code=403, detail="이 매칭의 당사자가 아닙니다.")

    # 송신 금지: 차단된 경우
    partner_id = match.user_b_id if current_user.user_id == match.user_a_id else match.user_a_id
    if db.query(models.Block).filter(models.Block.blocker_id == partner_id, models.Block.blocked_id == current_user.user_id).first():
        raise HTTPException(status_code=403, detail="차단된 사용자 입니다. 쪽지를 전송할 수 없습니다.")
    if db.query(models.Block).filter(models.Block.blocker_id == current_user.user_id, models.Block.blocked_id == partner_id).first():
        raise HTTPException(status_code=403, detail="차단된 사용자 입니다. 쪽지를 전송할 수 없습니다.")

    # 메시지 저장 (commit 필수)
    msg = models.Message(
        match_id=match_id,
        sender_id=current_user.user_id,
        content=req.content,
        is_read=False,
    )
    db.add(msg)

    # 알림 생성: 수신자에게 (NEW_MESSAGE 타입)
    notif = models.Notification(
        user_id=partner_id,
        type="NEW_MESSAGE",
        content=f"{current_user.nickname}님으로부터 새로운 쪽지가 도착했습니다.",
        link_path=f"/messages/{match_id}",
        is_read=False,
    )
    db.add(notif)

    # DB 반영
    db.commit()
    db.refresh(msg)

    # 응답 (schemas.SendMessageResponse 가 정의되어 있어야 함)
    return schemas.SendMessageResponse(message=msg)


# --- 신고 처리 ---
@router.post("/{match_id}/report")
def report_user(match_id: int, req: schemas.ReportRequest, db: Session = Depends(get_db), current_user: models.User = Depends(get_active_user)):
    match = db.query(models.MatchingQueue).filter(models.MatchingQueue.match_id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="매칭 정보를 찾을 수 없습니다.")
    if current_user.user_id not in (match.user_a_id, match.user_b_id):
        raise HTTPException(status_code=403, detail="이 매칭의 당사자가 아닙니다.")

    reported_id = match.user_b_id if current_user.user_id == match.user_a_id else match.user_a_id

    # Report model fields: reported_id, match_id, reason, description
    report = models.Report(
        reporter_id=current_user.user_id,
        reported_id=reported_id,
        match_id=match_id,
        reason=req.reason,
        description=getattr(req, "description", None),
    )
    db.add(report)
    db.commit()

    # 신고 누적 체크: 3회 이상이면 영구정지 처리
    report_count = db.query(models.Report).filter(models.Report.reported_id == reported_id).count()
    if report_count >= 3:
        user = db.query(models.User).get(reported_id)
        if user:
            user.user_status = "BANNED"
            user.is_matching_available = False
            db.add(user)
            db.commit()

    return {"result": "OK", "message": "신고가 접수되었습니다."}


# --- 차단 처리 ---
@router.post("/{match_id}/block", response_model=schemas.BlockResponse)
def block_user(match_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_active_user)):
    match = db.query(models.MatchingQueue).filter(models.MatchingQueue.match_id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="매칭 정보를 찾을 수 없습니다.")
    if current_user.user_id not in (match.user_a_id, match.user_b_id):
        raise HTTPException(status_code=403, detail="이 매칭의 당사자가 아닙니다.")

    blocked_id = match.user_b_id if current_user.user_id == match.user_a_id else match.user_a_id

    # 이미 차단되어 있으면 무시
    existing = db.query(models.Block).filter(models.Block.blocker_id == current_user.user_id, models.Block.blocked_id == blocked_id).first()
    if existing:
        return schemas.BlockResponse(result="OK", message="차단이 이미 완료되어 있습니다.")

    block = models.Block(blocker_id=current_user.user_id, blocked_id=blocked_id)
    db.add(block)
    db.commit()

    return schemas.BlockResponse(result="OK", message="차단이 완료되었습니다.")


@router.post("/{match_id}/mark-read")
def mark_read(match_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_active_user)):
    match = db.query(models.MatchingQueue).filter(models.MatchingQueue.match_id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="매칭 정보를 찾을 수 없습니다.")
    if current_user.user_id not in (match.user_a_id, match.user_b_id):
        raise HTTPException(status_code=403, detail="이 매칭의 당사자가 아닙니다.")

    updated = False
    messages = db.query(models.Message).filter(
        models.Message.match_id == match_id,
        models.Message.sender_id != current_user.user_id,
        models.Message.is_read == False
    ).all()
    for m in messages:
        m.is_read = True
        db.add(m)
        updated = True
    if updated:
        db.commit()
    return {"result": "OK", "updated": len(messages)}
