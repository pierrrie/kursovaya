# app/api/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlmodel import Session

from app.db.session import get_session
from app.auth.security import (
    verify_password,
    create_access_token,
    get_password_hash,
)
from app.models.user import User
from app.schemas.auth import UserLogin, UserRegister, Token

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(
    username: str = Form(...),  # Добавляем поддержку form-data
    password: str = Form(...),
    session: Session = Depends(get_session),
):
    # Также поддерживаем JSON
    user = session.query(User).filter(User.username == username).first()

    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверные учетные данные",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь заблокирован",
        )

    access_token = create_access_token(
        data={
            "sub": user.username,
            "user_id": user.id,
            "role": user.role,
        }
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        username=user.username,
        role=user.role,
    )


@router.post("/register", response_model=Token)
async def register(
    user_data: UserRegister,
    session: Session = Depends(get_session),
):
    # Проверка существующего пользователя
    existing_user = (
        session.query(User).filter(User.username == user_data.username).first()
    )
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким логином уже существует",
        )

    # Создание нового пользователя
    user = User(
        username=user_data.username,
        password_hash=get_password_hash(user_data.password),
        role=user_data.role,
        is_active=True,
    )

    session.add(user)
    session.commit()
    session.refresh(user)

    # Создаем токен для нового пользователя
    access_token = create_access_token(
        data={
            "sub": user.username,
            "user_id": user.id,
            "role": user.role,
        }
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        username=user.username,
        role=user.role,
    )