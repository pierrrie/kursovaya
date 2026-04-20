# app/api/dentist_diary.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List
from datetime import datetime, date, timedelta

from app.db.session import get_session
from app.auth.security import get_current_user
from app.models.user import User, UserRole
from app.models.appointment import Appointment, AppointmentStatus
from app.models.visit import Visit
from app.models.work import Work
from app.schemas.appointment import AppointmentCreate, AppointmentResponse
from app.schemas.visit import VisitResponse

router = APIRouter()


@router.get("/day", response_model=List[AppointmentResponse])  # Изменяем путь
async def get_day_schedule(
    day: date,  # Теперь это query параметр
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.DENTIST:
        raise HTTPException(status_code=403, detail="Только для стоматологов")
    
    appointments = session.exec(
        select(Appointment)
        .where(Appointment.doctor_id == current_user.id)
        .where(Appointment.date == day)
        .where(Appointment.status == AppointmentStatus.ACTIVE)
        .order_by(Appointment.time)
    ).all()
    
    return appointments


@router.get("/week", response_model=List[AppointmentResponse])
async def get_week_schedule(
    week_start: date,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.DENTIST:
        raise HTTPException(status_code=403, detail="Только для стоматологов")
    
    week_end = week_start + timedelta(days=7)
    
    appointments = session.exec(
        select(Appointment)
        .where(Appointment.doctor_id == current_user.id)
        .where(Appointment.date >= week_start)
        .where(Appointment.date < week_end)
        .where(Appointment.status == AppointmentStatus.ACTIVE)
        .order_by(Appointment.date, Appointment.time)
    ).all()
    
    return appointments


@router.get("/today-visits", response_model=List[VisitResponse])
async def get_today_visits(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.DENTIST:
        raise HTTPException(status_code=403, detail="Только для стоматологов")
    
    today = datetime.now().date()
    
    visits = session.exec(
        select(Visit)
        .where(Visit.doctor_id == current_user.id)
        .where(Visit.datetime >= datetime.combine(today, datetime.min.time()))
        .where(Visit.datetime <= datetime.combine(today, datetime.max.time()))
        .order_by(Visit.datetime)
    ).all()
    
    return visits


@router.post("/appointments", response_model=AppointmentResponse)
async def create_appointment_from_diary(
    data: AppointmentCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Врач создает запись на прием через дневник"""
    if current_user.role != UserRole.DENTIST:
        raise HTTPException(status_code=403, detail="Только для стоматологов")
    
    appointment = Appointment(**data.dict())
    session.add(appointment)
    session.commit()
    session.refresh(appointment)
    return appointment


@router.get("/patient-history/{patient_id}")
async def get_patient_history(
    patient_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Полная история пациента для врача"""
    if current_user.role not in [UserRole.DENTIST, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    # Получаем все визиты пациента
    visits = session.exec(
        select(Visit)
        .where(Visit.patient_id == patient_id)
        .order_by(Visit.datetime.desc())
    ).all()
    
    # Получаем все работы по визитам
    works_by_visit = {}
    for visit in visits:
        works = session.exec(
            select(Work)
            .where(Work.visit_id == visit.id)
        ).all()
        works_by_visit[visit.id] = works
    
    return {
        "visits": visits,
        "works_by_visit": works_by_visit
    }