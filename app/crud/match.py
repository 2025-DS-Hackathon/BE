from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app import models

def get_pending_match_by_user(db: Session, user_id: int):
    """
    user_a 또는 user_b 로 참여한 PENDING/AGREEMENT 상태의 매칭 반환
    """
    return (
        db.query(models.MatchingQueue)
        .filter(
            or_(
                models.MatchingQueue.user_a_id == user_id,
                models.MatchingQueue.user_b_id == user_id,
            ),
            models.MatchingQueue.status.in_(["PENDING", "AGREEMENT"])
        )
        .first()
    )

def create_match_request(db: Session, user_id: int, desired_category: str = None):
    """
    A 구조(신청자 = user_a_id) 기반
    - 신청자가 이미 매칭 대기 중이면 생성 불가
    - 신청자가 매칭 요청 시 is_matching_available = False
    - user_b_id 는 자동매칭 로직 없으면 None 유지
    """

    user = (
        db.query(models.User)
        .filter(models.User.user_id == user_id)
        .first()
    )

    if not user:
        raise ValueError("User not found")

    if not user.is_matching_available:
        raise ValueError("이미 매칭을 진행 중입니다.")

    # 대기열 생성
    new_match = models.MatchingQueue(
        user_a_id=user_id,
        user_b_id=None,                # 자동 매칭이 있다면 이후 로직에서 채움
        status="PENDING",
        a_consent=None,
        b_consent=None,
        shared_category=desired_category,
        requested_at=datetime.utcnow()
    )

    db.add(new_match)

    # 신청자 상태 잠금
    user.is_matching_available = False

    db.commit()
    db.refresh(new_match)

    return new_match

def get_match_by_id(db: Session, match_id: int):
    return (
        db.query(models.MatchingQueue)
        .filter(models.MatchingQueue.match_id == match_id)
        .first()
    )

def process_match_answer(db: Session, match_id: int, user_id: int, consent: bool):
    """
    - user_id 가 user_a 인지 user_b 인지 판별
    - a_consent / b_consent 값 설정
    - 둘 다 True → CONFIRMED
    - 하나라도 False → CANCELED
    - 확정되면 User.is_matching_available 복구
    - 알림(Notification) 생성
    """

    match = get_match_by_id(db, match_id)
    if not match:
        raise ValueError("Match not found")

    # 사용자 판별
    if user_id == match.user_a_id:
        match.a_consent = consent
    elif match.user_b_id and user_id == match.user_b_id:
        match.b_consent = consent
    else:
        raise PermissionError("해당 매칭에 참여한 유저가 아닙니다.")

    if consent is False:
        match.status = "CANCELED"
        match.canceled_at = datetime.utcnow()

        # 매칭 가능 상태 복구
        user_a = db.query(models.User).get(match.user_a_id)
        if user_a:
            user_a.is_matching_available = True

        if match.user_b_id:
            user_b = db.query(models.User).get(match.user_b_id)
            if user_b:
                user_b.is_matching_available = True

        db.commit()
        db.refresh(match)
        return match

    if not (match.a_consent is True and match.b_consent is True):
        match.status = "AGREEMENT"     # 합의 대기 상태
        db.commit()
        db.refresh(match)
        return match

    match.status = "CONFIRMED"
    match.confirmed_at = datetime.utcnow()

    # shared_category가 없다면 여기서 채울 수도 있음(선택)
    # e.g. user_a가 배움을 원하는 분야로 자동 설정 등

    # 유저 상태 복구
    user_a = db.query(models.User).get(match.user_a_id)
    user_b = db.query(models.User).get(match.user_b_id)

    if user_a:
        user_a.is_matching_available = True
    if user_b:
        user_b.is_matching_available = True

    for u in [user_a, user_b]:
        if not u:
            continue
        notif = models.Notification(
            user_id=u.user_id,
            type="MATCH_SUCCESS",
            content="매칭이 성사되었습니다! 쪽지함에서 대화를 시작하세요.",
            link_path="/messages",
            is_read=False
        )
        db.add(notif)

    db.commit()
    db.refresh(match)

    return match
