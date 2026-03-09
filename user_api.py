from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models import User, get_db
from schemas_user import LoginIn, UserCreate
from security import hash_password, verify_password, create_access_token
from auth import get_current_user

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()

    if not user:
        raise HTTPException(status_code=400, detail="用户不存在")

    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="密码错误")

    if not user.is_active:
        raise HTTPException(status_code=400, detail="用户已禁用")

    token = create_access_token({"user_id": user.id})

    return {
        "status": "success",
        "data": {
            "token": token,
            "username": user.username,
            "role": user.role
        }
    }


@router.get("")
def list_users(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 这里只做最小权限控制：登录后可看
    # 如果你想严格一点，可以改成只允许 admin 查看
    users = db.query(User).order_by(User.id.desc()).all()

    data = []
    for u in users:
        data.append({
            "id": u.id,
            "username": u.username,
            "role": u.role,
            "is_active": bool(u.is_active),
            "created_at": u.created_at.isoformat() if u.created_at else None,
        })

    return {"status": "success", "data": data}


@router.post("")
def create_user(
    payload: UserCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 只有管理员能创建用户
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可创建用户")

    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="用户已存在")

    user = User(
        username=payload.username.strip(),
        hashed_password=hash_password(payload.password),
        role=payload.role,
        is_active=True
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "status": "success",
        "data": {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "is_active": user.is_active
        }
    }