# app/schemas/user.py
from pydantic import BaseModel
from typing import Optional
from app.models.user import UserRole


class UserBase(BaseModel):
    username: str
    role: UserRole
    is_active: bool = True


class UserResponse(UserBase):
    id: int

    class Config:
        orm_mode = True


class UserRoleUpdate(BaseModel):
    role: UserRole
