# app/routers/matches.py
from datetime import datetime, timedelta
from typing import List, Optional

import time
import threading

from fastapi import APIRouter, Depends, FastAPI
from sqlalchemy.orm import Session

from app import models, schemas
from app.deps import get_db, get_active_user  # 약관 동의 + 로그인된 유저만 매칭 가능

router = APIRouter()

# ------------------------------
# 1) 랜덤 매칭 시작 API
#    (MAIN-2310, MAIN-2320)
# ------------------------------
@router.post("/start", response_model=schemas.MatchStartResponse)
def start_matching(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_active_user),
):
    """
    - 사용자가 '랜덤 매칭 시작' 버튼을 눌렀을 때 호출
    - 상태 체크 후 대기열에 등록
    - 바로 짝이 나올 수 있으므로, 한 번 매칭 알고리즘도 실행
    """

    # 1) 중년 유저는 서비스 대상 아님
    if current_user.user_type == "MIDDLE":
        return schemas.MatchStartResponse(
            result=schemas.MatchStartResult.MIDDLE_USER,
            message="현재 서비스는 청년-시니어 세대 간 교류를 위해 운영 중입니다.\n세대 조건이 맞지 않아 매칭 신청이 불가합니다.",
        )

    # 2) 재능 카드(배우고 싶은 것 + 가르쳐줄 수 있는 것) 존재 여부 확인
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
            message="랜덤 매칭을 시작하려면\n'배우고 싶은 재능'과 '가르쳐줄 수 있는 재능' 카드를 모두 등록해야 합니다.",
        )

    # 3) 이미 대기 중인지 확인 (PENDING 상태)
    existing_pending = (
        db.query(models.MatchingQueue)
        .filter(
            models.MatchingQueue.user_a_id == current_user.user_id,
            models.MatchingQueue.status == "PENDING",
        )
        .first()
    )
    if existing_pending:
        return schemas.MatchStartResponse(
            result=schemas.MatchStartResult.ALREADY_WAITING,
            message="이미 매칭 대기 중입니다.\n매칭 결과는 마이페이지의 알림에서 확인해 주세요.",
            match_id=existing_pending.match_id,
        )

    # 4) 대기열에 새로 등록
    new_entry = models.MatchingQueue(
        user_a_id=current_user.user_id,
        user_b_id=None,
        status="PENDING",
        a_consent=None,
        b_consent=None,
        shared_category=None,
        requested_at=datetime.utcnow(),
    )
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)

    # 5) 매칭 알고리즘 1회 실행 (바로 짝이 나올 수 있으므로)
    run_matching_once(db)

    # 6) 알고리즘 실행 이후, 이 유저가 이미 CONFIRMED 상태의 매칭을 가지는지 확인
    confirmed = (
        db.query(models.MatchingQueue)
        .filter(
            models.MatchingQueue.status == "CONFIRMED",
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
            message="신청 완료! 바로 매칭이 성사되었습니다.\n상대방과의 교류는 마이페이지에서 확인해 보세요.",
            match_id=confirmed.match_id,
        )

    # 7) 아직 확정된 매칭이 없다면, 대기 상태로 응답
    return schemas.MatchStartResponse(
        result=schemas.MatchStartResult.QUEUED,
        message="신청 완료! 매칭이 확정되면 알림(앱 내 뱃지)으로 알려드릴게요.\n잠시 후 마이페이지에서 확인해 보세요.",
        match_id=new_entry.match_id,
    )


# ------------------------------
# 2) 매칭 알고리즘 (1회 실행)
#    (MAIN-2321, 2322 – 매칭 조건 / 처리 로직)
# ------------------------------
def run_matching_once(db: Session) -> None:
    """
    - status='PENDING' 인 대기열을 조회
    - 매칭 조건:
        1) A.learn_category == B.teach_category
        2) A.User_Type != B.User_Type (청년 ↔ 시니어)
    - 조건을 만족하는 두 사용자를 찾으면:
        - 하나의 MatchingQueue row를 CONFIRMED로 만들고
        - user_a_id / user_b_id 채우고
        - confirmed_at 기록
        - 상대편 entry는 CANCELED 처리
        - 두 사용자에게 MATCH_SUCCESS 알림 생성
    """

    # 1) PENDING 상태의 대기열 가져오기 (user_b_id가 아직 없는 것만)
    pending_entries: List[models.MatchingQueue] = (
        db.query(models.MatchingQueue)
        .filter(
            models.MatchingQueue.status == "PENDING",
            models.MatchingQueue.user_b_id.is_(None),
        )
        .order_by(models.MatchingQueue.requested_at.asc())
        .all()
    )

    used_match_ids = set()  # 이미 매칭에 사용된 entry의 match_id

    # 헬퍼: 유저의 learn/teach 카테고리 가져오기
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
        entry_a = pending_entries[i]
        if entry_a.match_id in used_match_ids:
            continue

        user_a = db.query(models.User).get(entry_a.user_a_id)
        if not user_a:
            continue
        if user_a.user_type == "MIDDLE":
            # 중년은 매칭 대상에서 제외
            continue

        cats_a = get_categories(user_a.user_id)
        if not cats_a:
            continue
        a_learn_cat, a_teach_cat = cats_a

        for j in range(i + 1, len(pending_entries)):
            entry_b = pending_entries[j]
            if entry_b.match_id in used_match_ids:
                continue

            user_b = db.query(models.User).get(entry_b.user_a_id)
            if not user_b:
                continue
            if user_b.user_type == "MIDDLE":
                continue

            cats_b = get_categories(user_b.user_id)
            if not cats_b:
                continue
            b_learn_cat, b_teach_cat = cats_b

            # 매칭 조건:
            # 1) A.learn_category == B.teach_category
            # 2) A.User_Type != B.User_Type
            if (a_learn_cat == b_teach_cat) and (user_a.user_type != user_b.user_type):
                # 매칭 성사!
                entry_a.user_b_id = user_b.user_id
                entry_a.status = "CONFIRMED"
                entry_a.shared_category = a_learn_cat
                entry_a.confirmed_at = datetime.utcnow()
                entry_a.a_consent = None
                entry_a.b_consent = None

                # entry_b는 대기열에서 제거 (또는 상태만 변경)
                entry_b.status = "CANCELED"
                entry_b.canceled_at = datetime.utcnow()

                db.add(entry_a)
                db.add(entry_b)

                # ✅ 두 사용자에게 매칭 성공 알림 생성
                create_match_success_notifications(db, entry_a, user_a, user_b)

                used_match_ids.add(entry_a.match_id)
                used_match_ids.add(entry_b.match_id)

                # 한 번에 여러 쌍 매칭 가능하므로 계속 탐색
                break

    db.commit()


# ------------------------------
# 3) 매칭 확정 시 알림 생성
#    (MAIN-2323, 2324 – 알림 + 재능 ID 기록은 MatchingQueue에 이미 있음)
# ------------------------------
def create_match_success_notifications(
    db: Session,
    match_entry: models.MatchingQueue,
    user_a: models.User,
    user_b: models.User,
):
    """
    매칭이 CONFIRMED 되었을 때 두 사용자에게 MATCH_SUCCESS 알림 생성
    """
    category = match_entry.shared_category or "재능 교환"

    msg_for_a = f"{user_b.nickname}님과 '{category}' 재능 교환 가능성이 생겼습니다!"
    msg_for_b = f"{user_a.nickname}님과 '{category}' 재능 교환 가능성이 생겼습니다!"

    notif_a = models.Notification(
        user_id=user_a.user_id,
        type="MATCH_SUCCESS",
        content=msg_for_a,
        link_path="/matching",  # 프론트에서 매칭 상세/채팅으로 라우팅
        is_read=False,
    )
    notif_b = models.Notification(
        user_id=user_b.user_id,
        type="MATCH_SUCCESS",
        content=msg_for_b,
        link_path="/matching",
        is_read=False,
    )

    db.add(notif_a)
    db.add(notif_b)
    db.commit()


# ------------------------------
# 4) 매칭 만료(24시간) 처리
#    (MAIN-2325)
# ------------------------------
def expire_old_matches(db: Session) -> None:
    """
    - 매칭 대기 또는 확정 상태에서 24시간 이상 지난 항목을 CANCELED 처리
    - 각 사용자에게 MATCH_FAIL 알림 생성
    """
    now = datetime.utcnow()
    expire_before = now - timedelta(hours=24)

    # 24시간 넘은 PENDING / CONFIRMED 매칭
    expired_rows: List[models.MatchingQueue] = (
        db.query(models.MatchingQueue)
        .filter(
            models.MatchingQueue.status.in_(["PENDING", "CONFIRMED"]),
            models.MatchingQueue.requested_at < expire_before,
        )
        .all()
    )

    for row in expired_rows:
        row.status = "CANCELED"
        row.canceled_at = now

        msg = "매칭 대기 시간이 만료되어 매칭이 실패하였습니다."

        # user_a 알림
        fail_a = models.Notification(
            user_id=row.user_a_id,
            type="MATCH_FAIL",
            content=msg,
            link_path="/matching",
            is_read=False,
        )
        db.add(fail_a)

        # user_b가 존재하면 user_b도 알림
        if row.user_b_id:
            fail_b = models.Notification(
                user_id=row.user_b_id,
                type="MATCH_FAIL",
                content=msg,
                link_path="/matching",
                is_read=False,
            )
            db.add(fail_b)

        db.add(row)

    if expired_rows:
        db.commit()


# ------------------------------
# 5) 매칭 성공 통계 (MAIN-2400)
#    "오늘 OO명이 연결되었습니다!" 에서 OO 계산
# ------------------------------
@router.get("/stats/today", response_model=schemas.TodayMatchStats)
def get_today_match_stats(
    db: Session = Depends(get_db),
):
    """
    오늘 날짜 기준으로 CONFIRMED 된 매칭 개수 집계
    - confirmed_at 이 오늘인 row만 센다.
    """
    today = datetime.utcnow().date()
    start = datetime.combine(today, datetime.min.time())
    end = datetime.combine(today, datetime.max.time())

    count = (
        db.query(models.MatchingQueue)
        .filter(
            models.MatchingQueue.status == "CONFIRMED",
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
# 6) 주기적으로 매칭/만료 검사 (30초마다)
#    - main.py 에서 register_match_worker(app) 호출 필요
#    (MAIN-2322, 2325 자동 처리용)
# ------------------------------
def register_match_worker(app: FastAPI) -> None:
    """
    앱 시작 시 별도의 스레드에서 30초마다:
      - run_matching_once()
      - expire_old_matches()
    를 실행하는 워커 등록
    """

    from app.db import SessionLocal

    def worker():
        while True:
            db = SessionLocal()
            try:
                run_matching_once(db)
                expire_old_matches(db)
            except Exception as e:
                # 로그만 찍고 죽지 않도록
                print("[MATCH_WORKER_ERROR]", e)
            finally:
                db.close()

            time.sleep(30)  # 30초 주기

    @app.on_event("startup")
    def _start_worker():
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

# -------------------------------------------
# 7) 매칭 합의 여부 처리 API
# -------------------------------------------
@router.post("/{match_id}/consent", response_model=schemas.MatchConsentResponse)
def submit_match_consent(
    match_id: int,
    request: schemas.MatchConsentRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_active_user)
):
    """
    매칭 합의 여부(O/X)를 제출하는 API.
    - a_consent 또는 b_consent 저장
    - 둘 중 하나라도 X → 즉시 취소
    - 둘 다 O → 최종 확정
    """

    match = db.query(models.MatchingQueue).filter(
        models.MatchingQueue.match_id == match_id
    ).first()

    if not match:
        return schemas.MatchConsentResponse(
            result="NOT_FOUND",
            message="해당 매칭 정보를 찾을 수 없습니다."
        )

    # 본인이 user_a인지 user_b인지 판단
    if current_user.user_id == match.user_a_id:
        target_field = "a_consent"
    elif current_user.user_id == match.user_b_id:
        target_field = "b_consent"
    else:
        return schemas.MatchConsentResponse(
            result="FORBIDDEN",
            message="이 매칭의 당사자가 아닙니다."
        )

    # 이미 답변한 경우 방지
    if getattr(match, target_field) is not None:
        return schemas.MatchConsentResponse(
            result="ALREADY_ANSWERED",
            message="이미 합의 여부를 제출하셨습니다."
        )

    # 답변 저장
    setattr(match, target_field, request.choice.value)
    db.commit()
    db.refresh(match)

    # ------------------------------
    # 1) 사용자가 X → 즉시 취소
    # ------------------------------
    if request.choice == schemas.ConsentChoice.NO:
        match.status = "CANCELED"
        match.canceled_at = datetime.utcnow()
        db.add(match)

        # 알림 전송
        cancel_msg = "매칭이 취소되었습니다. 다시 재능 공유를 신청해보세요."
        db.add(models.Notification(
            user_id=match.user_a_id,
            type="MATCH_CANCELED",
            content=cancel_msg,
            is_read=False,
        ))
        if match.user_b_id:
            db.add(models.Notification(
                user_id=match.user_b_id,
                type="MATCH_CANCELED",
                content=cancel_msg,
                is_read=False,
            ))

        # 매칭 가능 상태 복원
        user = db.query(models.User).get(current_user.user_id)
        user.is_matching_available = True
        db.add(user)

        db.commit()

        return schemas.MatchConsentResponse(
            result="CANCELED",
            message="매칭이 취소되었습니다. 다시 재능 공유를 신청해보세요."
        )

    # ------------------------------
    # 2) 본인은 O, 상대방은 아직 → 대기
    # ------------------------------
    if (match.a_consent == "O" and match.b_consent is None) or \
       (match.b_consent == "O" and match.a_consent is None):

        return schemas.MatchConsentResponse(
            result="WAITING",
            message="상대방의 답변을 기다리고 있어요! 답변이 오면 알려드릴게요."
        )

    # ------------------------------
    # 3) 둘 다 O → 최종 확정
    # ------------------------------
    if match.a_consent == "O" and match.b_consent == "O":
        match.status = "FINAL_CONFIRMED"
        match.confirmed_at = datetime.utcnow()
        db.add(match)

        # 알림
        confirm_msg = "매칭이 성공 되었습니다. 지금 바로 쪽지함을 통해 재능을 공유해보세요."
        db.add(models.Notification(
            user_id=match.user_a_id,
            type="MATCH_CONFIRMED",
            content=confirm_msg,
            is_read=False,
        ))
        db.add(models.Notification(
            user_id=match.user_b_id,
            type="MATCH_CONFIRMED",
            content=confirm_msg,
            is_read=False,
        ))

        db.commit()

        return schemas.MatchConsentResponse(
            result="CONFIRMED",
            message=confirm_msg
        )

    # fallback
    return schemas.MatchConsentResponse(
        result="OK",
        message="처리가 완료되었습니다."
    )