# app/api/visits.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime

from app.db.session import get_session
from app.auth.security import get_current_user
from app.models.user import User, UserRole
from app.models.visit import Visit
from app.models.patient import Patient
from app.schemas.visit import VisitCreate, VisitResponse, VisitUpdate

router = APIRouter()

@router.post("/", response_model=VisitResponse)
async def create_visit(
    visit_data: VisitCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Создать новый визит пациента"""
    if current_user.role not in [UserRole.DENTIST, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только стоматолог или администратор может создавать визиты"
        )
    
    # Проверяем существование пациента
    patient = session.get(Patient, visit_data.patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пациент не найден"
        )
    
    # Если doctor_id не указан, используем текущего пользователя
    doctor_id = visit_data.doctor_id if visit_data.doctor_id else current_user.id
    
    visit = Visit(
        **visit_data.dict(exclude={'doctor_id'}),
        doctor_id=doctor_id
    )
    
    session.add(visit)
    session.commit()
    session.refresh(visit)
    
    return visit

@router.get("/", response_model=List[VisitResponse])
async def get_visits(
    patient_id: Optional[int] = None,
    doctor_id: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Получить список визитов с фильтрацией"""
    if current_user.role not in [UserRole.DENTIST, UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав"
        )
    
    query = select(Visit)
    
    # Фильтрация по пациенту
    if patient_id:
        query = query.where(Visit.patient_id == patient_id)
    
    # Фильтрация по врачу
    if doctor_id:
        query = query.where(Visit.doctor_id == doctor_id)
    
    # Фильтрация по дате
    if date_from:
        query = query.where(Visit.datetime >= date_from)
    if date_to:
        query = query.where(Visit.datetime <= date_to)
    
    # Стоматолог видит только свои визиты
    if current_user.role == UserRole.DENTIST:
        query = query.where(Visit.doctor_id == current_user.id)
    
    query = query.order_by(Visit.datetime.desc())
    
    visits = session.exec(query).all()
    return visits

@router.get("/patient/{patient_id}", response_model=List[VisitResponse])
async def get_patient_visits(
    patient_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Получить все визиты пациента"""
    if current_user.role not in [UserRole.DENTIST, UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав"
        )
    
    # Проверяем существование пациента
    patient = session.get(Patient, patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пациент не найден"
        )
    
    query = select(Visit).where(Visit.patient_id == patient_id)
    
    # Стоматолог видит только свои визиты
    if current_user.role == UserRole.DENTIST:
        query = query.where(Visit.doctor_id == current_user.id)
    
    query = query.order_by(Visit.datetime.desc())
    
    visits = session.exec(query).all()
    return visits

@router.get("/{visit_id}", response_model=VisitResponse)
async def get_visit(
    visit_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Получить визит по ID"""
    visit = session.get(Visit, visit_id)
    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Визит не найден"
        )
    
    # Проверка прав доступа
    if current_user.role == UserRole.DENTIST and visit.doctor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этому визиту"
        )
    
    return visit

@router.put("/{visit_id}", response_model=VisitResponse)
async def update_visit(
    visit_id: int,
    visit_data: VisitUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Обновить визит"""
    visit = session.get(Visit, visit_id)
    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Визит не найден"
        )
    
    # Проверка прав доступа
    if current_user.role == UserRole.DENTIST and visit.doctor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для редактирования этого визита"
        )
    
    # Обновляем только переданные поля
    update_data = visit_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(visit, key, value)
    
    session.add(visit)
    session.commit()
    session.refresh(visit)
    
    return visit

@router.delete("/{visit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_visit(
    visit_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Удалить визит"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только администратор может удалять визиты"
        )
    
    visit = session.get(Visit, visit_id)
    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Визит не найден"
        )
    
    session.delete(visit)
    session.commit()