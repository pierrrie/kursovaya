# app/api/admin.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List

from app.db.session import get_session
from app.auth.security import get_current_user
from app.models.user import User, UserRole
from app.schemas.user import UserResponse, UserRoleUpdate

router = APIRouter()


@router.get("/users/dentists", response_model=List[UserResponse])
async def get_dentists(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Получить список врачей (dentist)."""
    return session.query(User).filter(User.role == UserRole.DENTIST).all()


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав",
        )

    return session.query(User).all()


@router.put("/users/{user_id}/role", response_model=UserResponse)
async def change_user_role(
    user_id: int,
    data: UserRoleUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав",
        )

    user = session.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )

    user.role = data.role
    session.commit()
    session.refresh(user)
    return user
