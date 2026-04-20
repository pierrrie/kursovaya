from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List, Optional

from app.db.session import get_session
from app.auth.security import get_current_user
from app.models.user import User, UserRole
from app.models.research import Research
from app.schemas.research import ResearchCreate, ResearchUpdate, ResearchResponse

router = APIRouter()

@router.get("/", response_model=List[ResearchResponse])
async def get_all_research(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Получить все исследования"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.DENTIST]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав"
        )
    
    # Стоматолог видит только исследования своих пациентов через визиты
    if current_user.role == UserRole.DENTIST:
        research_list = session.exec(
            select(Research)
            .join(Research.visit)
            .where(Research.visit.has(doctor_id=current_user.id))
        ).all()
    else:
        research_list = session.exec(select(Research)).all()
    
    return research_list

@router.get("/{research_id}", response_model=ResearchResponse)
async def get_research(
    research_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Получить исследование по ID"""
    research = session.get(Research, research_id)
    if not research:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Исследование не найдено"
        )
    
    # Проверка прав доступа
    if current_user.role == UserRole.DENTIST:
        # Проверяем, принадлежит ли визит стоматологу
        from app.models.visit import Visit
        visit = session.get(Visit, research.visit_id) if research.visit_id else None
        if not visit or visit.doctor_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет доступа к этому исследованию"
            )
    
    return research

@router.get("/patient/{patient_id}", response_model=List[ResearchResponse])
async def get_patient_research(
    patient_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Получить все исследования пациента"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.DENTIST]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав"
        )
    
    # Стоматолог проверяет, есть ли у него визиты с этим пациентом
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
                detail="Нет доступа к исследованиям этого пациента"
            )
    
    research_list = session.exec(
        select(Research)
        .where(Research.patient_id == patient_id)
        .order_by(Research.datetime.desc())
    ).all()
    
    return research_list

@router.post("/patient/{patient_id}", response_model=ResearchResponse)
async def create_research(
    patient_id: int,
    research_data: ResearchCreate,
    visit_id: Optional[int] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Создать новое исследование"""
    # Только стоматологи и администраторы могут создавать исследования
    if current_user.role not in [UserRole.DENTIST, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для создания исследования"
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
                detail="Нельзя создать исследование для чужого визита"
            )
    
    research = Research(
        **research_data.dict(),
        patient_id=patient_id,
        visit_id=visit_id,
        created_by=current_user.id  # Добавляем кто создал
    )
    
    session.add(research)
    session.commit()
    session.refresh(research)
    
    return research

@router.put("/{research_id}", response_model=ResearchResponse)
async def update_research(
    research_id: int,
    research_data: ResearchUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Обновить исследование"""
    research = session.get(Research, research_id)
    if not research:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Исследование не найдено"
        )
    
    # Проверка прав доступа
    if current_user.role == UserRole.DENTIST:
        from app.models.visit import Visit
        visit = session.get(Visit, research.visit_id) if research.visit_id else None
        if not visit or visit.doctor_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет прав для редактирования этого исследования"
            )
    
    # Обновляем только переданные поля
    update_data = research_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(research, key, value)
    
    session.add(research)
    session.commit()
    session.refresh(research)
    
    return research

@router.delete("/{research_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_research(
    research_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Удалить исследование"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только администратор может удалять исследования"
        )
    
    research = session.get(Research, research_id)
    if not research:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Исследование не найдено"
        )
    
    session.delete(research)
    session.commit()