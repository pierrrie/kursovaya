from pydantic import BaseModel, validator
from typing import Optional

class ToothBase(BaseModel):
    patient_id: int
    number: int
    status: Optional[str] = None
    notes: Optional[str] = None

class ToothCreate(BaseModel):
    number: int
    status: Optional[str] = None
    notes: Optional[str] = None

class ToothUpdate(BaseModel):
    number: Optional[int] = None
    status: Optional[str] = None
    notes: Optional[str] = None

class ToothResponse(ToothBase):
    id: int

    class Config:
        from_attributes = True