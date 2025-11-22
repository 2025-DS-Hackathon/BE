# BE/create_test_data.py
import sys
import os
import random
from datetime import datetime, timedelta

# 현재 위치를 파이썬 경로에 추가
sys.path.append(os.getcwd())

from app.db import SessionLocal
from app.models import User, MatchingQueue, Message

def create_bulk_data():
    db = SessionLocal()
    print("--- 🚀 데이터 5개 추가 생성을 시작합니다 ---")

    # 1. 내 계정 찾기 (ID 1번이라고 가정)
    me = db.query(User).first()
    if not me:
        print("❌ 오류: 유저가 한 명도 없습니다. 웹에서 회원가입/로그인을 먼저 해주세요!")
        return
    print(f"👤 내 계정: {me.nickname} (ID: {me.user_id})")

    # 2. 생성할 가상 파트너 5명 리스트
    dummy_partners = [
        {"name": "헬스매니아", "category": "운동/헬스", "msg": "안녕하세요! 벤치프레스 자세 교환 가능할까요?", "read": False},
        {"name": "영어고수", "category": "외국어/영어", "msg": "Hi! I can teach you English conversation.", "read": True},
        {"name": "맛집탐방러", "category": "요리/베이킹", "msg": "혹시 한식 요리도 가르쳐 주시나요?", "read": False},
        {"name": "기타리스트", "category": "음악/악기", "msg": "기타 코드 잡는 법 알려드릴게요!", "read": True},
        {"name": "포토샵장인", "category": "디자인/툴", "msg": "누끼 따는 법 궁금하다고 하셔서 연락드렸어요.", "read": False},
    ]

    for i, p in enumerate(dummy_partners):
        # (1) 유저 생성 (없으면 만듦)
        partner = db.query(User).filter(User.nickname == p["name"]).first()
        if not partner:
            partner = User(
                nickname=p["name"],
                user_type="YOUNG",
                user_status="NORMAL",
                is_matching_available=True
            )
            db.add(partner)
            db.commit()
            db.refresh(partner)
            print(f"[{i+1}/5] 유저 생성 완료: {partner.nickname}")
        
        # (2) 매칭 생성 (CONFIRMED 상태)
        match = db.query(MatchingQueue).filter(
            MatchingQueue.user_a_id == me.user_id, 
            MatchingQueue.user_b_id == partner.user_id
        ).first()

        if not match:
            match = MatchingQueue(
                user_a_id=me.user_id,
                user_b_id=partner.user_id,
                status="CONFIRMED", # 중요: 쪽지함 노출 조건
                shared_category=p["category"],
                requested_at=datetime.now(),
                confirmed_at=datetime.now()
            )
            db.add(match)
            db.commit()
            db.refresh(match)

        # (3) 메시지 생성 (시간을 조금씩 다르게 해서 정렬 테스트)
        # 시간 차이를 두어 리스트 정렬이 잘 되는지 확인 (i분 전으로 설정)
        msg_time = datetime.now() - timedelta(minutes=i*10)
        
        msg = Message(
            match_id=match.match_id,
            sender_id=partner.user_id,
            content=p["msg"],
            is_read=p["read"], # True면 읽음, False면 빨간 배지 뜸
            timestamp=msg_time
        )
        db.add(msg)
        db.commit()
        
        status = "🔴 안읽음" if not p["read"] else "⚪ 읽음"
        print(f"   ↳ 쪽지 전송: \"{p['msg']}\" ({status})")

    print("\n🎉 데이터 5개가 성공적으로 추가되었습니다!")
    print("👉 프론트엔드 페이지를 새로고침 하세요.")
    db.close()

if __name__ == "__main__":
    create_bulk_data()