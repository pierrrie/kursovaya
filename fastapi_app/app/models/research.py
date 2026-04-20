# app/models/research.py
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class Research(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patient.id")
    visit_id: Optional[int] = Field(default=None, foreign_key="visit.id")
    datetime: datetime
    type: str                   # УЗИ, рентген и т.п.
    result: Optional[str] = None
