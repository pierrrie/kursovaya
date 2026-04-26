import os
import time
import unittest
from datetime import datetime
from urllib.parse import urljoin

import requests
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait


BASE_URL = os.getenv("E2E_BASE_URL", "http://127.0.0.1:8000/")
WAIT_SECONDS = int(os.getenv("E2E_WAIT_SECONDS", "10"))
HEADLESS = os.getenv("E2E_HEADLESS", "1") == "1"


USERS = {
    "admin": {"email": "admin@test.local", "password": "admin123"},
    "manager": {"email": "manager@test.local", "password": "manager123"},
    "dentist": {"email": "dentist1@test.local", "password": "dentist123"},
}


class SeleniumE2ERoleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls._assert_servers_up()
            options = webdriver.ChromeOptions()
            if HEADLESS:
                options.add_argument("--headless=new")
            options.add_argument("--window-size=1440,1000")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            cls.driver = webdriver.Chrome(options=options)
            cls.wait = WebDriverWait(cls.driver, WAIT_SECONDS)
        except (WebDriverException, AssertionError, requests.RequestException) as exc:
            raise unittest.SkipTest(f"Selenium E2E skipped: {exc}")

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "driver"):
            cls.driver.quit()

    @classmethod
    def _assert_servers_up(cls):
        django = requests.get(urljoin(BASE_URL, "/login/"), timeout=3)
        if django.status_code != 200:
            raise AssertionError(f"Django login page unavailable: {django.status_code}")

    def setUp(self):
        self.driver.delete_all_cookies()

    # --- helpers ---
    def open(self, path: str):
        self.driver.get(urljoin(BASE_URL, path))

    def login_as(self, role: str):
        creds = USERS[role]
        self.open("/login/")
        self.wait.until(EC.presence_of_element_located((By.NAME, "email"))).clear()
        self.driver.find_element(By.NAME, "email").send_keys(creds["email"])
        self.driver.find_element(By.NAME, "password").clear()
        self.driver.find_element(By.NAME, "password").send_keys(creds["password"])
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))
        self.assertIn("/patients/", self.driver.current_url)

    def logout(self):
        self.open("/logout/")
        self.wait.until(EC.presence_of_element_located((By.NAME, "email")))

    def assert_has_text(self, text: str):
        self.assertIn(text, self.driver.page_source)

    def assert_link_exists(self, href: str):
        self.driver.find_element(By.CSS_SELECTOR, f"a[href='{href}']")

    def _select_first_option(self, select_name: str):
        select = Select(self.driver.find_element(By.NAME, select_name))
        if len(select.options) < 2:
            self.fail(f"Not enough options in select '{select_name}'")
        select.select_by_index(1)

    # --- tests by role and required features ---
    def test_admin_accesses_admin_functions_and_mkb_page(self):
        self.login_as("admin")
        self.assert_has_text("Ваша роль")
        self.assert_link_exists("/settings/create-user/")
        self.assert_link_exists("/settings/mkb-s3/")

        self.open("/settings/mkb-s3/")
        self.assert_has_text("Управление МКБ-С-3")
        self.assert_has_text("Текущее состояние")
        self.driver.find_element(By.CSS_SELECTOR, "input[name='json_file']")
        self.driver.find_element(By.CSS_SELECTOR, "input[name='dll_file']")

    def test_manager_patient_crud_and_visit_date_search_ui(self):
        self.login_as("manager")
        self.open("/patients/")

        # Search patients by visit date
        self.driver.find_element(By.NAME, "visit_date").send_keys("2026-04-25")
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table")))
        self.assert_has_text("Поиск по дате посещения")

        # Create patient
        self.open("/patients/create/")
        stamp = datetime.now().strftime("%H%M%S")
        self.driver.find_element(By.NAME, "last_name").send_keys(f"E2E{stamp}")
        self.driver.find_element(By.NAME, "first_name").send_keys("Manager")
        self.driver.find_element(By.NAME, "middle_name").send_keys("Test")
        self.driver.find_element(By.NAME, "birth_date").send_keys("01.01.1990")
        self.driver.find_element(By.NAME, "phone").send_keys("+70000000000")
        self.driver.find_element(By.NAME, "address").send_keys("E2E address")
        self.driver.find_element(By.NAME, "allergies").send_keys("нет")
        self.driver.find_element(By.NAME, "note").send_keys("created by selenium")
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table")))
        self.assert_has_text("Пациенты")

        # Check delete control exists for manager
        self.driver.find_element(By.XPATH, "//button[contains(text(),'Удалить')]")

    def test_manager_can_open_appointment_create_flow(self):
        self.login_as("manager")
        self.open("/appointments/create/")
        self.assert_has_text("Создать запись на прием")
        self.driver.find_element(By.ID, "patient_id")
        self.driver.find_element(By.ID, "doctor_id")
        self.driver.find_element(By.ID, "datetime")

    def test_dentist_can_open_diary_documents_and_forms(self):
        self.login_as("dentist")

        # Diary and its core actions
        self.open("/dentist-diary/")
        self.assert_has_text("Дневник врача")
        self.assert_link_exists("/appointments/create/")
        self.assert_link_exists("/visits/create/")
        self.assert_link_exists("/dentist-documents/referrals/")
        self.assert_link_exists("/dentist-documents/patient-history/")
        self.assert_link_exists("/dentist-documents/medical-card/")
        self.assert_link_exists("/dentist-documents/work-orders/")

        # Visit form (results of examination and treatment info)
        self.open("/visits/create/")
        self.driver.find_element(By.NAME, "patient_id")
        self.driver.find_element(By.NAME, "complaints")
        self.driver.find_element(By.NAME, "anamnesis")
        self.driver.find_element(By.NAME, "diagnosis")
        self.driver.find_element(By.NAME, "exam_results")
        self.driver.find_element(By.NAME, "notes")

        # Referral creation
        self.open("/dentist-documents/referrals/create/")
        self.driver.find_element(By.NAME, "patient_id")
        self.driver.find_element(By.NAME, "referral_type")
        self.driver.find_element(By.NAME, "destination")
        self.driver.find_element(By.NAME, "reason")

        # Work order creation
        self.open("/dentist-documents/work-orders/create/")
        self.driver.find_element(By.NAME, "visit_id")
        self.driver.find_element(By.NAME, "description")
        self.driver.find_element(By.NAME, "materials")
        self.driver.find_element(By.NAME, "tooth_numbers")

    def test_dentist_can_generate_medical_docs_with_word_excel_links(self):
        self.login_as("dentist")

        # Patient history generation + Word link
        self.open("/dentist-documents/patient-history/")
        self._select_first_option("patient_id")
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))
        self.assert_has_text("Выписка из медицинской карты")
        self.driver.find_element(By.XPATH, "//a[contains(@href,'/api/documents/patient-history/') and contains(@href,'/word')]")

        # Medical card generation + Word/Excel links
        self.open("/dentist-documents/medical-card/")
        self._select_first_option("patient_id")
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))
        self.assert_has_text("Медицинская карта стоматологического больного")
        self.driver.find_element(By.XPATH, "//a[contains(@href,'/api/documents/medical-card/') and contains(@href,'/word')]")
        self.driver.find_element(By.XPATH, "//a[contains(@href,'/api/documents/medical-card/') and contains(@href,'/excel')]")

    def test_visit_date_search_available_on_visits_page(self):
        self.login_as("dentist")
        self.open("/visits/")
        self.driver.find_element(By.NAME, "date_from")
        self.driver.find_element(By.NAME, "date_to")
        self.assert_has_text("Искать по дате посещения")


if __name__ == "__main__":
    unittest.main(verbosity=2)
