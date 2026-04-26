from django.urls import path
from . import views

urlpatterns = [
    path("documents/patient-history/<int:patient_id>/word", views.download_patient_history_word, name="download_patient_history_word"),
    path("documents/medical-card/<int:patient_id>/word", views.download_medical_card_word, name="download_medical_card_word"),
    path("documents/medical-card/<int:patient_id>/excel", views.download_medical_card_excel, name="download_medical_card_excel"),
]