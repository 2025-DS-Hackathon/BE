from sqlalchemy.orm import Session
from app.models import MatchingQueue

def get_pending_match_by_user(db: Session, user_id: int):
    return db.query(MatchingQueue).filter(
        (MatchingQueue.requester_id == user_id) | (MatchingQueue.owner_id == user_id),
        MatchingQueue.status == "PENDING"
    ).first()

def create_match_request(db: Session, user_id: int, teach_talent_id: int):
    new_match = MatchingQueue(
        requester_id=user_id,
        teach_talent_id=teach_talent_id,
        status="PENDING"
    )
    db.add(new_match)
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app import models

# --- 간단 조회: 사용자가 이미 PENDING 상태인지 확인 ---
def get_pending_match_by_user(db: Session, user_id: int):
    return (
        db.query(models.MatchingQueue)
        .filter(
            models.MatchingQueue.status == "PENDING",
            models.MatchingQueue.user_a_id == user_id,
        )
        .first()
    )

# --- 매칭 요청 생성 ---
def create_match_request(db: Session, user_id: int, desired_category: str = None):
    """
    1) 새 대기열 row 생성 (user_a_id = 신청자)
    2) is_matching_available 을 False 로 바꿔 중복 방지
    """
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not user:
        raise ValueError("User not found")

    if not user.is_matching_available:
        raise ValueError("이미 다른 매칭을 진행 중입니다.")

    new_match = models.MatchingQueue(
        user_a_id=user_id,
        user_b_id=None,
        status="PENDING",
        a_consent=None,
        b_consent=None,
        shared_category=desired_category,
        requested_at=datetime.utcnow(),
    )
    db.add(new_match)
    # 신청자 상태 잠금
    user.is_matching_available = False

    db.commit()
    db.refresh(new_match)
    return new_match

def process_match_answer(db: Session, match_id: int, user_id: int, agreement: bool, is_requester: bool):
    match = db.query(MatchingQueue).filter(MatchingQueue.id == match_id).first()
    if not match:
        raise ValueError("Match not found")
    
    if is_requester:
        match.a_consent = agreement
    else:
        match.b_consent = agreement
    
    if match.a_consent and match.b_consent:
        match.status = "CONFIRMED"
    elif not agreement:
        match.status = "CANCELED"

    db.commit()
    db.refresh(match)
    return match, match.status
# --- match_id로 조회 ---
def get_match_by_id(db: Session, match_id: int):
    return db.query(models.MatchingQueue).filter(models.MatchingQueue.match_id == match_id).first()

# --- 합의 처리(사용자가 O/X 누를때) ---
def process_match_answer(db: Session, match_id: int, user_id: int, consent: bool):
    """
    - user_id가 user_a인지 user_b인지 확인
    - 해당 칼럼(a_consent/b_consent) 업데이트
    - 둘 다 O -> CONFIRMED 처리
    - 하나라도 X -> CANCELED 처리
    - 상태 변화시 알림/유저 is_matching_available 처리
    """
    match = get_match_by_id(db, match_id)
    if not match:
        raise ValueError("Match not found")

    # 누가 응답하는지 확인
    if user_id == match.user_a_id:
        match.a_consent = consent
    elif match.user_b_id and user_id == match.user_b_id:
        match.b_consent = consent
    else:
        raise PermissionError("해당 매칭의 당사자가 아닙니다.")

    # 응답이 False(거절)라면 즉시 취소
    if consent is False:
        match.status = "CANCELED"
        match.canceled_at = datetime.utcnow()
        # 복구: 신청자와 (있다면) 상대방의 매칭 가능 상태 true로
        user_a = db.query(models.User).get(match.user_a_id)
        if user_a:
            user_a.is_matching_available = True
        if match.user_b_id:
            user_b = db.query(models.User).get(match.user_b_id)
            if user_b:
                user_b.is_matching_available = True

        db.add(match)
        db.commit()
        db.refresh(match)
        return match

    # consent == True 인 경우 (승낙)
    # 만약 상대방이 아직 응답하지 않았다면 상태는 합의 대기(PENDING 또는 AGREEMENT)
    if match.a_consent is True and match.b_consent is True:
        # 둘다 O -> 최종 확정
        match.status = "CONFIRMED"
        match.confirmed_at = datetime.utcnow()
        # 알림 생성 (Notification 모델 사용)
        # 여기선 간단히 알림 row 생성
        user_a = db.query(models.User).get(match.user_a_id)
        user_b = db.query(models.User).get(match.user_b_id) if match.user_b_id else None

        # shared_category가 비어있으면 채우는 시점(선택적)
        if not match.shared_category:
            # 시나리오: a의 learn 카테고리 저장 또는 프론트에서 전달한 값 사용
            pass

        # 생성된 알림 추가
        if user_a:
            notif = models.Notification(
                user_id=user_a.user_id,
                type="MATCH_SUCCESS",
                content="매칭이 성공 되었습니다. 지금 바로 쪽지함을 통해 재능을 공유해보세요.",
                link_path="/messages",
                is_read=False,
            )
            db.add(notif)
        if user_b:
            notif = models.Notification(
                user_id=user_b.user_id,
                type="MATCH_SUCCESS",
                content="매칭이 성공 되었습니다. 지금 바로 쪽지함을 통해 재능을 공유해보세요.",
                link_path="/messages",
                is_read=False,
            )
            db.add(notif)

        # 쪽지 기능 활성화는 프론트레이어가 확인해서 활성화할 수 있도록 DB 상태만 바꿈
        # (예: status == CONFIRMED 이면 쪽지함에서 대화 가능)

        db.add(match)
        db.commit()
        db.refresh(match)
        return match

    # 아직 상대의 응답을 기다리는 상태
    db.add(match)
    db.commit()
    db.refresh(match)
    return match
