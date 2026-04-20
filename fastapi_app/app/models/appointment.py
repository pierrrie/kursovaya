# app/models/appointment.py
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import date, time
from enum import Enum

class AppointmentStatus(str, Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

class Appointment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patient.id")
    doctor_id: int = Field(foreign_key="user.id")
    date: date
    time: time
    status: AppointmentStatus = Field(default=AppointmentStatus.ACTIVE)
    comment: Optional[str] = None
