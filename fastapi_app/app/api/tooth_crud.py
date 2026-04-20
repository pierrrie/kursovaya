from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List
from pydantic import ValidationError

from app.db.session import get_session
from app.auth.security import get_current_user
from app.models.user import User, UserRole
from app.models.tooth import Tooth
from app.schemas.tooth import ToothCreate, ToothUpdate, ToothResponse

router = APIRouter()

def validate_tooth_number(number: int) -> bool:
    """Валидация номера зуба"""
    # Стоматологическая нумерация FDI: 11-18, 21-28, 31-38, 41-48
    # Или 1-32 для универсальной нумерации
    return 1 <= number <= 48

@router.get("/", response_model=List[ToothResponse])
async def get_all_teeth(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Получить все записи о зубах"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.DENTIST]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав"
        )
    
    # Стоматолог видит только зубы своих пациентов
    if current_user.role == UserRole.DENTIST:
        teeth = session.exec(
            select(Tooth)
            .join(Tooth.patient)
            .where(Tooth.patient.has(visits=current_user.id))
        ).all()
    else:
        teeth = session.exec(select(Tooth)).all()
    
    return teeth

@router.get("/patient/{patient_id}", response_model=List[ToothResponse])
async def get_patient_teeth(
    patient_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Получить зубную формулу пациента"""
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
                detail="Нет доступа к зубной формуле этого пациента"
            )
    
    teeth = session.exec(
        select(Tooth)
        .where(Tooth.patient_id == patient_id)
        .order_by(Tooth.number)
    ).all()
    
    return teeth

@router.get("/patient/{patient_id}/tooth/{tooth_number}", response_model=ToothResponse)
async def get_specific_tooth(
    patient_id: int,
    tooth_number: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Получить информацию о конкретном зубе пациента"""
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
                detail="Нет доступа к зубам этого пациента"
            )
    
    tooth = session.exec(
        select(Tooth)
        .where(Tooth.patient_id == patient_id)
        .where(Tooth.number == tooth_number)
    ).first()
    
    if not tooth:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Запись о зубе не найдена"
        )
    
    return tooth

@router.post("/patient/{patient_id}", response_model=ToothResponse)
async def create_tooth_record(
    patient_id: int,
    tooth_data: ToothCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Создать запись о зубе"""
    if current_user.role not in [UserRole.DENTIST, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только стоматолог или администратор может создавать записи о зубах"
        )
    
    # Валидация номера зуба
    if not validate_tooth_number(tooth_data.number):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Номер зуба должен быть от 1 до 48"
        )
    
    # Проверяем существование пациента
    from app.models.patient import Patient
    patient = session.get(Patient, patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пациент не найден"
        )
    
    # Проверяем, не существует ли уже запись о таком зубе
    existing_tooth = session.exec(
        select(Tooth)
        .where(Tooth.patient_id == patient_id)
        .where(Tooth.number == tooth_data.number)
    ).first()
    
    if existing_tooth:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Запись об этом зубе уже существует"
        )
    
    tooth = Tooth(
        **tooth_data.dict(),
        patient_id=patient_id
    )
    
    session.add(tooth)
    session.commit()
    session.refresh(tooth)
    
    return tooth

@router.put("/{tooth_id}", response_model=ToothResponse)
async def update_tooth_record(
    tooth_id: int,
    tooth_data: ToothUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Обновить запись о зубе"""
    tooth = session.get(Tooth, tooth_id)
    if not tooth:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Запись о зубе не найдена"
        )
    
    # Проверка прав доступа
    if current_user.role == UserRole.DENTIST:
        from app.models.visit import Visit
        has_access = session.exec(
            select(Visit)
            .where(Visit.patient_id == tooth.patient_id)
            .where(Visit.doctor_id == current_user.id)
        ).first()
        
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет прав для редактирования этой записи"
            )
    
    # Валидация номера зуба, если он обновляется
    if tooth_data.number is not None and not validate_tooth_number(tooth_data.number):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Номер зуба должен быть от 1 до 48"
        )
    
    # Обновляем только переданные поля
    update_data = tooth_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(tooth, key, value)
    
    session.add(tooth)
    session.commit()
    session.refresh(tooth)
    
    return tooth

@router.delete("/{tooth_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tooth_record(
    tooth_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Удалить запись о зубе"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только администратор может удалять записи о зубах"
        )
    
    tooth = session.get(Tooth, tooth_id)
    if not tooth:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Запись о зубе не найдена"
        )
    
    session.delete(tooth)
    session.commit()