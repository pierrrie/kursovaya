"""
Библиотека для работы с Международной классификацией стоматологических болезней МКБ-С-3
"""
import json
from pathlib import Path
from typing import Dict, List, Optional

class MKB_S3:
    def __init__(self, data_file: str = "mkb_s3_data.json"):
        self.data = self._load_data(data_file)
    
    def _load_data(self, filename: str) -> Dict:
        # В реальном проекте здесь загрузка из файла или БД
        # Пример структуры данных:
        return {
            "K01": {
                "code": "K01",
                "name": "Кариес эмали",
                "description": "Начальный кариес в стадии пятна",
                "cost": 1500.0,
                "duration": 30
            },
            "K02": {
                "code": "K02",
                "name": "Кариес дентина",
                "description": "Средний кариес",
                "cost": 2500.0,
                "duration": 45
            },
            # ... другие коды
        }
    
    def get_by_code(self, code: str) -> Optional[Dict]:
        return self.data.get(code.upper())
    
    def search_by_name(self, name_part: str) -> List[Dict]:
        name_lower = name_part.lower()
        return [
            item for item in self.data.values()
            if name_lower in item["name"].lower()
        ]
    
    def get_all_codes(self) -> List[Dict]:
        return list(self.data.values())
    
    def validate_code(self, code: str) -> bool:
        return code.upper() in self.data
    
    def suggest_services(self, diagnosis: str) -> List[Dict]:
        """Предлагает услуги на основе диагноза"""
        # Простая логика сопоставления
        suggestions = []
        diagnosis_lower = diagnosis.lower()
        
        for item in self.data.values():
            if any(word in diagnosis_lower for word in item["name"].lower().split()):
                suggestions.append(item)
        
        return suggestions

# Синглтон для использования во всем приложении
mkb_s3 = MKB_S3()