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
