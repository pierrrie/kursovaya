import requests

API_URL = "http://127.0.0.8:8000"

# Сначала получим токен для стоматолога
login_data = {"username": "vrach@mail.ru", "password": "dentist123"}
resp = requests.post(f"{API_URL}/auth/login", data=login_data)
print(f"Login response: {resp.status_code}")
if resp.status_code == 200:
    token = resp.json().get("access_token")
    print(f"Got token: {token[:20]}...")
    
    # Теперь получим работы
    headers = {"Authorization": f"Bearer {token}"}
    resp_works = requests.get(f"{API_URL}/works/", headers=headers)
    print(f"Works response: {resp_works.status_code}")
    print(f"Works data: {resp_works.text}")
else:
    print(f"Login failed: {resp.text}")