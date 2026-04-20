# app/db/database.py
from sqlmodel import SQLModel, create_engine
import os
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "root")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "stomatologiya")

DATABASE_URL = "sqlite:///stomatologiya.db"

# echo=True – чтобы видеть SQL в консоли, можно потом убрать
engine = create_engine(DATABASE_URL, echo=True)


def init_db() -> None:
    """
    Создание таблиц по всем SQLModel-моделям.
    """
    from app.models.user import User
    from app.models.patient import Patient
    from app.models.appointment import Appointment
    from app.models.visit import Visit
    from app.models.research import Research
    from app.models.prescription import Prescription
    from app.models.service_code import ServiceCode
    from app.models.tooth import Tooth
    from app.models.work import Work  # Добавляем
    from app.models.referral import Referral  # Добавляем
    
    SQLModel.metadata.create_all(engine)


def close_db() -> None:
    """
    Освобождаем ресурсы подключения.
    Вызывается в событии shutdown FastAPI.
    """
    engine.dispose()
