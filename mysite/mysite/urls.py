from django.urls import path, include
from django.contrib import admin
from django.urls import path

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", include("frontend.urls")),
    path("api/", include("frontend.api_urls")),  # Добавляем API URLs
]
