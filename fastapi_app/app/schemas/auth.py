# app/schemas/auth.py
from pydantic import BaseModel
from typing import Optional
from app.models.user import UserRole


class UserLogin(BaseModel):
    username: str
    password: str


class UserRegister(BaseModel):
    username: str
    password: str
    role: UserRole = UserRole.MANAGER  # по умолчанию менеджер


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    role: UserRole
