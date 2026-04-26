"""Работа со справочником МКБ-С-3 с поддержкой DLL и JSON-версий."""

from __future__ import annotations

import ctypes
import json
from pathlib import Path
from typing import Dict, List, Optional


class MKB_S3:
    def __init__(self) -> None:
        self.base_dir = Path(__file__).resolve().parent
        self.data_path = self.base_dir.parent / "data" / "mkb_s3_codes.json"
        self.dll_path = self.base_dir.parent / "dll" / "mkb_s3.dll"
        self._dll = None
        self._metadata: Dict[str, str] = {
            "version": "unknown",
            "source": "json",
            "updated_at": "",
        }
        self.services: List[Dict] = []
        self._diagnosis_keywords: Dict[str, List[str]] = {
            "кариес": ["K02.0", "K02.1", "K02.2"],
            "пульпит": ["K04.0", "K04.1"],
            "периодонтит": ["K05.2", "K05.3"],
            "гингивит": ["K05.0", "K05.1"],
            "удаление": ["K08.1"],
            "протез": ["K08.1"],
            "гигиена": ["Z01.2"],
            "консультация": ["Z01.2"],
        }
        self.reload()

    def _load_dll(self) -> bool:
        if not self.dll_path.exists():
            return False
        try:
            self._dll = ctypes.WinDLL(str(self.dll_path))
            self._metadata["source"] = "dll"
            return True
        except OSError:
            self._dll = None
            return False

    def _load_json(self) -> None:
        if not self.data_path.exists():
            raise FileNotFoundError(f"Файл справочника не найден: {self.data_path}")

        payload = json.loads(self.data_path.read_text(encoding="utf-8"))
        self._metadata["version"] = payload.get("version", "unknown")
        self._metadata["updated_at"] = payload.get("updated_at", "")
        if self._metadata.get("source") == "dll":
            self._metadata["source"] = "dll+json"
        else:
            self._metadata["source"] = "json"
        self.services = payload.get("services", [])

    def reload(self) -> None:
        # DLL интеграция подключена как первичный источник расширения.
        self._load_dll()
        self._load_json()

    def get_metadata(self) -> Dict[str, str]:
        return self._metadata

    def update_from_payload(self, payload: Dict) -> Dict[str, str]:
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        self.data_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.reload()
        return self.get_metadata()

    def get_all_codes(self) -> List[Dict]:
        return self.services

    def get_by_code(self, code: str) -> Optional[Dict]:
        code_upper = code.upper()
        for service in self.services:
            if service.get("code", "").upper() == code_upper:
                return service
        return None

    def search_by_name(self, query: str) -> List[Dict]:
        query_lower = query.lower().strip()
        if not query_lower:
            return self.services

        results = []
        for service in self.services:
            code = str(service.get("code", "")).lower()
            name = str(service.get("name", "")).lower()
            description = str(service.get("description", "")).lower()
            if query_lower in code or query_lower in name or query_lower in description:
                results.append(service)
        return results

    def suggest_services(self, diagnosis: str) -> List[Dict]:
        diagnosis_lower = diagnosis.lower()
        suggestions: List[Dict] = []
        suggested_codes = set()

        for keyword, codes in self._diagnosis_keywords.items():
            if keyword in diagnosis_lower:
                suggested_codes.update(codes)

        for code in suggested_codes:
            service = self.get_by_code(code)
            if service:
                suggestions.append(service)
        return suggestions


mkb_s3 = MKB_S3()