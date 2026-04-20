# app/schemas/service_code.py
from pydantic import BaseModel
from typing import Optional


class ServiceCodeBase(BaseModel):
    code: str
    name: str
    description: Optional[str] = None


class ServiceCodeCreate(ServiceCodeBase):
    pass


class ServiceCodeUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None


class ServiceCodeResponse(ServiceCodeBase):
    id: int

    class Config:
        orm_mode = True
