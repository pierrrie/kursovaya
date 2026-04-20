from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class WorkStatus(str, Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class Work(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    visit_id: int = Field(foreign_key="visit.id")
    service_code_id: Optional[int] = Field(default=None, foreign_key="servicecode.id")
    description: Optional[str] = None
    duration_minutes: Optional[int] = None
    materials: Optional[str] = None
    cost: Optional[float] = None
    status: WorkStatus = Field(default=WorkStatus.PLANNED)
    work_order_number: Optional[str] = None  # Номер наряда
    tooth_numbers: Optional[str] = None  # Номера зубов через запятую "11,12,13"
    work_date: datetime = Field(default_factory=datetime.now)