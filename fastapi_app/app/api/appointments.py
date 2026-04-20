# app/api/appointments.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List

from app.db.session import get_session
from app.auth.security import get_current_user
from app.models.user import User, UserRole
from app.models.appointment import Appointment
from app.schemas.appointment import (
    AppointmentResponse,
    AppointmentCreate,
    AppointmentUpdate,
)

router = APIRouter()


@router.get("/", response_model=List[AppointmentResponse])
async def get_appointments(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    # стоматолог видит только свои записи, менеджер/админ — все
    query = session.query(Appointment)
    if current_user.role == UserRole.DENTIST:
        query = query.filter(Appointment.doctor_id == current_user.id)
    return query.all()


@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(
    appointment_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    appointment = (
        session.query(Appointment)
        .filter(Appointment.id == appointment_id)
        .first()
    )
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Запись не найдена",
        )

    if current_user.role == UserRole.DENTIST and appointment.doctor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этой записи",
        )

    return appointment


@router.post("/", response_model=AppointmentResponse)
async def create_appointment(
    data: AppointmentCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.DENTIST]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав",
        )

    if current_user.role == UserRole.DENTIST and data.doctor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Стоматолог может создавать запись только для себя",
        )

    appointment = Appointment(**data.dict())
    session.add(appointment)
    session.commit()
    session.refresh(appointment)
    return appointment


@router.put("/{appointment_id}", response_model=AppointmentResponse)
async def update_appointment(
    appointment_id: int,
    data: AppointmentUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.DENTIST]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав",
        )

    appointment = (
        session.query(Appointment)
        .filter(Appointment.id == appointment_id)
        .first()
    )
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Запись не найдена",
        )

    # стоматолог может редактировать только свои записи
    if (
        current_user.role == UserRole.DENTIST
        and appointment.doctor_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нельзя изменять чужие записи",
        )

    for key, value in data.dict(exclude_unset=True).items():
        setattr(appointment, key, value)

    session.commit()
    session.refresh(appointment)
    return appointment


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_appointment(
    appointment_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав",
        )

    appointment = (
        session.query(Appointment)
        .filter(Appointment.id == appointment_id)
        .first()
    )
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Запись не найдена",
        )

    session.delete(appointment)
    session.commit()
    return
