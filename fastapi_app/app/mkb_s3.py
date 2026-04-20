# app/mkb_s3.py
"""
Библиотека для работы с Международной классификацией стоматологических болезней МКБ-С-3
"""
import json
from typing import Dict, List, Optional

class MKB_S3:
    def __init__(self):
        # Пример данных МКБ-С-3
        self.services = [
            {
                "code": "К01.0",
                "name": "Первичный осмотр и консультация",
                "description": "Осмотр полости рта, сбор анамнеза, консультация",
                "duration": 30,
                "cost": 1500.0
            },
            {
                "code": "К02.1",
                "name": "Лечение кариеса поверхностного",
                "description": "Препарирование и пломбирование кариозной полости I, V класса по Блэку",
                "duration": 40,
                "cost": 3500.0
            },
            {
                "code": "К02.2",
                "name": "Лечение кариеса среднего",
                "description": "Лечение кариеса дентина",
                "duration": 60,
                "cost": 4500.0
            },
            {
                "code": "К04.0",
                "name": "Эндодонтическое лечение одноканального зуба",
                "description": "Лечение пульпита, периодонтита (механическая и медикаментозная обработка канала, пломбирование)",
                "duration": 90,
                "cost": 8000.0
            },
            {
                "code": "К05.1",
                "name": "Профессиональная гигиена полости рта",
                "description": "Снятие зубных отложений, полировка",
                "duration": 60,
                "cost": 4000.0
            },
            {
                "code": "К08.1",
                "name": "Удаление зуба простое",
                "description": "Удаление зуба без разрезов",
                "duration": 30,
                "cost": 3000.0
            },
            {
                "code": "К08.2",
                "name": "Удаление зуба сложное",
                "description": "Удаление ретенированного, дистопированного зуба",
                "duration": 60,
                "cost": 6000.0
            }
        ]
    
    def get_all_codes(self) -> List[Dict]:
        """Получить все услуги по МКБ-С-3"""
        return self.services
    
    def get_by_code(self, code: str) -> Optional[Dict]:
        """Найти услугу по коду"""
        for service in self.services:
            if service["code"] == code:
                return service
        return None
    
    def search_by_name(self, query: str) -> List[Dict]:
        """Поиск услуг по названию или описанию"""
        query_lower = query.lower()
        results = []
        for service in self.services:
            if (query_lower in service["name"].lower() or 
                query_lower in service.get("description", "").lower() or
                query_lower in service["code"].lower()):
                results.append(service)
        return results
    
    def suggest_services(self, diagnosis: str) -> List[Dict]:
        """Подобрать услуги на основе диагноза"""
        diagnosis_lower = diagnosis.lower()
        suggestions = []
        
        # Простая логика сопоставления диагноза с услугами
        diagnosis_keywords = {
            "кариес": ["К02.1", "К02.2"],
            "пульпит": ["К04.0"],
            "периодонтит": ["К04.0"],
            "гигиена": ["К05.1"],
            "удаление": ["К08.1", "К08.2"]
        }
        
        for keyword, codes in diagnosis_keywords.items():
            if keyword in diagnosis_lower:
                for code in codes:
                    service = self.get_by_code(code)
                    if service:
                        suggestions.append(service)
        
        return suggestions

# Глобальный экземпляр для использования
mkb_s3 = MKB_S3()