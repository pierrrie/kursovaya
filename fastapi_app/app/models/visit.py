# app/models/visit.py
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class Visit(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patient.id")
    doctor_id: int = Field(foreign_key="user.id")
    datetime: datetime
    complaints: Optional[str] = None      # жалобы
    anamnesis: Optional[str] = None       # анамнез
    diagnosis: Optional[str] = None       # диагноз
    exam_results: Optional[str] = None    # результаты осмотра
    notes: Optional[str] = None           # прочее
