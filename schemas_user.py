from pydantic import BaseModel

class LoginIn(BaseModel):
    username: str
    password: str

class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "operator"

class UserOut(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool