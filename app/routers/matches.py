# app/routers/matches.py
from datetime import datetime, timedelta
from typing import List, Optional

import threading
import time

from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.deps import get_db, get_active_user  # 약관 동의 + 로그인된 유저만 매칭 가능
from app.db import SessionLocal

from app.schemas import MatchDetailResponse, TalentSummary # TalentSummary import 확인 필요
from app.models import Talent # 모델 필요

router = APIRouter()

# ------------------------------
# 1) 랜덤 매칭 시작 (MAIN-2310, 2320)
# ------------------------------
@router.post("/start", response_model=schemas.MatchStartResponse)
def start_matching(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_active_user),
):
    # 중년 유저는 서비스 대상 아님
    if current_user.user_type == "MIDDLE":
        return schemas.MatchStartResponse(
            result=schemas.MatchStartResult.MIDDLE_USER,
            message=(
                "현재 서비스는 청년-시니어 세대 간 교류를 위해 운영 중입니다.\n"
                "세대 조건이 맞지 않아 매칭 신청이 불가합니다."
            ),
        )

    # 재능 카드 존재 여부 확인
    learn_talent = (
        db.query(models.Talent)
        .filter(
            models.Talent.user_id == current_user.user_id,
            models.Talent.type.ilike("learn"),
        )
        .first()
    )
    teach_talent = (
        db.query(models.Talent)
        .filter(
            models.Talent.user_id == current_user.user_id,
            models.Talent.type.ilike("teach"),
        )
        .first()
    )
    if not learn_talent or not teach_talent:
        return schemas.MatchStartResponse(
            result=schemas.MatchStartResult.NO_TALENT,
            message=(
                "랜덤 매칭을 시작하려면\n"
                "'배우고 싶은 재능'과 '가르쳐줄 수 있는 재능' 카드를 모두 등록해야 합니다."
            ),
        )

    # 이미 PENDING 대기중인지 확인
    existing = (
        db.query(models.MatchingQueue)
        .filter(
            models.MatchingQueue.user_a_id == current_user.user_id,
            models.MatchingQueue.status == "PENDING",
        )
        .first()
    )
    if existing:
        return schemas.MatchStartResponse(
            result=schemas.MatchStartResult.ALREADY_WAITING,
            message=(
                "이미 매칭 대기 중입니다.\n"
                "매칭 결과는 마이페이지의 알림에서 확인해 주세요."
            ),
            match_id=existing.match_id,
        )

    # 대기열 등록
    new_entry = models.MatchingQueue(
        user_a_id=current_user.user_id,
        status="PENDING",
        requested_at=datetime.utcnow(),
    )
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)

    # 바로 1회 매칭 시도
    run_matching_once(db)

    # 매칭이 즉시 잡혔는지 확인
    confirmed = (
        db.query(models.MatchingQueue)
        .filter(
            models.MatchingQueue.status.in_(["CONFIRMED", "SUCCESS"]),
            (
                (models.MatchingQueue.user_a_id == current_user.user_id)
                | (models.MatchingQueue.user_b_id == current_user.user_id)
            ),
        )
        .order_by(models.MatchingQueue.confirmed_at.desc())
        .first()
    )
    if confirmed:
        return schemas.MatchStartResponse(
            result=schemas.MatchStartResult.MATCHED_IMMEDIATELY,
            message=(
                "신청 완료! 바로 매칭이 성사되었습니다.\n"
                "상대방과의 교류는 마이페이지에서 확인해 보세요."
            ),
            match_id=confirmed.match_id,
        )

    return schemas.MatchStartResponse(
        result=schemas.MatchStartResult.QUEUED,
        message=(
            "신청 완료! 매칭이 확정되면 알림(앱 내 뱃지)으로 알려드릴게요.\n"
            "잠시 후 마이페이지에서 확인해 보세요."
        ),
        match_id=new_entry.match_id,
    )


# ------------------------------
# 2) 매칭 알고리즘 1회 실행 (MAIN-2321, 2322)
# ------------------------------
def run_matching_once(db: Session) -> None:
    pending_entries: List[models.MatchingQueue] = (
        db.query(models.MatchingQueue)
        .filter(
            models.MatchingQueue.status == "PENDING",
            models.MatchingQueue.user_b_id.is_(None),
        )
        .order_by(models.MatchingQueue.requested_at.asc())
        .all()
    )

    used = set()

    def get_categories(user_id: int) -> Optional[tuple[str, str]]:
        learn = (
            db.query(models.Talent)
            .filter(
                models.Talent.user_id == user_id,
                models.Talent.type.ilike("learn"),
            )
            .first()
        )
        teach = (
            db.query(models.Talent)
            .filter(
                models.Talent.user_id == user_id,
                models.Talent.type.ilike("teach"),
            )
            .first()
        )
        if not learn or not teach:
            return None
        return (learn.category, teach.category)

    for i in range(len(pending_entries)):
        a_entry = pending_entries[i]
        if a_entry.match_id in used:
            continue

        user_a = db.query(models.User).get(a_entry.user_a_id)
        if not user_a or user_a.user_type == "MIDDLE":
            continue

        cats_a = get_categories(user_a.user_id)
        if not cats_a:
            continue
        a_learn, a_teach = cats_a

        for j in range(i + 1, len(pending_entries)):
            b_entry = pending_entries[j]
            if b_entry.match_id in used:
                continue

            user_b = db.query(models.User).get(b_entry.user_a_id)
            if not user_b or user_b.user_type == "MIDDLE":
                continue

            cats_b = get_categories(user_b.user_id)
            if not cats_b:
                continue
            b_learn, b_teach = cats_b

            # 매칭 조건
            if (a_learn == b_teach) and (user_a.user_type != user_b.user_type):
                # A row를 최종 매칭 row로 사용
                a_entry.user_b_id = user_b.user_id
                a_entry.status = "CONFIRMED"
                a_entry.shared_category = a_learn
                a_entry.confirmed_at = datetime.utcnow()
                a_entry.a_consent = None
                a_entry.b_consent = None

                # B row는 취소
                b_entry.status = "CANCELED"
                b_entry.canceled_at = datetime.utcnow()

                db.add(a_entry)
                db.add(b_entry)

                # ✅ MATCH_FOUND 알림 생성
                create_match_found_notifications(db, a_entry, user_a, user_b)

                used.add(a_entry.match_id)
                used.add(b_entry.match_id)
                break

    db.commit()


def create_match_found_notifications(
    db: Session,
    match_entry: models.MatchingQueue,
    user_a: models.User,
    user_b: models.User,
):
    category = match_entry.shared_category or "재능 교환"

    msg_a = f"{user_b.nickname}님과 '{category}' 재능 교환 가능성이 생겼습니다!"
    msg_b = f"{user_a.nickname}님과 '{category}' 재능 교환 가능성이 생겼습니다!"

    notif_a = models.Notification(
        user_id=user_a.user_id,
        type="MATCH_FOUND",
        content=msg_a,
        link_path=f"/matches/{match_entry.match_id}",
        is_read=False,
    )
    notif_b = models.Notification(
        user_id=user_b.user_id,
        type="MATCH_FOUND",
        content=msg_b,
        link_path=f"/matches/{match_entry.match_id}",
        is_read=False,
    )
    db.add(notif_a)
    db.add(notif_b)
    db.commit()

# ==========================================
# [추가] 2.5) 매칭 상세 정보 조회 (상대방 재능 확인용)
# ==========================================
@router.get("/{match_id}", response_model=schemas.MatchDetailResponse)
def get_match_detail(
    match_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_active_user),
):
    # 1. 매칭 정보 찾기
    match = db.query(models.MatchingQueue).filter(models.MatchingQueue.match_id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="매칭 정보를 찾을 수 없습니다.")

    # 2. 파트너 식별
    my_id = current_user.user_id
    if match.user_b_id is None:
        partner_id = my_id 
        partner_nickname = f"{current_user.nickname} (가상 파트너)"
    else:
        if match.user_a_id == my_id:
            partner_id = match.user_b_id
        elif match.user_b_id == my_id:
            partner_id = match.user_a_id
        else:
            raise HTTPException(status_code=403, detail="이 매칭의 참여자가 아닙니다.") 
        partner_user = db.query(models.User).filter(models.User.user_id == partner_id).first()
        partner_nickname = partner_user.nickname if partner_user else "알 수 없음"

    # 3. 재능 정보 가져오기
    my_talent_db = db.query(models.Talent).filter(
        models.Talent.user_id == my_id, 
        models.Talent.type.ilike("Teach") 
    ).first()

    partner_talent_db = db.query(models.Talent).filter(
        models.Talent.user_id == partner_id, 
        models.Talent.type.ilike("Teach")
    ).first()

    # 🔥 [수정 핵심] 자동 변환 대신 '수동 생성'으로 에러 방지
    my_talent_dto = None
    if my_talent_db:
        # DB에 'id'로 저장되어 있든 'talent_id'로 저장되어 있든 안전하게 가져옴
        tid = getattr(my_talent_db, "talent_id", getattr(my_talent_db, "id", 0))
        
        my_talent_dto = schemas.TalentSummary(
            talent_id=tid,
            type=my_talent_db.type,
            category=my_talent_db.category,
            title=my_talent_db.title,
            description=my_talent_db.description,
            tags=my_talent_db.tags
        )

    partner_talent_dto = None
    if partner_talent_db:
        tid = getattr(partner_talent_db, "talent_id", getattr(partner_talent_db, "id", 0))
        
        partner_talent_dto = schemas.TalentSummary(
            talent_id=tid,
            type=partner_talent_db.type,
            category=partner_talent_db.category,
            title=partner_talent_db.title,
            description=partner_talent_db.description,
            tags=partner_talent_db.tags
        )

    return schemas.MatchDetailResponse(
        match_id=match.match_id,
        my_talent=my_talent_dto,
        partner_talent=partner_talent_dto,
        status=match.status,
        partner_nickname=partner_nickname
    )

# ------------------------------
# 3) 합의(O/X) 처리 → SUCCESS / CANCELED
#    (MATCH_SUCCESS / MATCH_CANCELED 알림)
# ------------------------------
@router.post("/{match_id}/agreement", response_model=schemas.MatchAgreementResponse)
def submit_agreement(
    match_id: int,
    body: schemas.MatchAgreementRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_active_user),
):
    match = db.query(models.MatchingQueue).get(match_id)
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="매칭 정보를 찾을 수 없습니다.",
        )

    if current_user.user_id not in (match.user_a_id, match.user_b_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="이 매칭의 참여자가 아닙니다.",
        )

    if match.status not in ("CONFIRMED", "SUCCESS"):
        return schemas.MatchAgreementResponse(
            status=match.status,
            message="이미 처리된 매칭입니다.",
        )

    # 현재 유저 동의/거절 기록
    if current_user.user_id == match.user_a_id:
        match.a_consent = body.is_agreed
    else:
        match.b_consent = body.is_agreed

    # 누군가 X를 누른 경우 → 즉시 취소
    if match.a_consent is False or match.b_consent is False:
        match.status = "CANCELED"
        match.canceled_at = datetime.utcnow()
        db.add(match)
        db.commit()
        notify_match_canceled(db, match)
        return schemas.MatchAgreementResponse(
            status=match.status,
            message="매칭이 취소되었습니다. 다시 재능 공유를 신청해보세요.",
        )

    # 양쪽 모두 O를 누른 경우 → SUCCESS
    if match.a_consent and match.b_consent:
        match.status = "SUCCESS"
        db.add(match)
        db.commit()
        notify_match_success(db, match)
        return schemas.MatchAgreementResponse(
            status=match.status,
            message="매칭이 성공되었습니다. 지금 바로 쪽지를 통해 재능을 공유해 보세요.",
        )

    db.add(match)
    db.commit()
    return schemas.MatchAgreementResponse(
        status=match.status,
        message="상대방의 응답을 기다리는 중입니다.",
    )


def notify_match_success(db: Session, match: models.MatchingQueue) -> None:
    user_a = db.query(models.User).get(match.user_a_id)
    user_b = db.query(models.User).get(match.user_b_id)
    if not (user_a and user_b):
        return

    txt = "매칭이 성공되었습니다. 지금 바로 쪽지를 통해 재능을 공유해 보세요."

    for u in (user_a, user_b):
        notif = models.Notification(
            user_id=u.user_id,
            type="MATCH_SUCCESS",
            content=txt,
            link_path=f"/messages/{match.match_id}",
            is_read=False,
        )
        db.add(notif)
    db.commit()


def notify_match_canceled(db: Session, match: models.MatchingQueue) -> None:
    user_a = db.query(models.User).get(match.user_a_id)
    user_b = db.query(models.User).get(match.user_b_id)
    if not (user_a and user_b):
        return

    txt = "매칭이 취소되었습니다. 다시 재능 공유를 신청해보세요."

    for u in (user_a, user_b):
        notif = models.Notification(
            user_id=u.user_id,
            type="MATCH_CANCELED",
            content=txt,
            link_path=None,
            is_read=False,
        )
        db.add(notif)
    db.commit()


# ------------------------------
# 4) 24시간 만료 처리 (MATCH_FAIL)
# ------------------------------
def expire_old_matches(db: Session) -> None:
    now = datetime.utcnow()
    threshold = now - timedelta(hours=24)

    targets: List[models.MatchingQueue] = (
        db.query(models.MatchingQueue)
        .filter(
            models.MatchingQueue.status.in_(["PENDING", "CONFIRMED"]),
            models.MatchingQueue.requested_at < threshold,
        )
        .all()
    )

    for m in targets:
        m.status = "CANCELED"
        m.canceled_at = now
        db.add(m)

        txt = "매칭 대기 시간이 만료되어 매칭이 실패하였습니다."

        for uid in (m.user_a_id, m.user_b_id):
            if uid is None:
                continue
            notif = models.Notification(
                user_id=uid,
                type="MATCH_FAIL",
                content=txt,
                link_path=None,
                is_read=False,
            )
            db.add(notif)

    if targets:
        db.commit()


# ------------------------------
# 5) 오늘 매칭 통계 (MAIN-2400)
# ------------------------------
@router.get("/stats/today", response_model=schemas.TodayMatchStats)
def get_today_stats(
    db: Session = Depends(get_db),
):
    today = datetime.utcnow().date()
    start = datetime.combine(today, datetime.min.time())
    end = datetime.combine(today, datetime.max.time())

    count = (
        db.query(models.MatchingQueue)
        .filter(
            models.MatchingQueue.status.in_(["CONFIRMED", "SUCCESS"]),
            models.MatchingQueue.confirmed_at >= start,
            models.MatchingQueue.confirmed_at <= end,
        )
        .count()
    )
    return schemas.TodayMatchStats(
        date=today.isoformat(),
        matched_pairs=count,
    )


# ------------------------------
# 6) 주기적 작업 등록 (run_matching_once + expire_old_matches)
# ------------------------------
def register_periodic_task(app: FastAPI) -> None:
    def worker():
        while True:
            db = SessionLocal()
            try:
                run_matching_once(db)
                expire_old_matches(db)
            except Exception as e:
                print("[MATCH_WORKER_ERROR]", e)
            finally:
                db.close()
            time.sleep(30)

    @app.on_event("startup")
    def _start_worker():
        t = threading.Thread(target=worker, daemon=True)
        t.start()
