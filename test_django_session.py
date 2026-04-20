import requests
import re

# Создадим сессию для тестирования Django
session = requests.Session()

# Сначала получим страницу логина для CSRF токена
resp_login_page = session.get('http://127.0.0.1:8001/login/')
print(f"Login page response: {resp_login_page.status_code}")

# Найдем CSRF токен в HTML
csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', resp_login_page.text)
csrf_token = csrf_match.group(1) if csrf_match else None
print(f"CSRF token: {csrf_token}")

# Теперь войдем в Django с CSRF токеном
login_data = {
    'email': 'vrach@mail.ru',
    'password': 'dentist123',
    'csrfmiddlewaretoken': csrf_token
}
resp_login = session.post('http://127.0.0.1:8001/login/', data=login_data, headers={'Referer': 'http://127.0.0.1:8001/login/'})
print(f"Login response: {resp_login.status_code}")
print(f"Login redirect: {resp_login.url}")

# Проверим сессию
resp_check = session.get('http://127.0.0.1:8001/dentist-documents/work-orders/')
print(f"Works page after login response: {resp_check.status_code}")

# Посмотрим на контент
if "Наряды на выполнение работ" in resp_check.text:
    print("SUCCESS: Works page title found")
    if "Нет нарядов" in resp_check.text or "нарядов не найдено" in resp_check.text:
        print("INFO: No works found message")
    elif "<table" in resp_check.text:
        print("SUCCESS: Works table found")
        # Посчитаем количество строк в таблице
        import re
        table_rows = len(re.findall(r'<tr>', resp_check.text))
        print(f"Table has {table_rows} rows")
    else:
        print("WARNING: No table or no works message found")
else:
    print("ERROR: Works page not loaded properly")
    if "Только стоматолог может управлять нарядами" in resp_check.text:
        print("ERROR: Authentication failed")
    else:
        print("Page content preview:", resp_check.text[:500])