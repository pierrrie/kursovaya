# app/schemas/appointment.py
from pydantic import BaseModel
from typing import Optional
from datetime import date, time
from app.models.appointment import AppointmentStatus


class AppointmentBase(BaseModel):
    patient_id: int
    doctor_id: int
    date: date
    time: time
    status: AppointmentStatus = AppointmentStatus.ACTIVE
    comment: Optional[str] = None


class AppointmentCreate(BaseModel):
    patient_id: int
    doctor_id: int
    date: date
    time: time
    comment: Optional[str] = None


class AppointmentUpdate(BaseModel):
    date: Optional[date] = None
    time: Optional[time] = None
    status: Optional[AppointmentStatus] = None
    comment: Optional[str] = None


class AppointmentResponse(AppointmentBase):
    id: int

    class Config:
        orm_mode = True
