# app/api/mkb_s3_api.py
from fastapi import APIRouter, HTTPException
from typing import List
from app.mkb_s3 import mkb_s3

router = APIRouter()

@router.get("/services", operation_id="get_all_mkb_s3_services")
async def get_all_services():
    """Получить все услуги по МКБ-С-3"""
    # Метод называется get_all_codes, а не get_all_services
    return mkb_s3.get_all_codes()  # Изменил!

@router.get("/services/{code}", operation_id="get_mkb_s3_service_by_code")
async def get_service_by_code(code: str):
    """Получить услугу по коду"""
    # Метод называется get_by_code, а не get_service_by_code
    service = mkb_s3.get_by_code(code)  # Изменил!
    if not service:
        raise HTTPException(status_code=404, detail="Услуга не найдена")
    return service

@router.get("/search/{query}", operation_id="search_mkb_s3_services")
async def search_services(query: str):
    """Поиск услуг"""
    # Метод называется search_by_name, а не search_services
    return mkb_s3.search_by_name(query)  # Изменил!

@router.get("/suggest/{diagnosis}", operation_id="suggest_mkb_s3_services")
async def suggest_services_by_diagnosis(diagnosis: str):
    """Подобрать услуги на основе диагноза"""
    return mkb_s3.suggest_services(diagnosis)