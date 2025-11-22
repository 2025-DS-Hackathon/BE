# BE/reset_and_setup_all.py
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.getcwd())

from app.db import SessionLocal
from app import models

def reset_and_setup_all():
    db = SessionLocal()
    print("--- 🔥 [통합] 데이터 초기화 및 완벽 세팅 시작 ---")

    # -------------------------------------------------------
    # 1. 내 계정 찾기 (로그인 유지)
    # -------------------------------------------------------
    me = db.query(models.User).filter(models.User.social_provider.isnot(None)).first()
    if not me:
        # 카카오 유저 없으면 최근 유저로
        me = db.query(models.User).order_by(models.User.updated_at.desc()).first()
    
    if not me:
        print("❌ 로그인된 유저가 없습니다. 웹에서 로그인 먼저 해주세요!")
        return

    print(f"👤 내 계정 보호: {me.nickname} (ID: {me.user_id})")

    # -------------------------------------------------------
    # 2. 데이터 삭제 (내 계정 빼고 전부)
    # -------------------------------------------------------
    print("🧹 기존 데이터 삭제 중...")
    db.query(models.Report).delete()
    db.query(models.Block).delete()
    db.query(models.Notification).delete()
    db.query(models.Message).delete()
    db.query(models.MatchingQueue).delete()
    db.query(models.Talent).delete()
    
    # 나를 제외한 모든 유저 삭제
    db.query(models.User).filter(models.User.user_id != me.user_id).delete()
    db.commit()

    # -------------------------------------------------------
    # 3. [Main 화면용] 내 재능 등록
    # -------------------------------------------------------
    print("📝 내 재능 등록 중...")
    # Teach
    t1 = models.Talent(user_id=me.user_id, type="Teach", category="디지털/IT", title="키오스크 주문하는 법", description="터치스크린 사용법, 천천히 알려드려요.", tags="키오스크,IT")
    # Learn
    t2 = models.Talent(user_id=me.user_id, type="Learn", category="요리/생활", title="집반찬 배우기", description="맛있는 반찬 먹고 싶어요.")
    db.add(t1); db.add(t2)
    db.commit()

    # -------------------------------------------------------
    # 4. [쪽지함용] 다른 유저 5명 + 대화 생성
    # -------------------------------------------------------
    print("📨 쪽지함 데이터(5명) 생성 중...")
    inbox_partners = [
        ("김기타", "취미/예술", "안녕하세요! 재능 교환하고 싶어서 연락드렸어요.", 10, False), 
        ("박헬스", "건강/운동", "반갑습니다 ㅎㅎ 운동 관련해서 여쭤보고 싶어요.", 30, True),       
        ("이영어", "외국어", "Hi! Nice to meet you. I'd like to learn.", 60, False),        
        ("최엑셀", "디지털/IT", "안녕하세요! 엑셀 배우고 싶습니다.", 120, True),    
        ("정뜨개", "취미/예술", "안녕하세요~ 잘 부탁드립니다!", 300, True),             
    ]

    for name, cat, msg_content, mins, is_read in inbox_partners:
        # 유저 생성
        p = models.User(nickname=name, user_type="YOUNG", is_matching_available=True, terms_agreed=True)
        db.add(p)
        db.commit()
        db.refresh(p)

        # 재능 등록 (상대방도 재능이 있어야 자연스러움)
        db.add(models.Talent(user_id=p.user_id, type="Teach", category=cat, title=f"{name}의 재능", description=".."))
        
        # 매칭 생성 (CONFIRMED)
        match = models.MatchingQueue(
            user_a_id=me.user_id, user_b_id=p.user_id, status="CONFIRMED",
            shared_category=cat, requested_at=datetime.utcnow(), confirmed_at=datetime.utcnow()
        )
        db.add(match)
        db.commit()
        db.refresh(match)

        # 메시지 생성
        msg_time = datetime.utcnow() + timedelta(hours=9) - timedelta(minutes=mins)
        msg = models.Message(match_id=match.match_id, sender_id=p.user_id, content=msg_content, is_read=is_read, timestamp=msg_time)
        db.add(msg)
    
    db.commit()

    # -------------------------------------------------------
    # 5. [재능교환 & 채팅추가용] 이서진 (12번방)
    # -------------------------------------------------------
    print("💘 파트너 '이서진' (12번방) 생성 중...")
    
    # 이서진 유저
    sj = models.User(nickname="이서진 (가상 파트너)", user_type="SENIOR", is_matching_available=True, terms_agreed=True)
    db.add(sj)
    db.commit()
    db.refresh(sj)

    # 이서진 재능 (요리)
    sj_t1 = models.Talent(user_id=sj.user_id, type="Teach", category="요리/생활", title="집반찬 만드는 법", description="제철 재료로 만드는 건강한 반찬.", tags="반찬,한식")
    sj_t2 = models.Talent(user_id=sj.user_id, type="Learn", category="디지털/IT", title="키오스크 배우기", description="기계가 어려워요.")
    db.add(sj_t1); db.add(sj_t2)

    # 매칭 (12번 고정)
    # ★ 중요: 메시지는 아직 안 넣음! (수락하면 채팅방에 메시지가 생기도록 연출)
    match_12 = models.MatchingQueue(
        match_id=12, # ID 고정
        user_a_id=me.user_id, user_b_id=sj.user_id,
        status="CONFIRMED", shared_category="재능 교환",
        requested_at=datetime.utcnow(), confirmed_at=datetime.utcnow()
    )
    db.add(match_12)
    db.commit()

    print("\n✅ 모든 데이터 준비 완료!")
    print("1. [쪽지함] 확인 -> 5개의 대화가 보여야 함")
    print("2. [재능 교환] 확인 (Main -> 카드 클릭) -> 이서진(요리) vs 나(키오스크)")
    print("3. [수락하기] 클릭 -> 채팅방으로 이동되는지 확인")

if __name__ == "__main__":
    reset_and_setup_all()