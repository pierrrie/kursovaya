import requests

# Получим правильный токен стоматолога
API_URL = "http://127.0.0.8:8000"
login_data = {"username": "vrach@mail.ru", "password": "dentist123"}
resp = requests.post(f"{API_URL}/auth/login", data=login_data)
token = resp.json().get("access_token")

print(f"Real token: {token}")

# Теперь протестируем API работ с этим токеном
headers = {"Authorization": f"Bearer {token}"}
resp_works = requests.get(f"{API_URL}/works/", headers=headers)
print(f"Works API response: {resp_works.status_code}")
works = resp_works.json()
print(f"Number of works: {len(works)}")

# Также протестируем получение визитов
resp_visits = requests.get(f"{API_URL}/visits/?date_from=2026-04-01", headers=headers)
print(f"Visits API response: {resp_visits.status_code}")
visits = resp_visits.json()
print(f"Number of visits: {len(visits)}")