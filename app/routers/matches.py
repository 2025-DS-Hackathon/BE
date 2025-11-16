from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.deps import get_db, get_current_user
from app.schemas import MatchRequestIn, MatchOut, MatchAnswerIn  # 수정됨
from app.models import User as DBUser, MatchingQueue as DBMatchingQueue
from app.crud import match as match_crud 

router = APIRouter()

@router.get("/ping")
def ping_matches():
    return {"area": "matches", "status": "ok"}

# 1. 매칭 요청 
@router.post("/request", response_model=MatchOut, summary="재능 연결 찾기 버튼 클릭 (매칭 대기열 등록)")
def request_match(
    match_request: MatchRequestIn,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user) 
):
    
    if match_crud.get_pending_match_by_user(db, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 신청 완료 상태 입니다. 매칭이 확정되면 알림으로 알려드릴게요."
        )

    try:
        db_match = match_crud.create_match_request(
            db=db,
            user_id=current_user.id,
            teach_talent_id=match_request.teach_talent_id
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    return db_match

# 매칭 합의 처리
@router.post("/{match_id}/answer", response_model=MatchOut, summary="매칭 합의 여부 결정 (O/X)")
def answer_match(
    match_id: int,
    answer: MatchAnswerIn,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user) 
):
    
    db_match = db.scalar(select(DBMatchingQueue).where(DBMatchingQueue.id == match_id))
    if not db_match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found.")
        
    is_requester = (db_match.user_a_id == current_user.id)  # DB 컬럼명 기준으로 수정 가능
    is_owner = (db_match.user_b_id == current_user.id)
    
    if not is_requester and not is_owner:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="접근 거부: 해당 매칭의 당사자가 아닙니다.")
    
    try:
        updated_match, final_status = match_crud.process_match_answer(
            db=db,
            match_id=match_id,
            user_id=current_user.id,
            agreement=answer.consent,
            is_requester=is_requester
        )
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # 최종 결과 메시지 결정
    if final_status == 'CONFIRMED':
        message = "매칭이 성공 되었습니다. 지금 바로 쪽지함을 통해 재능을 공유해보세요."
    elif final_status == 'CANCELED':
        message = "매칭이 성사되지 않았습니다."
    else:
        message = "합의 내용이 저장되었습니다. 상대방의 응답을 기다리는 중입니다."

    return MatchOut(
        match_id=match_id,
        status=final_status,
        a_consent=updated_match.a_consent,
        b_consent=updated_match.b_consent,
        requested_at=updated_match.requested_at,
        shared_category=updated_match.shared_category
    )
