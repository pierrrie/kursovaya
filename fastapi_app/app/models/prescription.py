# app/models/prescription.py
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import date

class Prescription(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patient.id")
    visit_id: Optional[int] = Field(default=None, foreign_key="visit.id")
    medication: str
    dosage: Optional[str] = None
    instructions: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
