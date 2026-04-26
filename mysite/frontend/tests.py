from unittest.mock import patch

from django.test import Client, TestCase


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload if payload is not None else []
        self.text = text
        self.content = b""

    def json(self):
        return self._payload


class FrontendViewsTests(TestCase):
    def setUp(self):
        self.client = Client()

    def _set_session(self, token="test-token", role="manager"):
        session = self.client.session
        session["token"] = token
        session["role"] = role
        session.save()

    @patch("frontend.views.requests.get")
    def test_patients_search_by_visit_date_uses_filter_endpoint(self, mock_get):
        self._set_session()
        mock_get.return_value = FakeResponse(status_code=200, payload=[])

        response = self.client.get("/patients/?visit_date=2026-04-25")

        self.assertEqual(response.status_code, 200)
        args, kwargs = mock_get.call_args
        self.assertIn("/patients/by-visit-date/", args[0])
        self.assertEqual(kwargs["params"]["visit_date"], "2026-04-25")

    @patch("frontend.views.requests.delete")
    def test_patient_delete_forbidden_for_dentist(self, mock_delete):
        self._set_session(role="dentist")
        response = self.client.post("/patients/1/delete/")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/patients/")
        mock_delete.assert_not_called()

    @patch("frontend.views.requests.get")
    def test_download_medical_card_excel_returns_xlsx(self, mock_get):
        self._set_session(role="dentist")
        mock_get.return_value = FakeResponse(
            status_code=200,
            payload={
                "patient": {
                    "full_name": "Тест Пациент",
                    "birth_date": "1990-01-01",
                    "phone": "+70000000000",
                    "address": "г. Тест",
                    "allergies": "нет",
                },
                "tooth_formula": {"11": {"status": "здоров", "notes": ""}},
                "visits": [],
            },
        )

        response = self.client.get("/api/documents/medical-card/1/excel")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertIn("medical_card_043u.xlsx", response["Content-Disposition"])

    def test_mkb_s3_admin_requires_admin_role(self):
        self._set_session(role="manager")
        response = self.client.get("/settings/mkb-s3/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/")
