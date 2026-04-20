from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List, Optional

from app.db.session import get_session
from app.auth.security import get_current_user
from app.models.user import User, UserRole
from app.models.prescription import Prescription
from app.schemas.prescription import PrescriptionCreate, PrescriptionUpdate, PrescriptionResponse

router = APIRouter()

@router.get("/", response_model=List[PrescriptionResponse])
async def get_all_prescriptions(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Получить все назначения"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.DENTIST]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав"
        )
    
    # Стоматолог видит только назначения своих пациентов
    if current_user.role == UserRole.DENTIST:
        prescriptions = session.exec(
            select(Prescription)
            .join(Prescription.visit)
            .where(Prescription.visit.has(doctor_id=current_user.id))
        ).all()
    else:
        prescriptions = session.exec(select(Prescription)).all()
    
    return prescriptions

@router.get("/patient/{patient_id}", response_model=List[PrescriptionResponse])
async def get_patient_prescriptions(
    patient_id: int,
    active_only: bool = False,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Получить назначения пациента"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.DENTIST]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав"
        )
    
    # Проверка доступа стоматолога к пациенту
    if current_user.role == UserRole.DENTIST:
        from app.models.visit import Visit
        has_access = session.exec(
            select(Visit)
            .where(Visit.patient_id == patient_id)
            .where(Visit.doctor_id == current_user.id)
        ).first()
        
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет доступа к назначениям этого пациента"
            )
    
    query = select(Prescription).where(Prescription.patient_id == patient_id)
    
    if active_only:
        from datetime import date
        today = date.today()
        query = query.where(
            (Prescription.start_date <= today) & 
            (Prescription.end_date >= today)
        )
    
    prescriptions = session.exec(query.order_by(Prescription.start_date.desc())).all()
    
    return prescriptions

@router.post("/patient/{patient_id}", response_model=PrescriptionResponse)
async def create_prescription(
    patient_id: int,
    prescription_data: PrescriptionCreate,
    visit_id: Optional[int] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Создать новое назначение"""
    if current_user.role not in [UserRole.DENTIST, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только стоматолог или администратор может создавать назначения"
        )
    
    # Проверяем существование пациента
    from app.models.patient import Patient
    patient = session.get(Patient, patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пациент не найден"
        )
    
    # Если указан visit_id, проверяем принадлежность визита
    if visit_id:
        from app.models.visit import Visit
        visit = session.get(Visit, visit_id)
        if not visit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Визит не найден"
            )
        
        if current_user.role == UserRole.DENTIST and visit.doctor_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нельзя создать назначение для чужого визита"
            )
    
    prescription = Prescription(
        **prescription_data.dict(),
        patient_id=patient_id,
        visit_id=visit_id
    )
    
    session.add(prescription)
    session.commit()
    session.refresh(prescription)
    
    return prescription

@router.put("/{prescription_id}", response_model=PrescriptionResponse)
async def update_prescription(
    prescription_id: int,
    prescription_data: PrescriptionUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Обновить назначение"""
    prescription = session.get(Prescription, prescription_id)
    if not prescription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Назначение не найдено"
        )
    
    # Проверка прав доступа
    if current_user.role == UserRole.DENTIST:
        from app.models.visit import Visit
        visit = session.get(Visit, prescription.visit_id) if prescription.visit_id else None
        if not visit or visit.doctor_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет прав для редактирования этого назначения"
            )
    
    # Обновляем только переданные поля
    update_data = prescription_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(prescription, key, value)
    
    session.add(prescription)
    session.commit()
    session.refresh(prescription)
    
    return prescription

@router.delete("/{prescription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prescription(
    prescription_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Удалить назначение"""
    prescription = session.get(Prescription, prescription_id)
    if not prescription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Назначение не найдено"
        )
    
    # Только администратор или создавший назначение стоматолог
    if current_user.role == UserRole.DENTIST:
        from app.models.visit import Visit
        visit = session.get(Visit, prescription.visit_id) if prescription.visit_id else None
        if not visit or visit.doctor_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет прав для удаления этого назначения"
            )
    
    session.delete(prescription)
    session.commit()