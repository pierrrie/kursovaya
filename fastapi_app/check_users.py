from app.db.database import engine
from app.models.user import User
from sqlmodel import Session

with Session(engine) as session:
    users = session.query(User).all()
    print(f'Found {len(users)} users in database')
    for u in users:
        print(f'User {u.id}: username={u.username}, role={u.role}, active={u.is_active}')