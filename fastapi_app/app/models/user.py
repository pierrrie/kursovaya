# app/models/user.py
from sqlmodel import SQLModel, Field
from typing import Optional
from enum import Enum

class UserRole(str, Enum):
    ADMIN = "administrator"
    MANAGER = "manager"
    DENTIST = "dentist"

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    password_hash: str
    role: UserRole = Field(default=UserRole.MANAGER)
    is_active: bool = Field(default=True)
