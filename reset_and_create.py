import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.getcwd())

from app.db import SessionLocal
from app.models import User, MatchingQueue, Message

def reset_and_create():
    db = SessionLocal()
    print("--- 🧹 데이터 초기화 및 재생성을 시작합니다 ---")

    # 1. 내 계정 찾기
    me = db.query(User).first()
    if not me:
        print("❌ 오류: 내 계정이 없습니다.")
        return

    print(f"👤 내 계정: {me.nickname}")

    # 2. 기존 메시지 싹 지우기 (중복 해결!)
    # 안전을 위해 '나'와 관련된 매칭의 메시지만 삭제합니다.
    my_matches = db.query(MatchingQueue).filter(
        (MatchingQueue.user_a_id == me.user_id) | (MatchingQueue.user_b_id == me.user_id)
    ).all()
    
    deleted_count = 0
    for match in my_matches:
        # 해당 매칭방의 메시지 전체 삭제
        count = db.query(Message).filter(Message.match_id == match.match_id).delete()
        deleted_count += count
    
    db.commit()
    print(f"🗑️  기존 메시지 {deleted_count}개를 삭제했습니다.")


    # 3. 데이터 다시 생성 (기존 로직)
    dummy_partners = [
        {"name": "헬스매니아", "category": "운동/헬스", "msg": "안녕하세요! 벤치프레스 자세 교환 가능할까요?", "read": False},
        {"name": "영어고수", "category": "외국어/영어", "msg": "Hi! I can teach you English conversation.", "read": True},
        {"name": "맛집탐방러", "category": "요리/베이킹", "msg": "혹시 한식 요리도 가르쳐 주시나요?", "read": False},
        {"name": "기타리스트", "category": "음악/악기", "msg": "기타 코드 잡는 법 알려드릴게요!", "read": True},
        {"name": "포토샵장인", "category": "디자인/툴", "msg": "누끼 따는 법 궁금하다고 하셔서 연락드렸어요.", "read": False},
    ]

    for i, p in enumerate(dummy_partners):
        # 파트너 찾거나 생성
        partner = db.query(User).filter(User.nickname == p["name"]).first()
        if not partner:
            partner = User(nickname=p["name"], user_type="YOUNG", user_status="NORMAL")
            db.add(partner)
            db.commit()
            db.refresh(partner)
        
        # 매칭 찾거나 생성
        match = db.query(MatchingQueue).filter(
            MatchingQueue.user_a_id == me.user_id, MatchingQueue.user_b_id == partner.user_id
        ).first()

        if not match:
            match = MatchingQueue(
                user_a_id=me.user_id, user_b_id=partner.user_id, status="CONFIRMED",
                shared_category=p["category"], requested_at=datetime.now(), confirmed_at=datetime.now()
            )
            db.add(match)
            db.commit()
            db.refresh(match)

        # 메시지 생성 (i분 전, 2*i분 전 등 시간 차이를 둠)
        # 나중에 생성된 메시지(ID가 큰)가 더 최신이 되도록 i를 이용
        msg = Message(
            match_id=match.match_id,
            sender_id=partner.user_id,
            content=p["msg"],
            is_read=p["read"],
            timestamp=datetime.now() - timedelta(minutes=i*10)
        )
        db.add(msg)
    
    db.commit()
    print(f"✨ 새 메시지 5개를 생성했습니다!")
    print("👉 프론트엔드에서 새로고침 하세요.")
    db.close()

if __name__ == "__main__":
    reset_and_create()