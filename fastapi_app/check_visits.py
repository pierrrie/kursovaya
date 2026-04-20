from app.db.database import engine
from app.models.visit import Visit
from app.models.user import User
from sqlmodel import Session

with Session(engine) as session:
    visits = session.query(Visit).all()
    print(f'Found {len(visits)} visits in database')
    for v in visits:
        doctor = session.get(User, v.doctor_id)
        print(f'Visit {v.id}: doctor_id={v.doctor_id}, doctor_username={doctor.username if doctor else "None"}, patient_id={v.patient_id}, datetime={v.datetime}')