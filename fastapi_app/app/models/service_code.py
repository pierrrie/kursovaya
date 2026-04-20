# app/models/service_code.py
from sqlmodel import SQLModel, Field
from typing import Optional

class ServiceCode(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True)     # код МКБ-С-3
    name: str                         # название услуги
    description: Optional[str] = None
