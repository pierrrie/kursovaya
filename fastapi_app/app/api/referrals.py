# app/api/referrals.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List

from app.db.session import get_session
from app.auth.security import get_current_user
from app.models.user import User, UserRole
from app.models.referral import Referral
from app.schemas.referral import ReferralCreate, ReferralUpdate, ReferralResponse

router = APIRouter()


@router.post("/", response_model=ReferralResponse)
async def create_referral(
    referral_data: ReferralCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Создание направления на исследование или консультацию"""
    if current_user.role != UserRole.DENTIST:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только стоматолог может создавать направления"
        )
    
    # Проверяем существование пациента
    from app.models.patient import Patient
    patient = session.get(Patient, referral_data.patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пациент не найден"
        )
    
    # Если указан visit_id, проверяем существование визита
    if referral_data.visit_id:
        from app.models.visit import Visit
        visit = session.get(Visit, referral_data.visit_id)
        if not visit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Визит не найден"
            )
    
    referral = Referral(
        **referral_data.dict(),
        doctor_id=current_user.id
    )
    
    session.add(referral)
    session.commit()
    session.refresh(referral)
    
    return referral


@router.get("/patient/{patient_id}", response_model=List[ReferralResponse])
async def get_patient_referrals(
    patient_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Получение всех направлений пациента"""
    if current_user.role not in [UserRole.DENTIST, UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав"
        )
    
    # Проверяем существование пациента
    from app.models.patient import Patient
    patient = session.get(Patient, patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пациент не найден"
        )
    
    referrals = session.exec(
        select(Referral)
        .where(Referral.patient_id == patient_id)
        .order_by(Referral.date.desc())
    ).all()
    
    return referrals


@router.put("/{referral_id}", response_model=ReferralResponse)
async def update_referral(
    referral_id: int,
    referral_update: ReferralUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Обновление направления (например, добавление результата)"""
    referral = session.get(Referral, referral_id)
    if not referral:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Направление не найдено"
        )
    
    # Проверяем права
    if current_user.role != UserRole.DENTIST and current_user.id != referral.doctor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для обновления этого направления"
        )
    
    # Обновляем только переданные поля
    update_data = referral_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(referral, field, value)
    
    session.add(referral)
    session.commit()
    session.refresh(referral)
    
    return referral


@router.get("/", response_model=List[ReferralResponse])
async def get_referrals(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Получение направлений текущего пользователя"""
    if current_user.role not in [UserRole.DENTIST, UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав"
        )
    
    # Стоматолог видит только свои направления
    if current_user.role == UserRole.DENTIST:
        referrals = session.exec(
            select(Referral)
            .where(Referral.doctor_id == current_user.id)
            .order_by(Referral.date.desc())
        ).all()
    else:
        # Админ и менеджер видят все
        referrals = session.exec(
            select(Referral)
            .order_by(Referral.date.desc())
        ).all()
    
    return referrals


@router.get("/admin", response_model=List[ReferralResponse])
async def get_all_referrals(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Получение всех направлений (только для администратора)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только администратор может просматривать все направления"
        )
    
    referrals = session.exec(
        select(Referral)
        .order_by(Referral.date.desc())
    ).all()
    
    return referrals