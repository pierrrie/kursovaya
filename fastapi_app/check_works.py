from app.db.database import engine
from app.models.work import Work
from sqlmodel import Session

with Session(engine) as session:
    works = session.query(Work).all()
    print(f'Found {len(works)} works in database')
    for w in works[:5]:
        print(f'Work {w.id}: visit_id={w.visit_id}, description={w.description[:50]}...')