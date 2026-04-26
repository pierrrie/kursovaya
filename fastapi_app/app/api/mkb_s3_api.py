# app/api/mkb_s3_api.py
from fastapi import APIRouter, HTTPException
from typing import Dict
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


@router.get("/metadata")
async def get_mkb_s3_metadata() -> Dict[str, str]:
    """Получить метаданные загруженного справочника"""
    return mkb_s3.get_metadata()


@router.post("/reload")
async def reload_mkb_s3_data():
    """Перечитать справочник из файла/доступной DLL"""
    try:
        mkb_s3.reload()
        return {"status": "ok", "metadata": mkb_s3.get_metadata()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ошибка reload: {exc}") from exc


@router.post("/update")
async def update_mkb_s3_data(payload: Dict):
    """
    Обновить справочник из JSON payload.
    Ожидается структура:
    {
      "version": "...",
      "updated_at": "...",
      "services": [ ... ]
    }
    """
    if "services" not in payload or not isinstance(payload["services"], list):
        raise HTTPException(status_code=400, detail="Поле 'services' должно быть списком")
    meta = mkb_s3.update_from_payload(payload)
    return {"status": "ok", "metadata": meta}