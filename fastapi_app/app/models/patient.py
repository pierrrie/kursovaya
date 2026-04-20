from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import date

class Patient(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    full_name: str
    birth_date: Optional[date] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    allergies: Optional[str] = None
    note: Optional[str] = None
    
    # Связи
    # visits: List["Visit"] = Relationship(back_populates="patient")
    # appointments: List["Appointment"] = Relationship(back_populates="patient")
    # teeth: List["Tooth"] = Relationship(back_populates="patient")
    # prescriptions: List["Prescription"] = Relationship(back_populates="patient")
    # researches: List["Research"] = Relationship(back_populates="patient")
    # referrals: List["Referral"] = Relationship(back_populates="patient")