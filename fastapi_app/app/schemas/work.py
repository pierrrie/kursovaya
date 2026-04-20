from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.work import WorkStatus

class WorkBase(BaseModel):
    visit_id: int
    service_code_id: Optional[int] = None
    description: Optional[str] = None
    duration_minutes: Optional[int] = None
    materials: Optional[str] = None
    cost: Optional[float] = None
    tooth_numbers: Optional[str] = None

class WorkCreate(BaseModel):
    service_code_id: Optional[int] = None
    description: str
    duration_minutes: Optional[int] = None
    materials: Optional[str] = None
    cost: Optional[float] = None
    tooth_numbers: Optional[str] = None

class WorkUpdate(BaseModel):
    description: Optional[str] = None
    duration_minutes: Optional[int] = None
    materials: Optional[str] = None
    cost: Optional[float] = None
    tooth_numbers: Optional[str] = None
    status: Optional[WorkStatus] = None

class WorkResponse(WorkBase):
    id: int
    status: WorkStatus
    work_order_number: Optional[str] = None
    work_date: datetime

    class Config:
        from_attributes = True