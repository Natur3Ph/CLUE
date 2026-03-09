from models import SessionLocal, User
from security import hash_password

db = SessionLocal()

admin = User(
    username="admin",
    hashed_password=hash_password("123456"),
    role="admin"
)

db.add(admin)
db.commit()

print("管理员创建成功：admin / 123456")