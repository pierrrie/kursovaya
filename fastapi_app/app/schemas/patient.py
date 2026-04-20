# app/schemas/patient.py
from pydantic import BaseModel
from typing import Optional
from datetime import date


class PatientBase(BaseModel):
    full_name: str
    birth_date: Optional[date] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    allergies: Optional[str] = None  # сигнальная инфа
    note: Optional[str] = None


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    full_name: Optional[str] = None
    birth_date: Optional[date] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    allergies: Optional[str] = None
    note: Optional[str] = None


class PatientResponse(PatientBase):
    id: int

    class Config:
        orm_mode = True
