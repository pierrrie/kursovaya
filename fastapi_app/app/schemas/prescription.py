from pydantic import BaseModel
from typing import Optional
from datetime import date

class PrescriptionBase(BaseModel):
    patient_id: int
    visit_id: Optional[int] = None
    medication: str
    dosage: Optional[str] = None
    instructions: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class PrescriptionCreate(BaseModel):
    medication: str
    dosage: Optional[str] = None
    instructions: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class PrescriptionUpdate(BaseModel):
    medication: Optional[str] = None
    dosage: Optional[str] = None
    instructions: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class PrescriptionResponse(PrescriptionBase):
    id: int

    class Config:
        from_attributes = True