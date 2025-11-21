# seed.py
from app.db import SessionLocal, engine
from app import models
from passlib.context import CryptContext

# 비밀번호 해싱 도구
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def init_db():
    db = SessionLocal()
    
    # 1. 비밀번호 "1234"로 통일
    hashed_pw = get_password_hash("1234")

    # 2. 샘플 유저 데이터 (청년/시니어 섞어서)
    users_data = [
        {"email": "senior1@test.com", "nickname": "김부자", "year": 1960, "type": "SENIOR"},
        {"email": "young1@test.com", "nickname": "코딩왕", "year": 1998, "type": "YOUNG"},
        {"email": "senior2@test.com", "nickname": "요리맘", "year": 1965, "type": "SENIOR"},
        {"email": "young2@test.com", "nickname": "헬스보이", "year": 2000, "type": "YOUNG"},
        {"email": "young3@test.com", "nickname": "여행가", "year": 1995, "type": "YOUNG"},
    ]

    created_users = []
    print("🚀 유저 생성 중...")
    for u in users_data:
        # 이미 있는지 확인
        existing = db.query(models.User).filter(models.User.email == u["email"]).first()
        if not existing:
            user = models.User(
                email=u["email"],
                nickname=u["nickname"],
                hashed_password=hashed_pw,
                birth_year=u["year"],
                user_type=u["type"],
                terms_agreed=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            created_users.append(user)
            print(f"✅ 유저 생성 완료: {user.nickname}")
        else:
            created_users.append(existing)
            print(f"ℹ️ 이미 존재함: {existing.nickname}")

    # 3. 샘플 재능 데이터 (서로 매칭되도록 구성)
    # 구조: (유저인덱스, 타입, 카테고리, 제목, 내용, 태그)
    talents_data = [
        # 김부자(0): 가르침=부동산 / 배움=IT (-> 코딩왕과 매칭 가능)
        (0, "Teach", "요리/생활", "전월세 계약서 체크하는 법", "등기부등본 보는 법부터 특약 사항까지 꼼꼼히 알려드려요.", "부동산,전월세,자취"),
        (0, "Learn", "디지털/IT", "스마트폰 뱅킹 배우고 싶어요", "은행 가기 귀찮은데 폰으로 하는 법을 모르겠네요.", "어플,송금"),

        # 코딩왕(1): 가르침=IT / 배움=부동산 (-> 김부자와 매칭 가능)
        (1, "Teach", "디지털/IT", "React 기초 과외 해드립니다", "컴공 전공생입니다. 웹사이트 만드는 법 알려드려요.", "리액트,코딩,웹"),
        (1, "Learn", "요리/생활", "자취방 구하는 팁좀 주세요", "사회 초년생이라 집 계약이 너무 무서워요.", "부동산,이사"),

        # 요리맘(2): 가르침=요리 / 배움=운동
        (2, "Teach", "요리/생활", "맛있는 김치찌개 끓이는 비법", "조미료 없이 깊은 맛 내는 엄마 손맛 전수합니다.", "한식,집밥"),
        (2, "Learn", "건강/운동", "허리가 아픈데 스트레칭 배우고 싶어요", "집에서 할 수 있는 간단한 요가나 스트레칭 원해요.", "건강,재활"),

        # 헬스보이(3): 가르침=운동 / 배움=요리
        (3, "Teach", "건강/운동", "3대 500 만들어드립니다", "체계적인 웨이트 트레이닝 기초부터 알려드려요.", "헬스,PT"),
        (3, "Learn", "요리/생활", "닭가슴살 맛있게 먹는 법", "식단 관리 중인데 요리를 너무 못해요.", "다이어트,요리"),
        
        # 여행가(4): 가르침=스페인어 / 배움=사진
        (4, "Teach", "외국어", "여행용 스페인어 회화", "남미 배낭여행 경험 살려서 생존 스페인어 알려줌.", "스페인어,여행"),
        (4, "Learn", "취미/예술", "인생샷 찍는 법 배우고 싶어요", "사진 잘 찍는 금손님 찾습니다.", "사진,카메라"),
    ]

    print("🚀 재능 등록 중...")
    for idx, t_type, cat, title, desc, tags in talents_data:
        target_user = created_users[idx]
        
        # 중복 확인 (제목으로 대충 확인)
        existing_talent = db.query(models.Talent).filter(
            models.Talent.user_id == target_user.user_id,
            models.Talent.title == title
        ).first()

        if not existing_talent:
            # DB 모델 필드명에 맞춰서 수정 (talent_type vs type 확인 필요. 여기선 type으로 가정)
            talent = models.Talent(
                user_id=target_user.user_id,
                type=t_type,        # 모델에 따라 talent_type 일수도 있음
                category=cat,
                title=title,
                description=desc,
                tags=tags
            )
            db.add(talent)
            db.commit()
            print(f"✅ 재능 등록 완료: {target_user.nickname} - {title}")

    print("✨ 모든 데이터 생성이 완료되었습니다! ✨")
    db.close()

if __name__ == "__main__":
    init_db()