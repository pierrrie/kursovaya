import requests

# Протестируем создание работы для стоматолога
API_URL = 'http://127.0.0.8:8000'

# Сначала войдем как стоматолог
login_data = {'username': 'vrach@mail.ru', 'password': 'dentist123'}
resp = requests.post(f'{API_URL}/auth/login', data=login_data)
token = resp.json().get('access_token')
headers = {'Authorization': f'Bearer {token}'}

print(f'Login successful, token: {token[:20]}...')

# Создадим работу для визита 2
work_data = {
    'description': 'Тестовая работа',
    'materials': 'Тестовые материалы',
    'tooth_numbers': '12,13',
    'duration_minutes': 30
}

resp_work = requests.post(f'{API_URL}/works/visit/2', json=work_data, headers=headers)
print(f'Create work response: {resp_work.status_code}')
print(f'Create work data: {resp_work.text}')

# Теперь получим все работы
resp_works = requests.get(f'{API_URL}/works/', headers=headers)
print(f'Get works response: {resp_works.status_code}')
works = resp_works.json()
print(f'Works count: {len(works)}')
for work in works:
    print(f'  Work {work["id"]}: {work["description"][:30]}...')