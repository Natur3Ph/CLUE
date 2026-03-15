from backend.models import SessionLocal, User
from backend.security import hash_password


def create_admin():
    db = SessionLocal()

    admin = User(
        username="admin",
        hashed_password=hash_password("123456"),
        role="admin"
    )

    db.add(admin)
    db.commit()

    print("管理员创建成功：admin / 123456")


if __name__ == "__main__":
    create_admin()