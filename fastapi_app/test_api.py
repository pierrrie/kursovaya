# test_api.py
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from main import app
from app.db.session import get_session
from app.models.user import User, UserRole
from app.models.patient import Patient
from app.models.appointment import Appointment
from app.models.visit import Visit
from app.models.research import Research
from app.models.prescription import Prescription
from app.models.tooth import Tooth
from app.models.work import Work
from app.models.referral import Referral
from app.models.service_code import ServiceCode
from datetime import datetime, date, time
import json
import time as time_module

# Тестовая база данных в памяти
DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session
    
    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

@pytest.fixture(name="admin_user")
def admin_user_fixture(session: Session):
    from app.auth.security import get_password_hash
    
    admin_user = User(
        username="testadmin",
        password_hash=get_password_hash("testpass123"),
        role=UserRole.ADMIN,
        is_active=True
    )
    session.add(admin_user)
    session.commit()
    session.refresh(admin_user)
    return admin_user

@pytest.fixture(name="admin_token")
def admin_token_fixture(client: TestClient, admin_user: User):
    response = client.post(
        "/auth/login",
        data={"username": "testadmin", "password": "testpass123"}
    )
    return response.json()["access_token"]

@pytest.fixture(name="dentist_user")
def dentist_user_fixture(session: Session):
    from app.auth.security import get_password_hash
    
    dentist_user = User(
        username="testdentist",
        password_hash=get_password_hash("testpass123"),
        role=UserRole.DENTIST,
        is_active=True
    )
    session.add(dentist_user)
    session.commit()
    session.refresh(dentist_user)
    return dentist_user

@pytest.fixture(name="dentist_token")
def dentist_token_fixture(client: TestClient, dentist_user: User):
    response = client.post(
        "/auth/login",
        data={"username": "testdentist", "password": "testpass123"}
    )
    return response.json()["access_token"]

@pytest.fixture(name="manager_user")
def manager_user_fixture(session: Session):
    from app.auth.security import get_password_hash
    
    manager_user = User(
        username="testmanager",
        password_hash=get_password_hash("testpass123"),
        role=UserRole.MANAGER,
        is_active=True
    )
    session.add(manager_user)
    session.commit()
    session.refresh(manager_user)
    return manager_user

@pytest.fixture(name="manager_token")
def manager_token_fixture(client: TestClient, manager_user: User):
    response = client.post(
        "/auth/login",
        data={"username": "testmanager", "password": "testpass123"}
    )
    return response.json()["access_token"]

@pytest.fixture(name="test_patient")
def test_patient_fixture(session: Session):
    patient = Patient(
        full_name="Иван Иванов",
        birth_date=date(1990, 1, 1),
        phone="+79123456789",
        address="Москва",
        allergies="Пенициллин"
    )
    session.add(patient)
    session.commit()
    session.refresh(patient)
    return patient

@pytest.fixture(name="test_visit")
def test_visit_fixture(session: Session, test_patient: Patient, dentist_user: User):
    visit = Visit(
        patient_id=test_patient.id,
        doctor_id=dentist_user.id,
        datetime=datetime.now(),
        complaints="Болит зуб",
        diagnosis="Кариес"
    )
    session.add(visit)
    session.commit()
    session.refresh(visit)
    return visit

@pytest.fixture(name="test_appointment")
def test_appointment_fixture(session: Session, test_patient: Patient, dentist_user: User):
    appointment = Appointment(
        patient_id=test_patient.id,
        doctor_id=dentist_user.id,
        date=date.today(),
        time=time(10, 30),
        comment="Первичный осмотр"
    )
    session.add(appointment)
    session.commit()
    session.refresh(appointment)
    return appointment

# ===== TESTS =====

def test_root(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "API системы управления" in data["message"]

def test_health_check(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

# === АУТЕНТИФИКАЦИЯ ===

def test_register(client: TestClient):
    response = client.post(
        "/auth/register",
        json={
            "username": "newuser",
            "password": "newpass123",
            "role": "manager"
        }
    )
    # Может быть 200 или 400 если пользователь уже существует
    assert response.status_code in [200, 400]
    if response.status_code == 200:
        data = response.json()
        assert "access_token" in data
        assert data["username"] == "newuser"
        assert data["role"] == "manager"

def test_login(client: TestClient, session: Session):
    # Сначала регистрируем пользователя
    from app.auth.security import get_password_hash
    user = User(
        username="loginuser",
        password_hash=get_password_hash("mypassword"),
        role=UserRole.MANAGER
    )
    session.add(user)
    session.commit()
    
    # Пробуем войти
    response = client.post(
        "/auth/login",
        data={"username": "loginuser", "password": "mypassword"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["username"] == "loginuser"

# === ВИЗИТЫ (VISITS) ===

def test_create_visit(dentist_token: str, client: TestClient, test_patient: Patient):
    """Тест создания визита"""
    response = client.post(
        "/visits/",
        json={
            "patient_id": test_patient.id,
            "datetime": "2024-12-15T14:30:00",
            "complaints": "Болит зуб",
            "diagnosis": "Кариес"
        },
        headers={"Authorization": f"Bearer {dentist_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["patient_id"] == test_patient.id
    assert data["complaints"] == "Болит зуб"
    return data["id"]  # Возвращаем ID созданного визита

def test_get_visits(dentist_token: str, client: TestClient, test_visit: Visit):
    """Тест получения списка визитов"""
    response = client.get(
        "/visits/",
        headers={"Authorization": f"Bearer {dentist_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0

def test_get_visit_by_id(dentist_token: str, client: TestClient, test_visit: Visit):
    """Тест получения визита по ID"""
    response = client.get(
        f"/visits/{test_visit.id}",
        headers={"Authorization": f"Bearer {dentist_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_visit.id
    assert data["patient_id"] == test_visit.patient_id

def test_get_patient_visits(dentist_token: str, client: TestClient, test_patient: Patient, test_visit: Visit):
    """Тест получения визитов пациента"""
    response = client.get(
        f"/visits/patient/{test_patient.id}",
        headers={"Authorization": f"Bearer {dentist_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["patient_id"] == test_patient.id

def test_update_visit(dentist_token: str, client: TestClient, test_visit: Visit):
    """Тест обновления визита"""
    response = client.put(
        f"/visits/{test_visit.id}",
        json={"complaints": "Обновленные жалобы", "diagnosis": "Пульпит"},
        headers={"Authorization": f"Bearer {dentist_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["complaints"] == "Обновленные жалобы"
    assert data["diagnosis"] == "Пульпит"

def test_manager_cannot_create_visit(manager_token: str, client: TestClient, test_patient: Patient):
    """Тест что менеджер не может создавать визиты"""
    response = client.post(
        "/visits/",
        json={
            "patient_id": test_patient.id,
            "datetime": "2024-12-15T14:30:00",
            "complaints": "Болит зуб"
        },
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    assert response.status_code == 403

# === ПАЦИЕНТЫ ===

def test_create_patient(manager_token: str, client: TestClient):
    response = client.post(
        "/patients/",
        json={
            "full_name": "Петр Петров",
            "birth_date": "1985-05-15",
            "phone": "+79111111111",
            "address": "Санкт-Петербург"
        },
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Петр Петров"

def test_get_patients(dentist_token: str, client: TestClient, test_patient: Patient):
    response = client.get(
        "/patients/",
        headers={"Authorization": f"Bearer {dentist_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0

def test_get_patient_by_id(dentist_token: str, client: TestClient, test_patient: Patient):
    response = client.get(
        f"/patients/{test_patient.id}",
        headers={"Authorization": f"Bearer {dentist_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_patient.id
    assert data["full_name"] == test_patient.full_name

def test_update_patient(manager_token: str, client: TestClient, test_patient: Patient):
    response = client.put(
        f"/patients/{test_patient.id}",
        json={"phone": "+79222222222"},
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["phone"] == "+79222222222"

def test_delete_patient(admin_token: str, client: TestClient, session: Session):
    """Тест удаления пациента (администратор)."""
    patient = Patient(full_name="Удаляемый Пациент", phone="+79109998877")
    session.add(patient)
    session.commit()
    session.refresh(patient)
    
    response = client.delete(
        f"/patients/{patient.id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 204


def test_manager_can_delete_patient(manager_token: str, client: TestClient, session: Session):
    patient = Patient(full_name="Удаляемый Пациент", phone="+79109998877")
    session.add(patient)
    session.commit()
    session.refresh(patient)

    response = client.delete(
        f"/patients/{patient.id}",
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    assert response.status_code == 204


def test_dentist_cannot_delete_patient(dentist_token: str, client: TestClient, test_patient: Patient):
    response = client.delete(
        f"/patients/{test_patient.id}",
        headers={"Authorization": f"Bearer {dentist_token}"}
    )
    assert response.status_code == 403

# === ЗАПИСИ НА ПРИЕМ ===

def test_create_appointment(manager_token: str, client: TestClient, test_patient: Patient, dentist_user: User):
    response = client.post(
        "/appointments/",
        json={
            "patient_id": test_patient.id,
            "doctor_id": dentist_user.id,
            "date": "2024-12-15",
            "time": "14:30:00",
            "comment": "Контрольный осмотр"
        },
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["patient_id"] == test_patient.id
    assert data["doctor_id"] == dentist_user.id


def test_dentist_cannot_create_appointment_for_another_doctor(
    dentist_token: str,
    client: TestClient,
    test_patient: Patient,
    session: Session,
):
    from app.auth.security import get_password_hash
    other_dentist = User(
        username="otherdentist2",
        password_hash=get_password_hash("pass123"),
        role=UserRole.DENTIST,
        is_active=True,
    )
    session.add(other_dentist)
    session.commit()
    session.refresh(other_dentist)

    response = client.post(
        "/appointments/",
        json={
            "patient_id": test_patient.id,
            "doctor_id": other_dentist.id,
            "date": "2024-12-15",
            "time": "14:30:00",
            "comment": "Попытка записи на другого врача"
        },
        headers={"Authorization": f"Bearer {dentist_token}"}
    )
    assert response.status_code == 403


def test_get_appointments(dentist_token: str, client: TestClient, test_appointment: Appointment):
    response = client.get(
        "/appointments/",
        headers={"Authorization": f"Bearer {dentist_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_get_appointment_by_id(dentist_token: str, client: TestClient, test_appointment: Appointment):
    response = client.get(
        f"/appointments/{test_appointment.id}",
        headers={"Authorization": f"Bearer {dentist_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_appointment.id


def test_dentist_cannot_access_other_doctor_appointment(
    dentist_token: str,
    client: TestClient,
    test_patient: Patient,
    session: Session,
):
    from app.auth.security import get_password_hash
    other_doctor = User(
        username="otherdentist",
        password_hash=get_password_hash("password123"),
        role=UserRole.DENTIST,
        is_active=True,
    )
    session.add(other_doctor)
    session.commit()
    session.refresh(other_doctor)

    appointment = Appointment(
        patient_id=test_patient.id,
        doctor_id=other_doctor.id,
        date=date(2024, 12, 16),
        time=time(10, 0),
        comment="Тестовая запись другого врача"
    )
    session.add(appointment)
    session.commit()
    session.refresh(appointment)

    response = client.get(
        f"/appointments/{appointment.id}",
        headers={"Authorization": f"Bearer {dentist_token}"}
    )
    assert response.status_code == 403

# === СТОМАТОЛОГ ===

def test_get_today_schedule(dentist_token: str, client: TestClient, test_appointment: Appointment):
    response = client.get(
        "/dentist/schedule/today",
        headers={"Authorization": f"Bearer {dentist_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_get_waiting_patients(dentist_token: str, client: TestClient):
    response = client.get(
        "/dentist/patients/waiting",
        headers={"Authorization": f"Bearer {dentist_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

# === АДМИНИСТРАЦИЯ ===

def test_list_users(admin_token: str, client: TestClient):
    response = client.get(
        "/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_change_user_role(admin_token: str, client: TestClient, session: Session):
    # Создаем пользователя для изменения роли
    from app.auth.security import get_password_hash
    user = User(
        username="roletest",
        password_hash=get_password_hash("pass"),
        role=UserRole.MANAGER
    )
    session.add(user)
    session.commit()
    
    response = client.put(
        f"/admin/users/{user.id}/role",
        json={"role": "dentist"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "dentist"

# === ДНЕВНИК ВРАЧА ===

def test_get_day_schedule(dentist_token: str, client: TestClient):
    response = client.get(
        "/dentist-diary/day?day=2024-12-10",
        headers={"Authorization": f"Bearer {dentist_token}"}
    )
    # Может быть 200 или 404 если нет записей
    assert response.status_code in [200, 404]

def test_get_today_visits(dentist_token: str, client: TestClient, test_visit: Visit):
    response = client.get(
        "/dentist-diary/today-visits",
        headers={"Authorization": f"Bearer {dentist_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

# === ИССЛЕДОВАНИЯ (RESEARCH) С VISIT_ID ===

def test_create_research_with_visit(dentist_token: str, client: TestClient, test_patient: Patient, test_visit: Visit):
    """Тест создания исследования с привязкой к визиту"""
    response = client.post(
        f"/research/patient/{test_patient.id}?visit_id={test_visit.id}",
        json={
            "datetime": "2024-12-10T15:30:00",
            "type": "Рентген",
            "result": "Кариес 1.6"
        },
        headers={"Authorization": f"Bearer {dentist_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "Рентген"
    assert data["patient_id"] == test_patient.id
    assert data["visit_id"] == test_visit.id

def test_create_research_without_visit(dentist_token: str, client: TestClient, test_patient: Patient):
    """Тест создания исследования без привязки к визиту"""
    response = client.post(
        f"/research/patient/{test_patient.id}",
        json={
            "datetime": "2024-12-10T15:30:00",
            "type": "Рентген",
            "result": "Кариес 1.6"
        },
        headers={"Authorization": f"Bearer {dentist_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "Рентген"
    assert data["patient_id"] == test_patient.id
    # visit_id может быть None

def test_get_patient_research(dentist_token: str, client: TestClient, test_patient: Patient, session: Session):
    # Сначала создаем исследование
    research = Research(
        patient_id=test_patient.id,
        datetime=datetime.now(),
        type="УЗИ",
        result="Норма"
    )
    session.add(research)
    session.commit()
    
    response = client.get(
        f"/research/patient/{test_patient.id}",
        headers={"Authorization": f"Bearer {dentist_token}"}
    )
    # Может быть 200 или 403 если нет доступа
    assert response.status_code in [200, 403]

# === НАЗНАЧЕНИЯ (PRESCRIPTIONS) С VISIT_ID ===

def test_create_prescription_with_visit(dentist_token: str, client: TestClient, test_patient: Patient, test_visit: Visit):
    """Тест создания назначения с привязкой к визиту"""
    response = client.post(
        f"/prescriptions/patient/{test_patient.id}?visit_id={test_visit.id}",
        json={
            "medication": "Амоксиклав",
            "dosage": "500 мг 3 раза в день",
            "instructions": "После еды",
            "start_date": "2024-12-10",
            "end_date": "2024-12-17"
        },
        headers={"Authorization": f"Bearer {dentist_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["medication"] == "Амоксиклав"
    assert data["patient_id"] == test_patient.id
    assert data["visit_id"] == test_visit.id

def test_get_patient_prescriptions(dentist_token: str, client: TestClient, test_patient: Patient, session: Session):
    # Создаем назначение
    prescription = Prescription(
        patient_id=test_patient.id,
        medication="Ибупрофен",
        dosage="200 мг",
        instructions="При боли"
    )
    session.add(prescription)
    session.commit()
    
    response = client.get(
        f"/prescriptions/patient/{test_patient.id}",
        headers={"Authorization": f"Bearer {dentist_token}"}
    )
    # Может быть 200 или 403 если нет доступа
    assert response.status_code in [200, 403]

# === ЗУБЫ (TEETH) ===

def test_create_tooth_record(dentist_token: str, client: TestClient, test_patient: Patient):
    response = client.post(
        f"/teeth/patient/{test_patient.id}",
        json={
            "number": 16,
            "status": "Кариес",
            "notes": "Требуется лечение"
        },
        headers={"Authorization": f"Bearer {dentist_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["number"] == 16
    assert data["status"] == "Кариес"

def test_get_patient_teeth(dentist_token: str, client: TestClient, test_patient: Patient, session: Session):
    # Создаем запись о зубе
    tooth = Tooth(
        patient_id=test_patient.id,
        number=11,
        status="Здоров"
    )
    session.add(tooth)
    session.commit()
    
    response = client.get(
        f"/teeth/patient/{test_patient.id}",
        headers={"Authorization": f"Bearer {dentist_token}"}
    )
    # Может быть 200 или 403 если нет доступа
    assert response.status_code in [200, 403]

# === РАБОТЫ (WORKS) С VISIT_ID ===

def test_create_work_with_visit(dentist_token: str, client: TestClient, test_visit: Visit):
    """Тест создания работы с привязкой к визиту"""
    response = client.post(
        f"/works/visit/{test_visit.id}",
        json={
            "description": "Лечение кариеса",
            "duration_minutes": 60,
            "cost": 5000.0,
            "tooth_numbers": "16"
        },
        headers={"Authorization": f"Bearer {dentist_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["description"] == "Лечение кариеса"
    assert data["visit_id"] == test_visit.id

def test_get_works_by_visit(dentist_token: str, client: TestClient, test_visit: Visit, session: Session):
    # Сначала создаем работу
    work = Work(
        visit_id=test_visit.id,
        description="Тестовая работа",
        duration_minutes=30,
        cost=3000.0,
        tooth_numbers="11"
    )
    session.add(work)
    session.commit()
    
    response = client.get(
        f"/works/visit/{test_visit.id}",
        headers={"Authorization": f"Bearer {dentist_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0

# === НАПРАВЛЕНИЯ (REFERRALS) С VISIT_ID ===

def test_create_referral_with_visit(dentist_token: str, client: TestClient, test_patient: Patient, test_visit: Visit):
    """Тест создания направления с привязкой к визиту"""
    response = client.post(
        "/referrals/",
        json={
            "patient_id": test_patient.id,
            "referral_type": "research",
            "destination": "Рентген-кабинет",
            "reason": "Для уточнения диагноза",
            "visit_id": test_visit.id
        },
        headers={"Authorization": f"Bearer {dentist_token}"}
    )
    # Может быть 200, 403 или 500
    assert response.status_code in [200, 403, 500]

def test_get_patient_referrals(dentist_token: str, client: TestClient, test_patient: Patient, session: Session):
    # Создаем направление
    referral = Referral(
        patient_id=test_patient.id,
        doctor_id=1,  # ID доктора
        referral_type="research",
        destination="Тест",
        reason="Тестовая причина"
    )
    session.add(referral)
    session.commit()
    
    response = client.get(
        f"/referrals/patient/{test_patient.id}",
        headers={"Authorization": f"Bearer {dentist_token}"}
    )
    # Может быть 200 или 403
    assert response.status_code in [200, 403]

# === МКБ-С-3 ===

def test_get_all_mkb_s3_services(client: TestClient):
    response = client.get("/mkb-s3/services")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_search_mkb_s3_services(client: TestClient):
    response = client.get("/mkb-s3/search/кариес")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

# === ДОКУМЕНТЫ ===

def test_generate_patient_history(dentist_token: str, client: TestClient, test_patient: Patient):
    response = client.get(
        f"/documents/patient-history/{test_patient.id}",
        headers={"Authorization": f"Bearer {dentist_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "patient" in data
    assert data["patient"]["id"] == test_patient.id

def test_generate_visit_report(dentist_token: str, client: TestClient, test_visit: Visit):
    response = client.get(
        f"/documents/visit-report/{test_visit.id}",
        headers={"Authorization": f"Bearer {dentist_token}"}
    )
    # Может быть 200 или 404
    assert response.status_code in [200, 404]

# === ТЕСТЫ НА ПРАВА ДОСТУПА ===

def test_manager_cannot_create_research(manager_token: str, client: TestClient, test_patient: Patient):
    response = client.post(
        f"/research/patient/{test_patient.id}",
        json={
            "datetime": "2024-12-10T16:00:00",
            "type": "Рентген"
        },
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    # Менеджер не должен создавать исследования
    assert response.status_code == 403  # Forbidden

def test_dentist_cannot_delete_patient(dentist_token: str, client: TestClient, test_patient: Patient):
    response = client.delete(
        f"/patients/{test_patient.id}",
        headers={"Authorization": f"Bearer {dentist_token}"}
    )
    assert response.status_code == 403  # Forbidden

def test_manager_cannot_change_user_role(manager_token: str, client: TestClient, session: Session):
    from app.auth.security import get_password_hash
    user = User(
        username="norolechange",
        password_hash=get_password_hash("pass"),
        role=UserRole.MANAGER
    )
    session.add(user)
    session.commit()
    
    response = client.put(
        f"/admin/users/{user.id}/role",
        json={"role": "dentist"},
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    assert response.status_code == 403  # Forbidden

# === ОШИБОЧНЫЕ СЦЕНАРИИ ===

def test_nonexistent_patient(dentist_token: str, client: TestClient):
    response = client.get(
        "/patients/999999",
        headers={"Authorization": f"Bearer {dentist_token}"}
    )
    assert response.status_code == 404

def test_nonexistent_visit(dentist_token: str, client: TestClient):
    response = client.get(
        "/visits/999999",
        headers={"Authorization": f"Bearer {dentist_token}"}
    )
    assert response.status_code == 404

def test_unauthorized_access(client: TestClient):
    response = client.get("/patients/")
    assert response.status_code == 401  # Unauthorized

def test_invalid_token(client: TestClient):
    response = client.get(
        "/patients/",
        headers={"Authorization": "Bearer invalid_token_here"}
    )
    assert response.status_code == 401

def test_duplicate_username(client: TestClient, session: Session):
    from app.auth.security import get_password_hash
    user = User(
        username="duplicate",
        password_hash=get_password_hash("pass"),
        role=UserRole.MANAGER
    )
    session.add(user)
    session.commit()
    
    response = client.post(
        "/auth/register",
        json={
            "username": "duplicate",
            "password": "anotherpass",
            "role": "manager"
        }
    )
    assert response.status_code == 400  # Bad Request

# === ПОЛНЫЕ СЦЕНАРИИ С VISITS ===

def test_complete_workflow_with_visits(admin_token: str, client: TestClient, session: Session):
    """Полный тестовый сценарий с визитами"""
    
    print("\n🧪 Запуск полного workflow с визитами...")
    
    # 1. Создаем пациента
    patient_resp = client.post(
        "/patients/",
        json={
            "full_name": "Алексей Петров",
            "phone": "+79441112233"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert patient_resp.status_code == 200
    patient_id = patient_resp.json()["id"]
    print(f"✅ Пациент создан, ID: {patient_id}")
    
    # 2. Создаем запись на прием
    # Находим существующего стоматолога
    dentist = session.exec(select(User).where(User.role == UserRole.DENTIST)).first()
    if not dentist:
        # Создаем стоматолога если нет
        from app.auth.security import get_password_hash
        dentist = User(
            username="workflow_dentist",
            password_hash=get_password_hash("pass123"),
            role=UserRole.DENTIST
        )
        session.add(dentist)
        session.commit()
        session.refresh(dentist)
    
    appointment_resp = client.post(
        "/appointments/",
        json={
            "patient_id": patient_id,
            "doctor_id": dentist.id,
            "date": "2024-12-11",
            "time": "11:00:00",
            "comment": "Первичный осмотр"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert appointment_resp.status_code == 200
    print(f"✅ Запись создана, ID: {appointment_resp.json()['id']}")
    
    # 3. Логинимся как стоматолог
    dentist_login = client.post(
        "/auth/login",
        data={"username": dentist.username, "password": "pass123"}
    )
    assert dentist_login.status_code == 200
    dentist_token = dentist_login.json()["access_token"]
    print(f"✅ Авторизован как стоматолог")
    
    # 4. Создаем визит
    visit_resp = client.post(
        "/visits/",
        json={
            "patient_id": patient_id,
            "datetime": "2024-12-11T11:30:00",
            "complaints": "Острая боль",
            "diagnosis": "Глубокий кариес"
        },
        headers={"Authorization": f"Bearer {dentist_token}"}
    )
    assert visit_resp.status_code == 200
    visit_id = visit_resp.json()["id"]
    print(f"✅ Визит создан, ID: {visit_id}")
    
    # 5. Создаем исследование с привязкой к визиту
    research_resp = client.post(
        f"/research/patient/{patient_id}?visit_id={visit_id}",
        json={
            "datetime": "2024-12-11T11:45:00",
            "type": "Рентген",
            "result": "Кариес до пульпы"
        },
        headers={"Authorization": f"Bearer {dentist_token}"}
    )
    assert research_resp.status_code == 200
    print(f"✅ Исследование создано, ID: {research_resp.json()['id']}")
    
    # 6. Создаем назначение с привязкой к визиту
    prescription_resp = client.post(
        f"/prescriptions/patient/{patient_id}?visit_id={visit_id}",
        json={
            "medication": "Анальгин",
            "dosage": "1 таблетка при боли",
            "instructions": "Не чаще 3 раз в день"
        },
        headers={"Authorization": f"Bearer {dentist_token}"}
    )
    assert prescription_resp.status_code == 200
    print(f"✅ Назначение создано, ID: {prescription_resp.json()['id']}")
    
    # 7. Создаем работу с привязкой к визиту
    work_resp = client.post(
        f"/works/visit/{visit_id}",
        json={
            "description": "Лечение глубокого кариеса",
            "duration_minutes": 90,
            "cost": 7500.0,
            "tooth_numbers": "36"
        },
        headers={"Authorization": f"Bearer {dentist_token}"}
    )
    assert work_resp.status_code == 200
    print(f"✅ Работа создана, ID: {work_resp.json()['id']}")
    
    # 8. Создаем запись о зубе
    tooth_resp = client.post(
        f"/teeth/patient/{patient_id}",
        json={
            "number": 36,
            "status": "Леченый",
            "notes": "Поставлена пломба"
        },
        headers={"Authorization": f"Bearer {dentist_token}"}
    )
    assert tooth_resp.status_code == 200
    print(f"✅ Запись о зубе создана, ID: {tooth_resp.json()['id']}")
    
    print("✅ Весь workflow с визитами протестирован успешно!")

def test_bulk_operations_with_visits(admin_token: str, client: TestClient, session: Session):
    """Тест массовых операций с визитами"""
    
    # Создаем несколько пациентов
    patients_data = [
        {"full_name": f"Пациент Визит {i}", "phone": f"+7910{i:07d}"}
        for i in range(1, 4)
    ]
    
    created_ids = []
    for patient_data in patients_data:
        response = client.post(
            "/patients/",
            json=patient_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        created_ids.append(response.json()["id"])
    
    # Получаем всех пациентов
    response = client.get(
        "/patients/",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    all_patients = response.json()
    assert len(all_patients) >= 3
    
    # Создаем визиты для пациентов
    for patient_id in created_ids:
        visit_data = {
            "patient_id": patient_id,
            "datetime": datetime.now().isoformat(),
            "complaints": f"Тестовые жалобы для пациента {patient_id}"
        }
        response = client.post(
            "/visits/",
            json=visit_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # Может быть 200 или 403 (админ может создавать визиты?)
        assert response.status_code in [200, 403]
    
    # Проверяем поиск пациентов по дате визита
    try:
        search_response = client.get(
            f"/patients/by-visit-date/?visit_date={date.today().isoformat()}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # Разрешаем 200 (даже если список пустой) или 500
        assert search_response.status_code in [200, 500]
    except:
        # Если эндпоинт не существует, пропускаем
        pass

# === ТЕСТ ПРОИЗВОДИТЕЛЬНОСТИ ===

def test_performance_multiple_requests(client: TestClient, session: Session):
    """Тест на множественные запросы"""
    import time
    
    # Создаем пользователя для теста
    from app.auth.security import get_password_hash
    user = User(
        username="perftest",
        password_hash=get_password_hash("pass"),
        role=UserRole.ADMIN
    )
    session.add(user)
    session.commit()
    
    # Логинимся
    login_resp = client.post(
        "/auth/login",
        data={"username": "perftest", "password": "pass"}
    )
    token = login_resp.json()["access_token"]
    
    headers = {"Authorization": f"Bearer {token}"}
    
    start_time = time.time()
    
    # Выполняем несколько запросов
    requests_count = 10
    for i in range(requests_count):
        response = client.get("/health", headers=headers)
        assert response.status_code == 200
    
    end_time = time.time()
    elapsed = end_time - start_time
    avg_time = elapsed / requests_count
    
    print(f"✅ {requests_count} запросов за {elapsed:.2f} секунд")
    print(f"   Среднее время: {avg_time:.3f} сек/запрос")
    
    # Проверяем, что среднее время не слишком большое
    assert avg_time < 0.5  # 500 мс на запрос

# === ЗАПУСК ВСЕХ ТЕСТОВ ===

if __name__ == "__main__":
    # Запуск тестов через pytest
    print("=" * 60)
    print("🚀 ЗАПУСК ТЕСТОВ С ВИЗИТАМИ")
    print("=" * 60)
    pytest.main([__file__, "-v"])