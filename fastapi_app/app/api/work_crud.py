from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List
from datetime import datetime

from app.db.session import get_session
from app.auth.security import get_current_user
from app.models.user import User, UserRole
from app.models.work import Work, WorkStatus
from app.schemas.work import WorkCreate, WorkUpdate, WorkResponse

router = APIRouter()

@router.get("/", response_model=List[WorkResponse])
async def get_all_works(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Получить все работы/наряды"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.DENTIST]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав"
        )
    
    # Стоматолог видит только свои работы
    if current_user.role == UserRole.DENTIST:
        # Используем subquery для получения работ через визиты
        from app.models.visit import Visit
        works = session.exec(
            select(Work)
            .where(Work.visit_id.in_(
                select(Visit.id).where(Visit.doctor_id == current_user.id)
            ))
        ).all()
    else:
        works = session.exec(select(Work)).all()
    
    return works

@router.get("/visit/{visit_id}", response_model=List[WorkResponse])
async def get_works_by_visit(
    visit_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Получить работы по визиту"""
    from app.models.visit import Visit
    
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
            detail="Нет доступа к работам этого визита"
        )
    
    works = session.exec(
        select(Work)
        .where(Work.visit_id == visit_id)
        .order_by(Work.work_date)
    ).all()
    
    return works

@router.get("/patient/{patient_id}", response_model=List[WorkResponse])
async def get_patient_works(
    patient_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Получить все работы по пациенту"""
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
                detail="Нет доступа к работам этого пациента"
            )
    
    works = session.exec(
        select(Work)
        .join(Work.visit)
        .where(Work.visit.has(patient_id=patient_id))
        .order_by(Work.work_date.desc())
    ).all()
    
    return works

@router.post("/visit/{visit_id}", response_model=WorkResponse)
async def create_work(
    visit_id: int,
    work_data: WorkCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Создать наряд на работу"""
    if current_user.role not in [UserRole.DENTIST, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только стоматолог или администратор может создавать наряды"
        )
    
    # Проверяем существование визита
    from app.models.visit import Visit
    visit = session.get(Visit, visit_id)
    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Визит не найден"
        )
    
    # Проверка принадлежности визита
    if current_user.role == UserRole.DENTIST and visit.doctor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нельзя создавать наряд для чужого визита"
        )
    
    # Генерируем номер наряда
    work_order_number = f"WO-{datetime.now().strftime('%Y%m%d')}-{visit_id:04d}"
    
    work = Work(
        **work_data.dict(),
        visit_id=visit_id,
        work_order_number=work_order_number,
        status=WorkStatus.PLANNED,
        work_date=datetime.now()
    )
    
    session.add(work)
    session.commit()
    session.refresh(work)
    
    return work

@router.put("/{work_id}", response_model=WorkResponse)
async def update_work(
    work_id: int,
    work_data: WorkUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Обновить работу/наряд"""
    work = session.get(Work, work_id)
    if not work:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Работа не найдена"
        )
    
    # Проверка прав доступа
    if current_user.role == UserRole.DENTIST:
        from app.models.visit import Visit
        visit = session.get(Visit, work.visit_id)
        if not visit or visit.doctor_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет прав для редактирования этой работы"
            )
    
    # Обновляем только переданные поля
    update_data = work_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(work, key, value)
    
    session.add(work)
    session.commit()
    session.refresh(work)
    
    return work

@router.put("/{work_id}/complete", response_model=WorkResponse)
async def complete_work(
    work_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Отметить работу как выполненную"""
    work = session.get(Work, work_id)
    if not work:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Работа не найдена"
        )
    
    # Проверка прав доступа
    if current_user.role == UserRole.DENTIST:
        from app.models.visit import Visit
        visit = session.get(Visit, work.visit_id)
        if not visit or visit.doctor_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет прав для завершения этой работы"
            )
    
    work.status = WorkStatus.COMPLETED
    session.add(work)
    session.commit()
    session.refresh(work)
    
    return work

@router.delete("/{work_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_work(
    work_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Удалить работу/наряд"""
    work = session.get(Work, work_id)
    if not work:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Работа не найдена"
        )
    
    # Только администратор
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только администратор может удалять работы"
        )
    
    session.delete(work)
    session.commit()