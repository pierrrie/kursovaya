from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.mkb_s3 import mkb_s3

router = APIRouter()

@router.get("/codes")
async def get_all_codes():
    return mkb_s3.get_all_codes()

@router.get("/codes/{code}")
async def get_code(code: str):
    result = mkb_s3.get_by_code(code)
    if not result:
        raise HTTPException(status_code=404, detail="Код не найден")
    return result

@router.get("/search")
async def search_codes(name: str):
    return mkb_s3.search_by_name(name)

@router.get("/suggest")
async def suggest_services(diagnosis: str):
    return mkb_s3.suggest_services(diagnosis)