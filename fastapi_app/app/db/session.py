# app/db/session.py
from sqlmodel import Session
from app.db.database import engine


def get_session():
    """
    Зависимость FastAPI.
    Даёт sync Session (sqlmodel.Session) в обработчики запросов.
    """
    with Session(engine) as session:
        yield session
