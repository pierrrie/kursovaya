# app/models/tooth.py
from sqlmodel import SQLModel, Field
from typing import Optional

class Tooth(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patient.id")
    number: int                     # номер зуба по схеме
    status: Optional[str] = None    # кариес, пломба, удалён и т.п.
    notes: Optional[str] = None
