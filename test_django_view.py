import os
import django
import requests
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
django.setup()

from frontend.views import dentist_work_orders_view

# Создадим тестовый запрос
factory = RequestFactory()
request = factory.get('/dentist-documents/work-orders/')

# Добавим сессию
middleware = SessionMiddleware()
middleware.process_request(request)
request.session.save()

# Установим токен и роль стоматолога
request.session['token'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ2cmFjaEBtYWlsLnJ1Iiwicm9sZSI6ImRlbnRpc3QiLCJleHAiOjE3NDUwMDM0NzR9.example'  # неправильный токен для теста
request.session['role'] = 'dentist'

print("Testing dentist_work_orders_view...")
try:
    response = dentist_work_orders_view(request)
    print(f"Response status: {response.status_code}")
    if hasattr(response, 'content'):
        print(f"Response content length: {len(response.content)}")
except Exception as e:
    print(f"Error: {e}")