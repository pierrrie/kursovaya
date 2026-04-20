from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class ReferralType(str, Enum):
    RESEARCH = "research"  # На исследование
    CONSULTATION = "consultation"  # На консультацию

class ReferralStatus(str, Enum):
    CREATED = "created"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class Referral(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patient.id")
    doctor_id: int = Field(foreign_key="user.id")
    visit_id: Optional[int] = Field(default=None, foreign_key="visit.id")
    referral_type: ReferralType
    destination: str  # Куда направление (например, "УЗИ кабинета", "Хирург")
    reason: str  # Причина направления
    date: datetime = Field(default_factory=datetime.now)
    status: ReferralStatus = Field(default=ReferralStatus.CREATED)
    result: Optional[str] = None  # Результат выполнения направления
    notes: Optional[str] = None