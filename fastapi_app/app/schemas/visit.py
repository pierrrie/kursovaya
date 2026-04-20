# app/schemas/visit.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class VisitBase(BaseModel):
    patient_id: int
    doctor_id: Optional[int] = None  # Делаем опциональным
    datetime: datetime
    complaints: Optional[str] = None
    anamnesis: Optional[str] = None
    diagnosis: Optional[str] = None
    exam_results: Optional[str] = None
    notes: Optional[str] = None

class VisitCreate(BaseModel):
    patient_id: int
    doctor_id: Optional[int] = None  # Опционально
    datetime: datetime
    complaints: Optional[str] = None
    anamnesis: Optional[str] = None
    diagnosis: Optional[str] = None
    exam_results: Optional[str] = None
    notes: Optional[str] = None

class VisitUpdate(BaseModel):
    datetime: Optional[datetime] = None
    complaints: Optional[str] = None
    anamnesis: Optional[str] = None
    diagnosis: Optional[str] = None
    exam_results: Optional[str] = None
    notes: Optional[str] = None

class VisitResponse(VisitBase):
    id: int

    class Config:
        from_attributes = True  # Для Pydantic v2