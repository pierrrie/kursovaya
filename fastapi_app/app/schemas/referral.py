# app/schemas/referral.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.referral import ReferralType, ReferralStatus

class ReferralBase(BaseModel):
    patient_id: int
    referral_type: ReferralType
    destination: str
    reason: str
    visit_id: Optional[int] = None
    notes: Optional[str] = None  # Добавляем notes в базовый класс

class ReferralCreate(BaseModel):
    patient_id: int  # Обязательное поле
    referral_type: ReferralType
    destination: str
    reason: str
    visit_id: Optional[int] = None
    notes: Optional[str] = None

class ReferralUpdate(BaseModel):
    status: Optional[ReferralStatus] = None
    result: Optional[str] = None
    notes: Optional[str] = None

class ReferralResponse(ReferralBase):
    id: int
    doctor_id: int
    date: datetime
    status: ReferralStatus
    result: Optional[str] = None
    
    class Config:
        from_attributes = True  # Используем from_attributes вместо orm_mode для Pydantic v2