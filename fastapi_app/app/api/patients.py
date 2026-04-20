# app/api/patients.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select, func
from typing import List
from datetime import date

from app.db.session import get_session
from app.auth.security import get_current_user
from app.models.user import User, UserRole
from app.models.patient import Patient
# ДОБАВЛЯЕМ ИМПОРТ:
from app.models.visit import Visit
from app.schemas.patient import (
    PatientResponse,
    PatientCreate,
    PatientUpdate,
)

router = APIRouter()


@router.get("/", response_model=List[PatientResponse])
async def get_patients(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    patients = session.query(Patient).all()
    return patients


@router.get("/search/by-visit-date/{visit_date}", response_model=List[PatientResponse])
async def search_patients_by_visit_date(
    visit_date: date,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Поиск пациентов по дате посещения"""
    if current_user.role not in [UserRole.DENTIST, UserRole.MANAGER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав"
        )
    
    # Ищем пациентов, у которых были визиты в указанную дату
    patients = session.exec(
        select(Patient)
        .join(Visit, Patient.id == Visit.patient_id)
        .where(func.date(Visit.datetime) == visit_date)
        .distinct()
    ).all()
    
    return patients


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    patient = session.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пациент не найден",
        )
    return patient


@router.post("/", response_model=PatientResponse)
async def create_patient(
    patient_data: PatientCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    # добавлять пациентов могут администратор и менеджер
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав",
        )

    patient = Patient(**patient_data.dict())
    session.add(patient)
    session.commit()
    session.refresh(patient)
    return patient


@router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: int,
    patient_data: PatientUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав",
        )

    patient = session.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пациент не найден",
        )

    for key, value in patient_data.dict(exclude_unset=True).items():
        setattr(patient, key, value)

    session.commit()
    session.refresh(patient)
    return patient


@router.get("/by-visit-date/", response_model=List[PatientResponse])
async def get_patients_by_visit_date(
    visit_date: date,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Поиск пациентов по дате посещения"""
    if current_user.role not in [UserRole.DENTIST, UserRole.MANAGER, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    # Находим пациентов, у которых были визиты в указанную дату
    # Теперь Visit импортирован и доступен
    patients = session.exec(
        select(Patient)
        .join(Visit, Visit.patient_id == Patient.id)
        .where(func.date(Visit.datetime) == visit_date)
        .distinct()
    ).all()
    
    return patients


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(
    patient_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав",
        )

    patient = session.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пациент не найден",
        )

    session.delete(patient)
    session.commit()
    return