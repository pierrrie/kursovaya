from django.shortcuts import render, redirect
from django.contrib import messages
import requests
import json
from pathlib import Path

API_URL = "http://127.0.0.8:8000"  # FastAPI сервер


def get_json_or_empty(resp):
    try:
        return resp.json()
    except Exception:
        return []


def get_patients_list(headers):
    resp = requests.get(f"{API_URL}/patients/", headers=headers)
    return [] if resp.status_code != 200 else get_json_or_empty(resp)


def get_dentists_list(headers):
    resp = requests.get(f"{API_URL}/admin/users/dentists", headers=headers)
    if resp.status_code == 200:
        return get_json_or_empty(resp)
    return []


def enrich_appointments(appointments, headers):
    patients = {p["id"]: p for p in get_patients_list(headers)}
    doctors = {d["id"]: d for d in get_dentists_list(headers)}
    for appointment in appointments:
        appointment["patient_name"] = patients.get(appointment.get("patient_id"), {}).get("full_name", f"Пациент #{appointment.get('patient_id')}")
        appointment["doctor_name"] = doctors.get(appointment.get("doctor_id"), {}).get("username", f"Врач #{appointment.get('doctor_id')}")
    return appointments


def enrich_visit(visit, headers):
    from datetime import datetime

    patients = {p["id"]: p for p in get_patients_list(headers)}
    doctors = {d["id"]: d for d in get_dentists_list(headers)}
    visit["patient_name"] = patients.get(visit.get("patient_id"), {}).get("full_name", f"Пациент #{visit.get('patient_id')}")
    visit["doctor_name"] = doctors.get(visit.get("doctor_id"), {}).get("username", f"Врач #{visit.get('doctor_id')}")

    raw_datetime = visit.get("datetime")
    if raw_datetime:
        try:
            parsed = datetime.fromisoformat(raw_datetime)
            visit["date"] = parsed.date().isoformat()
            visit["time"] = parsed.time().strftime("%H:%M")
        except ValueError:
            visit["date"] = raw_datetime
            visit["time"] = ""
    return visit


def get_appointment_form_context(request, headers):
    """Получить контекст для формы создания записи на прием"""
    patients = get_patients_list(headers)
    doctors = get_dentists_list(headers)
    return {"patients": patients, "doctors": doctors}


def home_view(request):
    if request.session.get("token"):
        return redirect("/patients/")
    else:
        return redirect("/login/")

def admin_create_user_view(request):
    token = request.session.get("token")
    role = request.session.get("role")
    
    if not token:
        return redirect("/login/")
    
    if role != "administrator":
        messages.error(request, "Только администратор может создавать пользователей")
        return redirect("/")
    
    if request.method == "POST":
        data = {
            "username": request.POST.get("username"),
            "password": request.POST.get("password"),
            "role": request.POST.get("role")
        }
        resp = requests.post(
            f"{API_URL}/auth/register",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        if resp.status_code in [200, 201]:
            messages.success(request, f"Пользователь {data['username']} успешно создан с ролью {data['role']}")
            return redirect("/")
        else:
            try:
                result = resp.json()
                error_msg = result.get('detail', result.get('error', f'Статус код: {resp.status_code}'))
            except Exception:
                error_msg = resp.text
            messages.error(request, f"Ошибка: {error_msg}")
    
    return render(request, "create_user.html")

def login_view(request):
    error = None
    if request.method == "POST":
        data = {
            "username": request.POST["email"],  # используем email как username
            "password": request.POST["password"]
        }
        print(f"DEBUG LOGIN: Отправляем: {data}")
        resp = requests.post(f"{API_URL}/auth/login", data=data)  # используем data вместо json для form-data
        print(f"DEBUG LOGIN: Статус код: {resp.status_code}")
        print(f"DEBUG LOGIN: Ответ: {resp.text[:500]}")
        
        if resp.status_code == 200:
            response_data = resp.json()
            token = response_data.get("access_token")
            user_id = response_data.get("user_id")
            role = response_data.get("role")
            
            print(f"DEBUG LOGIN: Token={token[:20] if token else 'NONE'}..., user_id={user_id}, role={role}")
            
            request.session["token"] = token  # сохраняем токен в сессии Django
            request.session["user_id"] = user_id
            request.session["role"] = role
            
            print(f"DEBUG LOGIN: Сессия сохранена - token={request.session.get('token')[:20] if request.session.get('token') else 'NONE'}...")
            
            messages.success(request, f"Добро пожаловать, {request.POST.get('email')}! Ваша роль: {role}.")
            return redirect("/patients/")     # перенаправление после входа
        else:
            error = resp.json().get("detail", "Ошибка авторизации")
            messages.error(request, error)
            print(f"DEBUG LOGIN: Ошибка - {error}")
    return render(request, "login.html", {"error": error})


def register_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        
        data = {
            "username": email,
            "password": password,
            "role": "manager"
        }
        
        # Регистрируем пользователя и получаем токен
        print(f"DEBUG REGISTER: Отправляем данные: {data}")
        resp = requests.post(
            f"{API_URL}/auth/register",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"DEBUG REGISTER: Статус код: {resp.status_code}")
        print(f"DEBUG REGISTER: Ответ: {resp.text[:500]}")
        
        if resp.status_code == 200:
            response_data = resp.json()
            print(f"DEBUG REGISTER: Полный ответ: {response_data}")
            
            # API теперь возвращает Token с access_token
            token = response_data.get("access_token")
            user_id = response_data.get("user_id")
            role = response_data.get("role")
            
            print(f"DEBUG REGISTER: Token={token}, user_id={user_id}, role={role}")
            
            if token:
                request.session["token"] = token
                request.session["user_id"] = user_id
                request.session["role"] = role
                print(f"DEBUG REGISTER: Сессия сохранена: token={request.session.get('token')[:20]}...")
                messages.success(request, f"Регистрация успешна! Добро пожаловать, {email}! Ваша роль: {role}.")
                return redirect("/patients/")
            else:
                messages.error(request, "Регистрация успешна, но токен не получен")
                return redirect("/login/")
        else:
            try:
                result = resp.json()
                result = json.dumps(result, indent=2, ensure_ascii=False)
            except Exception:
                result = resp.text
            messages.error(request, f"Ошибка: {result}")
            return render(request, "register.html", {"result": result})
    return render(request, "register.html")


def logout_view(request):
    request.session.flush()
    messages.success(request, "Вы успешно вышли из системы")
    return redirect("/login/")


def patients_view(request):
    token = request.session.get("token")
    if not token:
        return redirect("/login/")
    
    headers = {"Authorization": f"Bearer {token}"}
    visit_date = (request.GET.get("visit_date") or "").strip()
    if visit_date:
        resp = requests.get(
            f"{API_URL}/patients/by-visit-date/",
            headers=headers,
            params={"visit_date": visit_date},
        )
    else:
        resp = requests.get(f"{API_URL}/patients/", headers=headers)
    if resp.status_code == 200:
        patients = resp.json()
    else:
        patients = []
        error = resp.json().get("detail", "Ошибка загрузки пациентов")
    
    return render(
        request,
        "patients.html",
        {
            "patients": patients,
            "selected_visit_date": visit_date,
            "error": error if 'error' in locals() else None,
        },
    )


def patient_detail_view(request, patient_id):
    token = request.session.get("token")
    if not token:
        return redirect("/login/")
    
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{API_URL}/patients/{patient_id}", headers=headers)
    if resp.status_code == 200:
        patient = resp.json()
    else:
        patient = None
        error = resp.json().get("detail", "Ошибка загрузки пациента")
    
    return render(request, "patient_detail.html", {"patient": patient, "error": error if 'error' in locals() else None})


def patient_edit_view(request, patient_id):
    token = request.session.get("token")
    if not token:
        return redirect("/login/")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    if request.method == "POST":
        last_name = request.POST.get("last_name", "")
        first_name = request.POST.get("first_name", "")
        middle_name = request.POST.get("middle_name", "")
        full_name = f"{last_name} {first_name} {middle_name}".strip()
        data = {
            "full_name": full_name,
            "birth_date": request.POST.get("birth_date"),
            "phone": request.POST.get("phone"),
            "address": request.POST.get("address"),
            "allergies": request.POST.get("allergies"),
            "note": request.POST.get("note"),
        }
        resp = requests.put(f"{API_URL}/patients/{patient_id}", json=data, headers=headers)
        if resp.status_code in [200, 201]:
            messages.success(request, "Данные пациента успешно обновлены!")
            return redirect(f"/patients/{patient_id}/")
        else:
            try:
                result = resp.json()
                error_msg = result.get('detail', result.get('error', f'Статус код: {resp.status_code}'))
            except Exception:
                error_msg = f'Статус код: {resp.status_code}'
            messages.error(request, f"Ошибка: {error_msg}")
    
    # Получаем данные пациента для предзаполнения формы
    resp = requests.get(f"{API_URL}/patients/{patient_id}", headers=headers)
    if resp.status_code == 200:
        patient = resp.json()
        # Разделяем full_name на части
        parts = patient.get('full_name', '').split()
        if len(parts) >= 2:
            patient['last_name'] = parts[0]
            patient['first_name'] = parts[1]
            patient['middle_name'] = parts[2] if len(parts) > 2 else ''
        else:
            patient['last_name'] = ''
            patient['first_name'] = patient.get('full_name', '')
            patient['middle_name'] = ''
    else:
        patient = None
        error = resp.json().get("detail", "Ошибка загрузки пациента")
    
    return render(request, "patient_form.html", {"patient": patient, "is_edit": True, "error": error if 'error' in locals() else None})


def patient_create_view(request):
    token = request.session.get("token")
    print(f"DEBUG PATIENT_CREATE: token={token[:20] if token else 'NONE'}...")
    if not token:
        messages.error(request, "Токен не найден. Пожалуйста, залогиньтесь заново.")
        return redirect("/login/")
    
    if request.method == "POST":
        last_name = request.POST.get("last_name")
        first_name = request.POST.get("first_name")
        middle_name = request.POST.get("middle_name", "")
        full_name = f"{last_name} {first_name} {middle_name}".strip()
        data = {
            "full_name": full_name,
            "birth_date": request.POST.get("birth_date"),
            "phone": request.POST.get("phone"),
            "address": request.POST.get("address"),
            "allergies": request.POST.get("allergies"),
            "note": request.POST.get("note"),
        }
        headers = {"Authorization": f"Bearer {token}"}
        print(f"DEBUG PATIENT_CREATE: Отправляем пациента: {data}")
        print(f"DEBUG PATIENT_CREATE: Headers: {headers}")
        
        resp = requests.post(f"{API_URL}/patients/", json=data, headers=headers)
        print(f"DEBUG PATIENT_CREATE: Статус код: {resp.status_code}")
        print(f"DEBUG PATIENT_CREATE: Ответ: {resp.text[:300]}")
        
        if resp.status_code in [200, 201]:
            messages.success(request, "Пациент успешно создан!")
            return redirect("/patients/")
        else:
            try:
                result = resp.json()
                error_msg = result.get('detail', result.get('error', f'Статус код: {resp.status_code}'))
            except Exception:
                error_msg = f'Статус код: {resp.status_code}'
            messages.error(request, f"Ошибка: {error_msg}")
            return render(request, "patient_form.html")
    
    return render(request, "patient_form.html")


def patient_delete_view(request, patient_id):
    token = request.session.get("token")
    role = request.session.get("role")
    if not token:
        return redirect("/login/")

    if role not in ["manager", "administrator"]:
        messages.error(request, "Только менеджер или администратор может удалять пациентов")
        return redirect("/patients/")

    if request.method != "POST":
        return redirect("/patients/")

    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.delete(f"{API_URL}/patients/{patient_id}", headers=headers)
    if resp.status_code in [200, 202, 204]:
        messages.success(request, "Пациент удален")
    elif resp.status_code == 404:
        messages.error(request, "Пациент не найден")
    else:
        messages.error(request, f"Ошибка удаления пациента: {resp.status_code}")
    return redirect("/patients/")


def visits_view(request):
    token = request.session.get("token")
    if not token:
        return redirect("/login/")
    
    headers = {"Authorization": f"Bearer {token}"}
    date_from = (request.GET.get("date_from") or "").strip()
    date_to = (request.GET.get("date_to") or "").strip()
    params = {}
    if date_from:
        params["date_from"] = date_from
    if date_to:
        params["date_to"] = date_to

    resp = requests.get(f"{API_URL}/visits/", headers=headers, params=params if params else None)
    if resp.status_code == 200:
        visits = [enrich_visit(v, headers) for v in resp.json()]
    else:
        visits = []
        error = resp.json().get("detail", "Ошибка загрузки визитов")
    
    return render(
        request,
        "visits.html",
        {
            "visits": visits,
            "selected_date_from": date_from,
            "selected_date_to": date_to,
            "error": error if 'error' in locals() else None,
        },
    )


def visit_detail_view(request, visit_id):
    token = request.session.get("token")
    if not token:
        return redirect("/login/")
    
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{API_URL}/visits/{visit_id}", headers=headers)
    if resp.status_code == 200:
        visit = enrich_visit(resp.json(), headers)
    else:
        visit = None
        error = resp.json().get("detail", "Ошибка загрузки визита")
    
    return render(request, "visit_detail.html", {"visit": visit, "error": error if 'error' in locals() else None})


def visit_create_view(request):
    token = request.session.get("token")
    if not token:
        return redirect("/login/")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    if request.method == "POST":
        from datetime import datetime
        data = {
            "patient_id": int(request.POST.get("patient_id")),
            "datetime": request.POST.get("datetime"),
            "complaints": request.POST.get("complaints"),
            "anamnesis": request.POST.get("anamnesis"),
            "diagnosis": request.POST.get("diagnosis"),
            "exam_results": request.POST.get("exam_results"),
            "notes": request.POST.get("notes"),
        }
        resp = requests.post(f"{API_URL}/visits/", json=data, headers=headers)
        if resp.status_code in [200, 201]:
            messages.success(request, "Визит успешно создан!")
            return redirect("/visits/")
        else:
            try:
                result = resp.json()
                error_msg = result.get('detail', result.get('error', f'Статус код: {resp.status_code}'))
            except Exception:
                error_msg = f'Статус код: {resp.status_code}'
            messages.error(request, f"Ошибка: {error_msg}")
    
    # Получаем список пациентов для выбора
    resp = requests.get(f"{API_URL}/patients/", headers=headers)
    patients = [] if resp.status_code != 200 else resp.json()
    
    return render(request, "visit_form.html", {"patients": patients})


def visit_edit_view(request, visit_id):
    token = request.session.get("token")
    if not token:
        return redirect("/login/")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    if request.method == "POST":
        data = {
            "datetime": request.POST.get("datetime"),
            "complaints": request.POST.get("complaints"),
            "anamnesis": request.POST.get("anamnesis"),
            "diagnosis": request.POST.get("diagnosis"),
            "exam_results": request.POST.get("exam_results"),
            "notes": request.POST.get("notes"),
        }
        resp = requests.put(f"{API_URL}/visits/{visit_id}", json=data, headers=headers)
        if resp.status_code in [200, 201]:
            messages.success(request, "Визит успешно обновлен!")
            return redirect("/dentist-diary/")
        else:
            try:
                result = resp.json()
                error_msg = result.get('detail', result.get('error', f'Статус код: {resp.status_code}'))
            except Exception:
                error_msg = f'Статус код: {resp.status_code}'
            messages.error(request, f"Ошибка: {error_msg}")
    
    # Получаем данные визита для редактирования
    resp = requests.get(f"{API_URL}/visits/{visit_id}", headers=headers)
    if resp.status_code == 200:
        visit = resp.json()
        # Преобразуем datetime в формат для input type="datetime-local"
        raw_datetime = visit.get("datetime")
        if raw_datetime:
            from datetime import datetime
            try:
                parsed = datetime.fromisoformat(raw_datetime)
                visit["datetime_local"] = parsed.strftime("%Y-%m-%dT%H:%M")
            except ValueError:
                visit["datetime_local"] = raw_datetime
    else:
        visit = None
        error = resp.json().get("detail", "Ошибка загрузки визита")
    
    return render(request, "visit_edit.html", {"visit": visit, "error": error if 'error' in locals() else None})


def appointments_view(request):
    token = request.session.get("token")
    if not token:
        return redirect("/login/")
    
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{API_URL}/appointments/", headers=headers)
    if resp.status_code == 200:
        appointments = enrich_appointments(resp.json(), headers)
    else:
        appointments = []
        error = resp.json().get("detail", "Ошибка загрузки записей")
    
    return render(request, "appointments.html", {"appointments": appointments, "error": error if 'error' in locals() else None})


def appointment_detail_view(request, appointment_id):
    token = request.session.get("token")
    if not token:
        return redirect("/login/")
    
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{API_URL}/appointments/{appointment_id}", headers=headers)
    if resp.status_code == 200:
        appointment = enrich_visit(resp.json(), headers)
    else:
        appointment = None
        error = resp.json().get("detail", "Ошибка загрузки записи")
    
    return render(request, "appointment_detail.html", {"appointment": appointment, "error": error if 'error' in locals() else None})


def get_appointment_form_context(request, headers):
    """Получить контекст для формы создания записи на прием"""
    patients = get_patients_list(headers)
    doctors = get_dentists_list(headers)
    return {"patients": patients, "doctors": doctors}


def appointment_create_view(request):
    token = request.session.get("token")
    if not token:
        return redirect("/login/")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    if request.method == "POST":
        from datetime import datetime
        
        try:
            # Проверяем обязательные поля
            patient_id = request.POST.get("patient_id", "").strip()
            doctor_id = request.POST.get("doctor_id", "").strip()
            dt_str = request.POST.get("datetime", "").strip()
            
            if not patient_id:
                messages.error(request, "Пожалуйста, выберите пациента")
                return render(request, "appointment_form.html", get_appointment_form_context(request, headers))
            if not doctor_id:
                messages.error(request, "Пожалуйста, выберите врача")
                return render(request, "appointment_form.html", get_appointment_form_context(request, headers))
            if not dt_str:
                messages.error(request, "Пожалуйста, укажите дату и время приема")
                return render(request, "appointment_form.html", get_appointment_form_context(request, headers))
            
            # Парсим дату и время
            dt = datetime.fromisoformat(dt_str)
            
            data = {
                "patient_id": int(patient_id),
                "doctor_id": int(doctor_id),
                "date": dt.strftime("%Y-%m-%d"),
                "time": dt.strftime("%H:%M"),
                "comment": request.POST.get("reason", "").strip(),
            }
            resp = requests.post(f"{API_URL}/appointments/", json=data, headers=headers)
            if resp.status_code in [200, 201]:
                messages.success(request, "Запись успешно создана!")
                return redirect("/appointments/")
            else:
                try:
                    result = resp.json()
                    # Если это ошибка валидации с деталями
                    if "detail" in result and isinstance(result["detail"], list):
                        error_msg = "Ошибки валидации:\n"
                        for err in result["detail"]:
                            if isinstance(err, dict):
                                field = ".".join(str(loc) for loc in err.get("loc", []))
                                msg = err.get("msg", "Неизвестная ошибка")
                                error_msg += f"- {field}: {msg}\n"
                    else:
                        error_msg = result.get('detail', result.get('error', f'Статус код: {resp.status_code}'))
                except Exception:
                    error_msg = f'Статус код: {resp.status_code}'
                messages.error(request, f"Ошибка валидации: {error_msg}")
        except ValueError as e:
            messages.error(request, f"Ошибка при обработке данных: {str(e)}")
        except Exception as e:
            messages.error(request, f"Ошибка: {str(e)}")
    
    context = get_appointment_form_context(request, headers)
    return render(request, "appointment_form.html", context)


def dentist_diary_view(request):
    """Дневник врача - просмотр расписания и управление приемами"""
    token = request.session.get("token")
    role = request.session.get("role")
    
    if not token:
        return redirect("/login/")
    
    if role != "dentist":
        messages.error(request, "Только стоматолог может просматривать дневник")
        return redirect("/")
    
    headers = {"Authorization": f"Bearer {token}"}
    from datetime import datetime, timedelta
    
    # Получаем дату для просмотра (по умолчанию сегодня)
    day_str = request.GET.get("day", datetime.now().strftime("%Y-%m-%d"))
    
    try:
        selected_day = datetime.strptime(day_str, "%Y-%m-%d").date()
    except ValueError:
        selected_day = datetime.now().date()
    
    # Получаем расписание на день
    resp = requests.get(
        f"{API_URL}/dentist-diary/day",
        params={"day": selected_day.isoformat()},
        headers=headers
    )
    appointments = [] if resp.status_code != 200 else get_json_or_empty(resp)
    
    # Обогащаем данные пациентов
    patients = {p["id"]: p for p in get_patients_list(headers)}
    for apt in appointments:
        apt["patient_name"] = patients.get(apt.get("patient_id"), {}).get("full_name", f"Пациент #{apt.get('patient_id')}")
    
    # Получаем визиты на сегодня
    today_visits = []
    if selected_day == datetime.now().date():
        resp = requests.get(
            f"{API_URL}/dentist-diary/today-visits",
            headers=headers
        )
        if resp.status_code == 200:
            today_visits = [enrich_visit(v, headers) for v in get_json_or_empty(resp)]
    
    context = {
        "selected_day": selected_day.isoformat(),
        "appointments": appointments,
        "today_visits": today_visits,
        "prev_day": (selected_day - timedelta(days=1)).isoformat(),
        "next_day": (selected_day + timedelta(days=1)).isoformat(),
    }
    return render(request, "dentist_diary.html", context)


def appointment_edit_view(request, appointment_id):
    """Редактирование приема"""
    token = request.session.get("token")
    role = request.session.get("role")
    
    if not token:
        return redirect("/login/")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    if request.method == "POST":
        data = {
            "date": request.POST.get("date"),
            "time": request.POST.get("time"),
            "comment": request.POST.get("comment", "").strip(),
        }
        # Убираем пустые значения
        data = {k: v for k, v in data.items() if v}
        resp = requests.put(f"{API_URL}/appointments/{appointment_id}", json=data, headers=headers)
        if resp.status_code in [200, 201]:
            messages.success(request, "Запись успешно обновлена!")
            return redirect("/dentist-diary/" if role == "dentist" else "/appointments/")
        else:
            try:
                result = resp.json()
                error_msg = result.get('detail', result.get('error', f'Статус код: {resp.status_code}'))
            except Exception:
                error_msg = f'Статус код: {resp.status_code}'
            messages.error(request, f"Ошибка: {error_msg}")
    
    # Получаем данные приема
    resp = requests.get(f"{API_URL}/appointments/{appointment_id}", headers=headers)
    if resp.status_code == 200:
        appointment = resp.json()
        patients = {p["id"]: p for p in get_patients_list(headers)}
        doctors = {d["id"]: d for d in get_dentists_list(headers)}
        appointment["patient_name"] = patients.get(appointment.get("patient_id"), {}).get("full_name", f"Пациент #{appointment.get('patient_id')}")
        appointment["doctor_name"] = doctors.get(appointment.get("doctor_id"), {}).get("username", f"Врач #{appointment.get('doctor_id')}")
    else:
        appointment = None
        error = resp.json().get("detail", "Ошибка загрузки приема")
    
    return render(request, "appointment_edit.html", {"appointment": appointment, "error": error if 'error' in locals() else None})


def dentist_referrals_view(request):
    """Управление направлениями стоматолога"""
    token = request.session.get("token")
    role = request.session.get("role")
    
    if not token or role != "dentist":
        messages.error(request, "Только стоматолог может управлять направлениями")
        return redirect("/")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Получаем все направления стоматолога
    resp = requests.get(f"{API_URL}/referrals/", headers=headers)
    referrals = [] if resp.status_code != 200 else get_json_or_empty(resp)
    
    # Обогащаем данными пациентов
    patients = {p["id"]: p for p in get_patients_list(headers)}
    for ref in referrals:
        ref["patient_name"] = patients.get(ref.get("patient_id"), {}).get("full_name", f"Пациент #{ref.get('patient_id')}")
        
        # Обрабатываем дату
        if ref.get("date"):
            try:
                from datetime import datetime
                # Если дата приходит как строка ISO, парсим её
                if isinstance(ref["date"], str):
                    # Убираем микросекунды и timezone info если есть
                    date_str = ref["date"].split('.')[0]  # Убираем микросекунды
                    ref["date"] = datetime.fromisoformat(date_str)
                # Если уже datetime объект, оставляем как есть
            except (ValueError, AttributeError):
                # Если не удалось распарсить, оставляем как есть
                pass
    
    return render(request, "dentist_referrals.html", {"referrals": referrals})


def dentist_referral_create_view(request):
    """Создание направления"""
    token = request.session.get("token")
    role = request.session.get("role")
    
    if not token or role != "dentist":
        messages.error(request, "Только стоматолог может создавать направления")
        return redirect("/")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    if request.method == "POST":
        data = {
            "patient_id": int(request.POST.get("patient_id")),
            "referral_type": request.POST.get("referral_type"),
            "destination": request.POST.get("destination"),
            "reason": request.POST.get("reason"),
            "date": request.POST.get("date"),
        }
        if request.POST.get("visit_id"):
            data["visit_id"] = int(request.POST.get("visit_id"))
        
        resp = requests.post(f"{API_URL}/referrals/", json=data, headers=headers)
        if resp.status_code in [200, 201]:
            messages.success(request, "Направление успешно создано!")
            return redirect("/dentist-documents/referrals/")
        else:
            try:
                result = resp.json()
                error_msg = result.get('detail', result.get('error', f'Статус код: {resp.status_code}'))
            except Exception:
                error_msg = f'Статус код: {resp.status_code}'
            messages.error(request, f"Ошибка: {error_msg}")
    
    # Получаем пациентов и визиты для выбора
    patients = get_patients_list(headers)
    # Получаем визиты стоматолога за последний месяц
    from datetime import datetime, timedelta
    month_ago = (datetime.now() - timedelta(days=30)).isoformat()
    resp = requests.get(f"{API_URL}/visits/?date_from={month_ago}", headers=headers)
    visits = [] if resp.status_code != 200 else get_json_or_empty(resp)
    
    # Обогащаем визиты данными пациентов
    patients_dict = {p["id"]: p for p in patients}
    for visit in visits:
        visit["patient_name"] = patients_dict.get(visit.get("patient_id"), {}).get("full_name", f"Пациент #{visit.get('patient_id')}")
    
    return render(request, "dentist_referral_form.html", {"patients": patients, "visits": visits})


def dentist_research_view(request):
    """История проведенных исследований"""
    token = request.session.get("token")
    role = request.session.get("role")

    if not token or role != "dentist":
        messages.error(request, "Только стоматолог может просматривать исследования")
        return redirect("/")

    headers = {"Authorization": f"Bearer {token}"}

    resp = requests.get(f"{API_URL}/research/", headers=headers)
    researches = [] if resp.status_code != 200 else get_json_or_empty(resp)

    # Обогащаем список данными пациентов для отображения ФИО
    patients = {p["id"]: p for p in get_patients_list(headers)}
    for item in researches:
        item["patient_name"] = patients.get(item.get("patient_id"), {}).get(
            "full_name", f"Пациент #{item.get('patient_id')}"
        )

    return render(request, "dentist_research.html", {"researches": researches})


def dentist_research_create_view(request):
    """Добавление исследования"""
    token = request.session.get("token")
    role = request.session.get("role")

    if not token or role != "dentist":
        messages.error(request, "Только стоматолог может добавлять исследования")
        return redirect("/")

    headers = {"Authorization": f"Bearer {token}"}

    if request.method == "POST":
        patient_id = request.POST.get("patient_id")
        visit_id = request.POST.get("visit_id")
        datetime_value = request.POST.get("datetime")
        research_type = request.POST.get("type")
        result = request.POST.get("result")

        if not patient_id or not datetime_value or not research_type:
            messages.error(request, "Заполните обязательные поля: пациент, дата/время, тип")
        else:
            data = {
                "datetime": datetime_value,
                "type": research_type,
                "result": result or None,
            }
            params = {}
            if visit_id:
                params["visit_id"] = int(visit_id)

            resp = requests.post(
                f"{API_URL}/research/patient/{int(patient_id)}",
                json=data,
                params=params,
                headers=headers,
            )
            if resp.status_code in [200, 201]:
                messages.success(request, "Исследование успешно добавлено")
                return redirect("/dentist-documents/research/")
            try:
                error_msg = resp.json().get("detail", f"Статус код: {resp.status_code}")
            except Exception:
                error_msg = f"Статус код: {resp.status_code}"
            messages.error(request, f"Ошибка: {error_msg}")

    patients = get_patients_list(headers)

    # Для удобства выбора показываем недавние визиты стоматолога
    from datetime import datetime, timedelta

    month_ago = (datetime.now() - timedelta(days=60)).isoformat()
    resp = requests.get(f"{API_URL}/visits/?date_from={month_ago}", headers=headers)
    visits = [] if resp.status_code != 200 else get_json_or_empty(resp)
    patients_dict = {p["id"]: p for p in patients}
    for visit in visits:
        visit["patient_name"] = patients_dict.get(visit.get("patient_id"), {}).get(
            "full_name", f"Пациент #{visit.get('patient_id')}"
        )

    return render(
        request,
        "dentist_research_form.html",
        {"patients": patients, "visits": visits},
    )


def dentist_prescriptions_view(request):
    """Назначения пациентам"""
    token = request.session.get("token")
    role = request.session.get("role")

    if not token or role != "dentist":
        messages.error(request, "Только стоматолог может работать с назначениями")
        return redirect("/")

    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{API_URL}/prescriptions/", headers=headers)
    prescriptions = [] if resp.status_code != 200 else get_json_or_empty(resp)

    patients = {p["id"]: p for p in get_patients_list(headers)}
    for item in prescriptions:
        item["patient_name"] = patients.get(item.get("patient_id"), {}).get(
            "full_name", f"Пациент #{item.get('patient_id')}"
        )

    return render(request, "dentist_prescriptions.html", {"prescriptions": prescriptions})


def dentist_prescription_create_view(request):
    """Добавление назначения пациенту"""
    token = request.session.get("token")
    role = request.session.get("role")

    if not token or role != "dentist":
        messages.error(request, "Только стоматолог может создавать назначения")
        return redirect("/")

    headers = {"Authorization": f"Bearer {token}"}

    if request.method == "POST":
        patient_id = request.POST.get("patient_id")
        visit_id = request.POST.get("visit_id")
        medication = request.POST.get("medication")
        dosage = request.POST.get("dosage")
        instructions = request.POST.get("instructions")
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")

        if not patient_id or not medication or not dosage or not start_date:
            messages.error(request, "Заполните обязательные поля: пациент, препарат, дозировка, дата начала")
        else:
            data = {
                "medication": medication,
                "dosage": dosage,
                "instructions": instructions or None,
                "start_date": start_date,
                "end_date": end_date or None,
            }
            params = {}
            if visit_id:
                params["visit_id"] = int(visit_id)
            resp = requests.post(
                f"{API_URL}/prescriptions/patient/{int(patient_id)}",
                json=data,
                params=params,
                headers=headers,
            )
            if resp.status_code in [200, 201]:
                messages.success(request, "Назначение успешно добавлено")
                return redirect("/dentist-documents/prescriptions/")
            try:
                error_msg = resp.json().get("detail", f"Статус код: {resp.status_code}")
            except Exception:
                error_msg = f"Статус код: {resp.status_code}"
            messages.error(request, f"Ошибка: {error_msg}")

    patients = get_patients_list(headers)
    from datetime import datetime, timedelta
    month_ago = (datetime.now() - timedelta(days=60)).isoformat()
    resp = requests.get(f"{API_URL}/visits/?date_from={month_ago}", headers=headers)
    visits = [] if resp.status_code != 200 else get_json_or_empty(resp)
    patients_dict = {p["id"]: p for p in patients}
    for visit in visits:
        visit["patient_name"] = patients_dict.get(visit.get("patient_id"), {}).get(
            "full_name", f"Пациент #{visit.get('patient_id')}"
        )

    return render(request, "dentist_prescription_form.html", {"patients": patients, "visits": visits})


def dentist_teeth_view(request):
    """Зубная формула пациента"""
    token = request.session.get("token")
    role = request.session.get("role")

    if not token or role != "dentist":
        messages.error(request, "Только стоматолог может работать с зубной формулой")
        return redirect("/")

    headers = {"Authorization": f"Bearer {token}"}
    patient_id = request.GET.get("patient_id")
    teeth = []
    selected_patient = None

    patients = get_patients_list(headers)
    if patient_id:
        resp_patient = requests.get(f"{API_URL}/patients/{patient_id}", headers=headers)
        if resp_patient.status_code == 200:
            selected_patient = resp_patient.json()
        resp = requests.get(f"{API_URL}/teeth/patient/{int(patient_id)}", headers=headers)
        if resp.status_code == 200:
            teeth = get_json_or_empty(resp)
        else:
            try:
                error_msg = resp.json().get("detail", f"Статус код: {resp.status_code}")
            except Exception:
                error_msg = f"Статус код: {resp.status_code}"
            messages.error(request, f"Ошибка загрузки зубной формулы: {error_msg}")

    return render(
        request,
        "dentist_teeth.html",
        {"patients": patients, "teeth": teeth, "selected_patient": selected_patient},
    )


def dentist_tooth_create_view(request):
    """Добавление записи в зубную формулу"""
    token = request.session.get("token")
    role = request.session.get("role")

    if not token or role != "dentist":
        messages.error(request, "Только стоматолог может добавлять записи о зубах")
        return redirect("/")

    headers = {"Authorization": f"Bearer {token}"}

    if request.method == "POST":
        patient_id = request.POST.get("patient_id")
        number = request.POST.get("number")
        status_value = request.POST.get("status")
        notes = request.POST.get("notes")

        if not patient_id or not number or not status_value:
            messages.error(request, "Заполните обязательные поля: пациент, номер зуба, статус")
        else:
            data = {
                "number": int(number),
                "status": status_value,
                "notes": notes or None,
            }
            resp = requests.post(
                f"{API_URL}/teeth/patient/{int(patient_id)}",
                json=data,
                headers=headers,
            )
            if resp.status_code in [200, 201]:
                messages.success(request, "Запись о зубе добавлена")
                return redirect(f"/dentist-documents/teeth/?patient_id={patient_id}")
            try:
                error_msg = resp.json().get("detail", f"Статус код: {resp.status_code}")
            except Exception:
                error_msg = f"Статус код: {resp.status_code}"
            messages.error(request, f"Ошибка: {error_msg}")

    patients = get_patients_list(headers)
    return render(request, "dentist_tooth_form.html", {"patients": patients})


def dentist_patient_history_view(request):
    """Выписка из медицинской карты"""
    token = request.session.get("token")
    role = request.session.get("role")
    
    if not token or role != "dentist":
        messages.error(request, "Только стоматолог может создавать выписки")
        return redirect("/")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    if request.method == "POST":
        patient_id = request.POST.get("patient_id")
        if patient_id:
            # Получаем данные пациента
            resp = requests.get(f"{API_URL}/patients/{patient_id}", headers=headers)
            if resp.status_code == 200:
                patient = resp.json()
                
                # Получаем визиты пациента
                resp = requests.get(f"{API_URL}/visits/?patient_id={patient_id}", headers=headers)
                visits = [] if resp.status_code != 200 else resp.json()
                
                # Получаем назначения
                resp = requests.get(f"{API_URL}/prescriptions/?patient_id={patient_id}", headers=headers)
                prescriptions = [] if resp.status_code != 200 else resp.json()
                
                # Получаем исследования
                resp = requests.get(f"{API_URL}/research/?patient_id={patient_id}", headers=headers)
                research = [] if resp.status_code != 200 else resp.json()
                
                # Получаем направления
                resp = requests.get(f"{API_URL}/referrals/?patient_id={patient_id}", headers=headers)
                referrals = [] if resp.status_code != 200 else resp.json()
                
                # Получаем работы
                resp = requests.get(f"{API_URL}/work/?patient_id={patient_id}", headers=headers)
                works = [] if resp.status_code != 200 else resp.json()
                
                # Формируем данные для шаблона
                history_data = {
                    "patient": patient,
                    "visits": visits,
                    "prescriptions": prescriptions,
                    "research": research,
                    "referrals": referrals,
                    "works": works
                }
                
                messages.success(request, "Выписка подготовлена!")
                return render(request, "dentist_patient_history.html", {"history": history_data, "generated": True})
            else:
                messages.error(request, "Ошибка при получении данных пациента")
    
    # Получаем пациентов для выбора
    patients = get_patients_list(headers)
    return render(request, "dentist_patient_history.html", {"patients": patients})


def dentist_medical_card_view(request):
    """Медицинская карта стоматологического больного (форма 043/у)"""
    token = request.session.get("token")
    role = request.session.get("role")
    
    if not token or role != "dentist":
        messages.error(request, "Только стоматолог может создавать медицинские карты")
        return redirect("/")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    if request.method == "POST":
        patient_id = request.POST.get("patient_id")
        if patient_id:
            # Получаем данные для медицинской карты
            resp = requests.get(f"{API_URL}/documents/patient-history/{patient_id}", headers=headers)
            if resp.status_code == 200:
                card_data = resp.json()
                # Здесь можно добавить логику для генерации Word/Excel документа
                messages.success(request, "Медицинская карта подготовлена!")
                return render(request, "dentist_medical_card.html", {"card": card_data, "generated": True})
            else:
                messages.error(request, "Ошибка при получении данных пациента")
    
    # Получаем пациентов для выбора
    patients = get_patients_list(headers)
    return render(request, "dentist_medical_card.html", {"patients": patients})


def dentist_work_orders_view(request):
    """Наряды на выполнение работ"""
    token = request.session.get("token")
    role = request.session.get("role")
    
    if not token or role != "dentist":
        messages.error(request, "Только стоматолог может управлять нарядами")
        return redirect("/")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Получаем все работы стоматолога
    resp = requests.get(f"{API_URL}/works/", headers=headers)
    works = [] if resp.status_code != 200 else get_json_or_empty(resp)
    
    # Получаем все визиты стоматолога для обогащения данных
    from datetime import datetime, timedelta
    month_ago = (datetime.now() - timedelta(days=30)).isoformat()
    resp_visits = requests.get(f"{API_URL}/visits/?date_from={month_ago}", headers=headers)
    visits = [] if resp_visits.status_code != 200 else get_json_or_empty(resp_visits)
    
    # Создаем словарь визитов для быстрого доступа
    visits_dict = {v["id"]: v for v in visits}
    
    # Обогащаем данными пациентов
    patients = {p["id"]: p for p in get_patients_list(headers)}
    for work in works:
        visit = visits_dict.get(work.get("visit_id"))
        if visit:
            work["patient_name"] = patients.get(visit.get("patient_id"), {}).get("full_name", f"Пациент #{visit.get('patient_id')}")
            work["visit_datetime"] = visit.get("datetime")
        else:
            work["patient_name"] = "Неизвестно"
            work["visit_datetime"] = None
            
        # Обрабатываем дату работы
        if work.get("work_date"):
            try:
                from datetime import datetime
                # Если дата приходит как строка ISO, парсим её
                if isinstance(work["work_date"], str):
                    # Убираем микросекунды и timezone info если есть
                    date_str = work["work_date"].split('.')[0]  # Убираем микросекунды
                    work["work_date"] = datetime.fromisoformat(date_str)
                # Если уже datetime объект, оставляем как есть
            except (ValueError, AttributeError):
                # Если не удалось распарсить, оставляем как есть
                pass
    
    return render(request, "dentist_work_orders.html", {"works": works})


def dentist_work_create_view(request):
    """Создание наряда на работу"""
    token = request.session.get("token")
    role = request.session.get("role")
    
    if not token or role != "dentist":
        messages.error(request, "Только стоматолог может создавать наряды")
        return redirect("/")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    if request.method == "POST":
        data = {
            "visit_id": int(request.POST.get("visit_id")),
            "description": request.POST.get("description"),
            "materials": request.POST.get("materials"),
            "tooth_numbers": request.POST.get("tooth_numbers"),
            "work_date": request.POST.get("work_date"),
        }
        if request.POST.get("service_code_id"):
            data["service_code_id"] = int(request.POST.get("service_code_id"))
        if request.POST.get("duration_minutes"):
            data["duration_minutes"] = int(request.POST.get("duration_minutes"))
        if request.POST.get("cost"):
            data["cost"] = float(request.POST.get("cost"))
        
        resp = requests.post(f"{API_URL}/works/visit/{data['visit_id']}", json={k: v for k, v in data.items() if k != 'visit_id'}, headers=headers)
        if resp.status_code in [200, 201]:
            messages.success(request, "Наряд успешно создан!")
            return redirect("/dentist-documents/work-orders/")
        else:
            try:
                result = resp.json()
                error_msg = result.get('detail', result.get('error', f'Статус код: {resp.status_code}'))
            except Exception:
                error_msg = f'Статус код: {resp.status_code}'
            messages.error(request, f"Ошибка: {error_msg}")
    
    # Получаем визиты стоматолога за последний месяц для выбора
    from datetime import datetime, timedelta
    month_ago = (datetime.now() - timedelta(days=30)).isoformat()
    resp = requests.get(f"{API_URL}/visits/?date_from={month_ago}", headers=headers)
    visits = [] if resp.status_code != 200 else get_json_or_empty(resp)
    
    # Обогащаем визиты данными пациентов
    patients = {p["id"]: p for p in get_patients_list(headers)}
    for visit in visits:
        visit["patient_name"] = patients.get(visit.get("patient_id"), {}).get("full_name", f"Пациент #{visit.get('patient_id')}")
    
    return render(request, "dentist_work_form.html", {"visits": visits})


def download_patient_history_word(request, patient_id):
    """Скачивание истории болезни пациента в формате Word"""
    token = request.session.get("token")
    if not token:
        from django.http import HttpResponse
        return HttpResponse("Необходима авторизация", status=401)
    
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(
        f"{API_URL}/documents/patient-history/{patient_id}/word",
        headers=headers,
    )
    if resp.status_code != 200:
        from django.http import HttpResponse
        return HttpResponse(f"Ошибка генерации документа: {resp.status_code}", status=resp.status_code)

    from django.http import HttpResponse
    response = HttpResponse(
        resp.content,
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )
    # ASCII-имя файла для совместимости с Django и браузерами.
    response['Content-Disposition'] = 'attachment; filename="patient_history.docx"'
    return response


def download_medical_card_word(request, patient_id):
    """Скачивание медицинской карты пациента (форма 043/у) в формате Word"""
    token = request.session.get("token")
    if not token:
        messages.error(request, "Необходима авторизация")
        return redirect("/login/")
    
    headers = {"Authorization": f"Bearer {token}"}

    resp = requests.get(
        f"{API_URL}/documents/medical-card/{patient_id}/word",
        headers=headers,
    )
    if resp.status_code != 200:
        messages.error(request, "Ошибка генерации медицинской карты")
        return redirect(f"/patients/{patient_id}/")

    from django.http import HttpResponse
    response = HttpResponse(
        resp.content,
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )
    response['Content-Disposition'] = 'attachment; filename="medical_card_043u.docx"'
    return response


def download_medical_card_excel(request, patient_id):
    """Скачивание медицинской карты пациента (форма 043/у) в формате XLSX"""
    token = request.session.get("token")
    if not token:
        messages.error(request, "Необходима авторизация")
        return redirect("/login/")

    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(
        f"{API_URL}/documents/patient-history/{patient_id}",
        headers=headers,
    )
    if resp.status_code != 200:
        messages.error(request, "Ошибка генерации Excel-файла")
        return redirect(f"/patients/{patient_id}/")

    card = resp.json()

    from django.http import HttpResponse
    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Медицинская карта"

    patient = card.get("patient", {})
    sheet.append(["Поле", "Значение"])
    sheet.append(["ФИО", patient.get("full_name", "")])
    sheet.append(["Дата рождения", patient.get("birth_date", "")])
    sheet.append(["Телефон", patient.get("phone", "")])
    sheet.append(["Адрес", patient.get("address", "")])
    sheet.append(["Аллергии", patient.get("allergies", "")])
    sheet.append([])

    sheet.append(["Зуб", "Статус", "Примечания"])
    tooth_formula = card.get("tooth_formula", {})
    for tooth_num, tooth_data in tooth_formula.items():
        sheet.append([
            tooth_num,
            tooth_data.get("status", ""),
            tooth_data.get("notes", ""),
        ])
    sheet.append([])

    sheet.append(["Дата визита", "Жалобы", "Диагноз", "Лечение", "Рекомендации"])
    for visit in card.get("visits", []):
        sheet.append([
            visit.get("datetime", ""),
            visit.get("complaints", ""),
            visit.get("diagnosis", ""),
            visit.get("exam_results", ""),
            visit.get("notes", ""),
        ])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="medical_card_043u.xlsx"'
    workbook.save(response)
    return response


def mkb_s3_admin_view(request):
    """Админ-страница обновления справочника МКБ-С-3 и загрузки DLL."""
    token = request.session.get("token")
    role = request.session.get("role")
    if not token:
        return redirect("/login/")
    if role != "administrator":
        messages.error(request, "Доступ только для администратора")
        return redirect("/")

    headers = {"Authorization": f"Bearer {token}"}
    metadata = {}
    services_count = None
    data_path = (
        Path(__file__).resolve().parents[2]
        / "fastapi_app"
        / "app"
        / "data"
        / "mkb_s3_codes.json"
    )
    dll_path = (
        Path(__file__).resolve().parents[2]
        / "fastapi_app"
        / "app"
        / "dll"
        / "mkb_s3.dll"
    )

    def refresh_state():
        nonlocal metadata, services_count
        try:
            payload = json.loads(data_path.read_text(encoding="utf-8"))
        except Exception:
            payload = {}

        services = payload.get("services", [])
        services_count = len(services)

        dll_loaded = False
        if dll_path.exists():
            try:
                import ctypes
                ctypes.WinDLL(str(dll_path))
                dll_loaded = True
            except Exception:
                dll_loaded = False

        metadata = {
            "version": payload.get("version", "unknown"),
            "updated_at": payload.get("updated_at", ""),
            "source": "dll+json" if dll_loaded else "json",
            "dll_loaded": "yes" if dll_loaded else "no",
        }

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "reload":
            # Локальный reload без API: проверяем, что JSON читается и DLL загружается.
            try:
                _ = json.loads(data_path.read_text(encoding="utf-8"))
                if dll_path.exists():
                    import ctypes
                    ctypes.WinDLL(str(dll_path))
                messages.success(request, "Справочник перезагружен (локальная проверка)")
            except Exception as exc:
                messages.error(request, f"Ошибка reload: {exc}")

        elif action == "upload_json":
            json_file = request.FILES.get("json_file")
            json_text = request.POST.get("json_text", "").strip()
            payload = None

            try:
                if json_file:
                    payload = json.loads(json_file.read().decode("utf-8"))
                elif json_text:
                    payload = json.loads(json_text)
            except Exception as exc:
                messages.error(request, f"Некорректный JSON: {exc}")

            if payload:
                try:
                    data_path.parent.mkdir(parents=True, exist_ok=True)
                    data_path.write_text(
                        json.dumps(payload, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                    messages.success(request, "Справочник обновлен из JSON")
                except Exception as exc:
                    messages.error(request, f"Ошибка update: {exc}")

        elif action == "upload_dll":
            dll_file = request.FILES.get("dll_file")
            if not dll_file:
                messages.error(request, "Выберите файл DLL")
            else:
                try:
                    target = (
                        Path(__file__).resolve().parents[2]
                        / "fastapi_app"
                        / "app"
                        / "dll"
                        / "mkb_s3.dll"
                    )
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(dll_file.read())
                    import ctypes
                    ctypes.WinDLL(str(target))
                    messages.success(request, "DLL загружена и подключена")
                except Exception as exc:
                    messages.error(request, f"Ошибка сохранения DLL: {exc}")

    refresh_state()
    return render(
        request,
        "mkb_s3_admin.html",
        {"metadata": metadata, "services_count": services_count},
    )
