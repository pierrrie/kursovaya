# seed.py (в корне проекта)
import sys
import os

# Добавляем корень проекта в путь Python
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

try:
    from faker import Faker
    HAS_FAKER = True
except ImportError:
    print("❌ Faker не установлен. Установите: pip install faker")
    HAS_FAKER = False
    sys.exit(1)

from sqlmodel import Session
from datetime import datetime
import random

from app.db.database import engine
from app.models.user import User, UserRole
from app.models.patient import Patient
from app.models.appointment import Appointment, AppointmentStatus
from app.models.visit import Visit
from app.models.tooth import Tooth
from app.models.prescription import Prescription
from app.models.research import Research
from app.models.work import Work, WorkStatus
from app.models.referral import Referral, ReferralType, ReferralStatus
from app.auth.security import get_password_hash

fake = Faker('ru_RU')  # Русские данные

def create_test_users(session):
    """Создать тестовых пользователей"""
    print("👥 Создание пользователей...")
    
    users = [
        # Администраторы
        User(
            username="admin",
            password_hash=get_password_hash("admin123"),
            role=UserRole.ADMIN,
            is_active=True
        ),
        # Менеджеры
        User(
            username="manager",
            password_hash=get_password_hash("manager123"),
            role=UserRole.MANAGER,
            is_active=True
        ),
        # Стоматологи
        User(
            username="dentist1",
            password_hash=get_password_hash("dentist123"),
            role=UserRole.DENTIST,
            is_active=True
        ),
        User(
            username="dentist2",
            password_hash=get_password_hash("dentist123"),
            role=UserRole.DENTIST,
            is_active=True
        ),
    ]
    
    for user in users:
        session.add(user)
    session.commit()
    print(f"✅ Создано {len(users)} пользователей")
    return users

def create_test_patients(session, count=20):
    """Создать тестовых пациентов"""
    print(f"👤 Создание {count} пациентов...")
    
    patients = []
    for i in range(count):
        patient = Patient(
            full_name=fake.name(),
            birth_date=fake.date_of_birth(minimum_age=18, maximum_age=80),
            phone=fake.phone_number(),
            address=fake.address(),
            allergies="Аллергия на пенициллин" if random.random() > 0.7 else None,
            note=fake.text(max_nb_chars=100) if random.random() > 0.5 else None
        )
        patients.append(patient)
        session.add(patient)
    
    session.commit()
    print(f"✅ Создано {len(patients)} пациентов")
    return patients

def create_test_appointments(session, patients, dentists, count=30):
    """Создать тестовые записи на прием"""
    print(f"📅 Создание {count} записей на прием...")
    
    statuses = [AppointmentStatus.ACTIVE, AppointmentStatus.CANCELLED, AppointmentStatus.COMPLETED]
    
    appointments = []
    for i in range(count):
        patient = random.choice(patients)
        dentist = random.choice([u for u in dentists if u.role == UserRole.DENTIST])
        
        # Дата от вчера до +30 дней
        date = fake.date_between(start_date='-1d', end_date='+30d')
        
        # Время приема
        hour = random.randint(9, 17)
        minute = random.choice([0, 15, 30, 45])
        time_str = f"{hour:02d}:{minute:02d}:00"
        
        appointment = Appointment(
            patient_id=patient.id,
            doctor_id=dentist.id,
            date=date,
            time=datetime.strptime(time_str, "%H:%M:%S").time(),
            status=random.choice(statuses),
            comment=fake.text(max_nb_chars=50) if random.random() > 0.5 else None
        )
        appointments.append(appointment)
        session.add(appointment)
    
    session.commit()
    print(f"✅ Создано {len(appointments)} записей на прием")
    return appointments

def create_test_visits(session, patients, dentists, count=20):
    """Создать тестовые визиты"""
    print(f"🏥 Создание {count} визитов...")
    
    visits = []
    for i in range(count):
        patient = random.choice(patients)
        dentist = random.choice([u for u in dentists if u.role == UserRole.DENTIST])
        
        # Визит в прошлом (от -90 до -1 дней)
        visit_date = fake.date_time_between(start_date='-90d', end_date='-1d')
        
        visit = Visit(
            patient_id=patient.id,
            doctor_id=dentist.id,
            datetime=visit_date,
            complaints=fake.text(max_nb_chars=100) if random.random() > 0.3 else None,
            anamnesis=fake.text(max_nb_chars=200) if random.random() > 0.4 else None,
            diagnosis=fake.text(max_nb_chars=80) if random.random() > 0.3 else None,
            exam_results=fake.text(max_nb_chars=150) if random.random() > 0.5 else None,
            notes=fake.text(max_nb_chars=120) if random.random() > 0.6 else None
        )
        visits.append(visit)
        session.add(visit)
    
    session.commit()
    print(f"✅ Создано {len(visits)} визитов")
    return visits

def create_test_teeth(session, patients):
    """Создать зубные формулы для пациентов"""
    print("🦷 Создание зубных формул...")
    
    teeth_statuses = ["здоров", "кариес", "пломба", "коронка", "отсутствует", "имплант"]
    
    teeth_count = 0
    for patient in random.sample(patients, min(10, len(patients))):
        # У каждого пациента 20-32 зуба
        for tooth_num in range(1, random.randint(20, 33)):
            tooth = Tooth(
                patient_id=patient.id,
                number=tooth_num,
                status=random.choice(teeth_statuses),
                notes=fake.text(max_nb_chars=50) if random.random() > 0.7 else None
            )
            session.add(tooth)
            teeth_count += 1
    
    session.commit()
    print(f"✅ Создано {teeth_count} записей о зубах")
    return teeth_count

def create_test_prescriptions(session, patients, visits, count=15):
    """Создать тестовые назначения"""
    print(f"💊 Создание {count} назначений...")
    
    medications = ["Амоксиклав", "Нимесил", "Кетанов", "Ибупрофен", "Парацетамол"]
    
    prescriptions = []
    for i in range(count):
        patient = random.choice(patients)
        visit = random.choice(visits) if visits and random.random() > 0.3 else None
        
        prescription = Prescription(
            patient_id=patient.id,
            visit_id=visit.id if visit else None,
            medication=random.choice(medications),
            dosage=f"{random.randint(1, 3)} таблетки {random.randint(1, 3)} раза в день",
            instructions=fake.text(max_nb_chars=80),
            start_date=fake.date_between(start_date='-30d', end_date='today'),
            end_date=fake.date_between(start_date='today', end_date='+14d')
        )
        prescriptions.append(prescription)
        session.add(prescription)
    
    session.commit()
    print(f"✅ Создано {len(prescriptions)} назначений")
    return prescriptions

def create_test_researches(session, patients, visits, count=10):
    """Создать тестовые исследования"""
    print(f"🔬 Создание {count} исследований...")
    
    research_types = ["Рентген", "КТ", "Ортопантомограмма", "Прицельный снимок"]
    
    researches = []
    for i in range(count):
        patient = random.choice(patients)
        visit = random.choice(visits) if visits and random.random() > 0.4 else None
        
        research = Research(
            patient_id=patient.id,
            visit_id=visit.id if visit else None,
            datetime=fake.date_time_between(start_date='-60d', end_date='today'),
            type=random.choice(research_types),
            result=fake.text(max_nb_chars=200) if random.random() > 0.3 else None
        )
        researches.append(research)
        session.add(research)
    
    session.commit()
    print(f"✅ Создано {len(researches)} исследований")
    return researches

def create_test_works(session, visits, count=15):
    """Создать тестовые работы/наряды"""
    print(f"🛠️ Создание {count} работ...")
    
    work_descriptions = ["Лечение кариеса", "Пломбирование", "Профессиональная гигиена",
                        "Удаление зуба", "Лечение каналов"]
    
    works = []
    for i in range(count):
        visit = random.choice(visits)
        
        work = Work(
            visit_id=visit.id,
            description=random.choice(work_descriptions),
            duration_minutes=random.choice([30, 45, 60, 90, 120]),
            materials=fake.text(max_nb_chars=60) if random.random() > 0.5 else None,
            cost=random.randint(1000, 20000),
            status=random.choice(list(WorkStatus)),
            work_order_number=f"WO-{fake.date_this_year().strftime('%Y%m%d')}-{i:04d}",
            tooth_numbers=", ".join(map(str, random.sample(range(1, 33), random.randint(1, 3)))) if random.random() > 0.4 else None,
            work_date=fake.date_time_between(start_date='-30d', end_date='today')
        )
        works.append(work)
        session.add(work)
    
    session.commit()
    print(f"✅ Создано {len(works)} работ")
    return works

def create_test_referrals(session, patients, dentists, visits, count=10):
    """Создать тестовые направления"""
    print(f"🏥 Создание {count} направлений...")
    
    destinations = ["Рентген кабинет", "Хирург", "Ортодонт", "Ортопед"]
    
    referrals = []
    for i in range(count):
        patient = random.choice(patients)
        dentist = random.choice([u for u in dentists if u.role == UserRole.DENTIST])
        visit = random.choice(visits) if visits and random.random() > 0.5 else None
        
        referral = Referral(
            patient_id=patient.id,
            doctor_id=dentist.id,
            visit_id=visit.id if visit else None,
            referral_type=random.choice(list(ReferralType)),
            destination=random.choice(destinations),
            reason=fake.text(max_nb_chars=100),
            date=fake.date_time_between(start_date='-90d', end_date='today'),
            status=random.choice(list(ReferralStatus)),
            result=fake.text(max_nb_chars=150) if random.random() > 0.4 else None,
            notes=fake.text(max_nb_chars=80) if random.random() > 0.6 else None
        )
        referrals.append(referral)
        session.add(referral)
    
    session.commit()
    print(f"✅ Создано {len(referrals)} направлений")
    return referrals

def main():
    """Основная функция заполнения БД"""
    print("=" * 60)
    print("🌱 ЗАПОЛНЕНИЕ БАЗЫ ДАННЫХ ТЕСТОВЫМИ ДАННЫМИ")
    print("=" * 60)
    
    try:
        with Session(engine) as session:
            # 1. Пользователи
            users = create_test_users(session)
            dentists = [u for u in users if u.role == UserRole.DENTIST]
            
            # 2. Пациенты
            patients = create_test_patients(session, count=20)
            
            # 3. Записи на прием
            appointments = create_test_appointments(session, patients, users, count=30)
            
            # 4. Визиты
            visits = create_test_visits(session, patients, users, count=20)
            
            # 5. Зубы
            teeth_count = create_test_teeth(session, patients)
            
            # 6. Назначения
            prescriptions = create_test_prescriptions(session, patients, visits, count=15)
            
            # 7. Исследования
            researches = create_test_researches(session, patients, visits, count=10)
            
            # 8. Работы
            works = create_test_works(session, visits, count=15)
            
            # 9. Направления
            referrals = create_test_referrals(session, patients, users, visits, count=10)
            
            print("=" * 60)
            print("📊 ИТОГИ:")
            print(f"   👥 Пользователи: {len(users)}")
            print(f"   👤 Пациенты: {len(patients)}")
            print(f"   📅 Записи: {len(appointments)}")
            print(f"   🏥 Визиты: {len(visits)}")
            print(f"   🦷 Зубы: {teeth_count}")
            print(f"   💊 Назначения: {len(prescriptions)}")
            print(f"   🔬 Исследования: {len(researches)}")
            print(f"   🛠️ Работы: {len(works)}")
            print(f"   🏥 Направления: {len(referrals)}")
            print("=" * 60)
            print("✅ База данных успешно заполнена!")
            print("=" * 60)
            
            # Вывод тестовых учетных данных
            print("\n🔑 ТЕСТОВЫЕ УЧЕТНЫЕ ДАННЫЕ:")
            print("-" * 40)
            for user in users:
                password = f"{user.username}123"
                print(f"👤 {user.username:<10} | Пароль: {password:<12} | Роль: {user.role}")
            print("-" * 40)
            
            print("\n👤 ПЕРВЫЕ 5 ПАЦИЕНТОВ:")
            print("-" * 50)
            for i, patient in enumerate(patients[:5], 1):
                print(f"{i}. {patient.full_name:<35} | Тел: {patient.phone}")
            print("-" * 50)
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if not HAS_FAKER:
        print("Установите Faker: pip install faker")
        sys.exit(1)
    main()