from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ResearchBase(BaseModel):
    patient_id: int
    visit_id: Optional[int] = None
    datetime: datetime
    type: str
    result: Optional[str] = None

class ResearchCreate(BaseModel):
    datetime: datetime
    type: str
    result: Optional[str] = None

class ResearchUpdate(BaseModel):
    datetime: Optional[datetime] = None
    type: Optional[str] = None
    result: Optional[str] = None

class ResearchResponse(ResearchBase):
    id: int

    class Config:
        from_attributes = True  # Было orm_mode=True