from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List
from datetime import datetime, date, timedelta

from app.db.session import get_session
from app.auth.security import get_current_user
from app.models.user import User, UserRole
from app.models.appointment import Appointment, AppointmentStatus
from app.models.visit import Visit
from app.models.patient import Patient
from app.schemas.appointment import AppointmentCreate, AppointmentResponse
from app.schemas.visit import VisitResponse

router = APIRouter()

@router.get("/schedule/today", response_model=List[AppointmentResponse])
async def get_today_schedule(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Получить расписание врача на сегодня"""
    if current_user.role != UserRole.DENTIST:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступно только для стоматологов"
        )
    
    today = datetime.now().date()
    
    appointments = session.exec(
        select(Appointment)
        .where(Appointment.doctor_id == current_user.id)
        .where(Appointment.date == today)
        .where(Appointment.status == AppointmentStatus.ACTIVE)
        .order_by(Appointment.time)
    ).all()
    
    return appointments

@router.get("/schedule/{schedule_date}", response_model=List[AppointmentResponse])
async def get_schedule_by_date(
    schedule_date: date,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Получить расписание врача на указанную дату"""
    if current_user.role != UserRole.DENTIST:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступно только для стоматологов"
        )
    
    appointments = session.exec(
        select(Appointment)
        .where(Appointment.doctor_id == current_user.id)
        .where(Appointment.date == schedule_date)
        .where(Appointment.status == AppointmentStatus.ACTIVE)
        .order_by(Appointment.time)
    ).all()
    
    return appointments

@router.get("/patients/waiting")
async def get_waiting_patients(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Получить список пациентов, ожидающих приема сейчас"""
    if current_user.role != UserRole.DENTIST:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступно только для стоматологов"
        )
    
    now = datetime.now()
    current_time = now.time()
    
    # Пациенты с записью на сегодня, время которых уже наступило,
    # но визит еще не создан
    today_appointments = session.exec(
        select(Appointment, Patient)
        .join(Patient, Patient.id == Appointment.patient_id)
        .where(Appointment.doctor_id == current_user.id)
        .where(Appointment.date == now.date())
        .where(Appointment.status == AppointmentStatus.ACTIVE)
        .where(Appointment.time <= current_time)
    ).all()
    
    # Проверяем, есть ли уже визиты для этих записей
    waiting_patients = []
    for appointment, patient in today_appointments:
        # Проверяем, не создан ли уже визит
        existing_visit = session.exec(
            select(Visit)
            .where(Visit.patient_id == patient.id)
            .where(Visit.doctor_id == current_user.id)
            .where(Visit.datetime >= datetime.combine(now.date(), appointment.time))
        ).first()
        
        if not existing_visit:
            waiting_patients.append({
                "appointment": appointment,
                "patient": patient,
                "appointment_time": appointment.time
            })
    
    return waiting_patients

@router.post("/appointment")
async def create_appointment_from_diary(
    appointment_data: AppointmentCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Врач создает запись на прием через дневник"""
    if current_user.role != UserRole.DENTIST:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступно только для стоматологов"
        )
    
    # Проверяем, не занято ли это время у врача
    existing_appointment = session.exec(
        select(Appointment)
        .where(Appointment.doctor_id == current_user.id)
        .where(Appointment.date == appointment_data.date)
        .where(Appointment.time == appointment_data.time)
        .where(Appointment.status == AppointmentStatus.ACTIVE)
    ).first()
    
    if existing_appointment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Это время уже занято"
        )
    
    appointment = Appointment(**appointment_data.dict())
    session.add(appointment)
    session.commit()
    session.refresh(appointment)
    
    return appointment