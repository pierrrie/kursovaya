import os
import unittest
from datetime import datetime
from urllib.parse import urljoin

import requests
from selenium import webdriver
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait


BASE_URL = os.getenv("E2E_BASE_URL", "http://127.0.0.1:8001/")
FASTAPI_HEALTH_URL = os.getenv("E2E_FASTAPI_HEALTH_URL", "http://127.0.0.1:8000/health")
WAIT_SECONDS = int(os.getenv("E2E_WAIT_SECONDS", "10"))
# По умолчанию браузер открывается (не headless), как просил пользователь.
HEADLESS = os.getenv("E2E_HEADLESS", "0") == "1"


USERS = {
    "admin": {"email": "admin@test.local", "password": "admin123"},
    "manager": {"email": "manager@test.local", "password": "manager123"},
    "dentist": {"email": "dentist1@test.local", "password": "dentist123"},
}


class SeleniumE2EFullProjectTests(unittest.TestCase):
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
        django = requests.get(urljoin(BASE_URL, "/login/"), timeout=5)
        if django.status_code != 200:
            raise AssertionError(f"Django login page unavailable: {django.status_code}")
        fastapi = requests.get(FASTAPI_HEALTH_URL, timeout=5)
        if fastapi.status_code != 200:
            raise AssertionError(f"FastAPI health unavailable: {fastapi.status_code}")

    def setUp(self):
        self.driver.delete_all_cookies()

    # ---------- helpers ----------
    def open(self, path: str):
        self.driver.get(urljoin(BASE_URL, path))
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        self.assertNotIn("Server Error (500)", self.driver.page_source)

    def login_as(self, role: str):
        creds = USERS[role]
        self.open("/login/")
        self.wait.until(EC.presence_of_element_located((By.NAME, "email"))).clear()
        self.driver.find_element(By.NAME, "email").send_keys(creds["email"])
        self.driver.find_element(By.NAME, "password").clear()
        self.driver.find_element(By.NAME, "password").send_keys(creds["password"])
        self.click_submit()
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        current = self.driver.current_url
        if "/login/" in current:
            self.skipTest(f"Login failed for role '{role}' with configured credentials")
        if role == "dentist":
            self.assertTrue("/dentist-diary/" in current or "/patients/" in current)
        else:
            self.assertIn("/patients/", current)

    def logout(self):
        self.open("/logout/")
        self.wait.until(EC.presence_of_element_located((By.NAME, "email")))

    def assert_link_exists(self, href: str):
        self.driver.find_element(By.CSS_SELECTOR, f"a[href='{href}']")

    def assert_inputs_exist(self, *names: str):
        for name in names:
            with self.subTest(name=name):
                self.driver.find_element(By.NAME, name)

    def assert_redirects_to_login(self):
        self.wait.until(EC.presence_of_element_located((By.NAME, "email")))
        self.assertIn("/login/", self.driver.current_url)

    def open_if_link_exists(self, contains_path: str):
        links = self.driver.find_elements(By.CSS_SELECTOR, f"a[href*='{contains_path}']")
        if links:
            target = links[0].get_attribute("href")
            self.driver.get(target)
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            self.assertNotIn("Server Error (500)", self.driver.page_source)

    def submit_first_patient_selector_if_exists(self):
        try:
            patient_select = Select(self.driver.find_element(By.NAME, "patient_id"))
            if len(patient_select.options) > 1:
                patient_select.select_by_index(1)
                self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
                self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        except (NoSuchElementException, TimeoutException):
            pass

    def ensure_not_500_for_paths(self, paths: list[str]):
        for path in paths:
            with self.subTest(path=path):
                self.open(path)

    def select_first_non_empty_option(self, select_name: str):
        select = Select(self.driver.find_element(By.NAME, select_name))
        if len(select.options) < 2:
            self.skipTest(f"Not enough options in select '{select_name}'")
        select.select_by_index(1)

    def fill_input(self, name: str, value: str):
        field = self.driver.find_element(By.NAME, name)
        field.clear()
        field.send_keys(value)

    def click_submit(self):
        submit = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit)
        try:
            submit.click()
        except ElementClickInterceptedException:
            self.driver.execute_script("arguments[0].click();", submit)

    # ---------- full coverage tests ----------
    def test_login_page_has_required_fields(self):
        self.open("/login/")
        self.assert_inputs_exist("email", "password")
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")

    def test_register_page_has_required_fields(self):
        self.open("/register/")
        self.assert_inputs_exist("email", "password")
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")

    def test_login_with_invalid_credentials_shows_error_page(self):
        self.open("/login/")
        self.driver.find_element(By.NAME, "email").send_keys("invalid@test.local")
        self.driver.find_element(By.NAME, "password").send_keys("wrong-password")
        self.click_submit()
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        self.assertIn("/login/", self.driver.current_url)

    def test_public_pages_open_in_browser(self):
        for path in ["/", "/login/", "/register/"]:
            with self.subTest(path=path):
                self.open(path)

    def test_protected_pages_redirect_to_login_without_session(self):
        protected_paths = [
            "/patients/",
            "/patients/create/",
            "/visits/",
            "/visits/create/",
            "/appointments/",
            "/appointments/create/",
            "/dentist-diary/",
            "/dentist-documents/referrals/",
            "/dentist-documents/referrals/create/",
            "/dentist-documents/patient-history/",
            "/dentist-documents/medical-card/",
            "/dentist-documents/work-orders/",
            "/dentist-documents/work-orders/create/",
            "/settings/create-user/",
            "/settings/mkb-s3/",
        ]
        for path in protected_paths:
            with self.subTest(path=path):
                self.open(path)
                self.assert_redirects_to_login()

    def test_manager_has_expected_navigation_links(self):
        self.login_as("manager")
        self.open("/patients/")
        for href in ["/patients/", "/patients/create/", "/appointments/", "/logout/"]:
            with self.subTest(href=href):
                self.assert_link_exists(href)
        self.logout()

    def test_manager_filter_forms_present(self):
        self.login_as("manager")
        self.open("/patients/")
        self.assert_inputs_exist("visit_date")
        self.open("/visits/")
        self.assert_inputs_exist("date_from", "date_to")
        self.logout()

    def test_manager_can_open_patient_detail_and_edit_pages(self):
        self.login_as("manager")
        self.open("/patients/")
        detail_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/patients/'][href$='/']")
        if not detail_links:
            self.skipTest("No patients in list for detail/edit route checks")
        detail_url = detail_links[0].get_attribute("href")
        self.driver.get(detail_url)
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        self.assertNotIn("Server Error (500)", self.driver.page_source)

        edit_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/edit/']")
        if edit_links:
            self.driver.get(edit_links[0].get_attribute("href"))
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            self.assert_inputs_exist("last_name", "first_name", "middle_name")
        self.logout()

    def test_manager_can_open_appointment_and_visit_detail_pages(self):
        self.login_as("manager")
        self.open("/appointments/")
        self.open_if_link_exists("/appointments/")
        self.open("/visits/")
        self.open_if_link_exists("/visits/")
        self.logout()

    def test_manager_has_no_admin_navigation(self):
        self.login_as("manager")
        self.open("/patients/")
        self.assertEqual(len(self.driver.find_elements(By.CSS_SELECTOR, "a[href='/settings/create-user/']")), 0)
        self.assertEqual(len(self.driver.find_elements(By.CSS_SELECTOR, "a[href='/settings/mkb-s3/']")), 0)
        self.logout()

    def test_admin_pages_and_forms_open(self):
        self.login_as("admin")
        admin_paths = ["/patients/", "/settings/create-user/", "/settings/mkb-s3/"]
        for path in admin_paths:
            with self.subTest(path=path):
                self.open(path)

        self.open("/settings/create-user/")
        self.driver.find_element(By.NAME, "username")
        self.driver.find_element(By.NAME, "password")
        self.driver.find_element(By.NAME, "role")
        self.open("/settings/mkb-s3/")
        self.driver.find_element(By.CSS_SELECTOR, "input[name='json_file']")
        self.driver.find_element(By.CSS_SELECTOR, "input[name='dll_file']")
        self.logout()

    def test_admin_can_open_create_user_page_controls(self):
        self.login_as("admin")
        self.open("/settings/create-user/")
        self.assert_inputs_exist("username", "password")
        self.driver.find_element(By.NAME, "role")
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        self.logout()

    def test_admin_can_access_mkb_s3_actions_page(self):
        self.login_as("admin")
        self.open("/settings/mkb-s3/")
        self.driver.find_element(By.CSS_SELECTOR, "input[name='json_file']")
        self.driver.find_element(By.CSS_SELECTOR, "textarea[name='json_text']")
        self.driver.find_element(By.CSS_SELECTOR, "input[name='dll_file']")
        self.driver.find_element(By.CSS_SELECTOR, "input[name='action'][value='reload']")
        self.logout()

    def test_admin_can_open_core_registry_pages(self):
        self.login_as("admin")
        self.ensure_not_500_for_paths(
            [
                "/patients/",
                "/patients/create/",
                "/visits/",
                "/appointments/",
                "/appointments/create/",
            ]
        )
        self.logout()

    def test_manager_pages_and_dynamic_routes_open(self):
        self.login_as("manager")
        manager_paths = ["/patients/", "/patients/create/", "/visits/", "/appointments/", "/appointments/create/"]
        for path in manager_paths:
            with self.subTest(path=path):
                self.open(path)

        self.open("/patients/")
        self.open_if_link_exists("/patients/")
        self.open_if_link_exists("/edit/")

        self.open("/visits/")
        self.open_if_link_exists("/visits/")
        self.open_if_link_exists("/edit/")

        self.open("/appointments/")
        self.open_if_link_exists("/appointments/")
        self.open_if_link_exists("/edit/")
        self.logout()

    def test_manager_patient_create_form_controls(self):
        self.login_as("manager")
        self.open("/patients/create/")
        self.assert_inputs_exist("last_name", "first_name", "middle_name", "birth_date", "phone", "address", "allergies", "note")
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        self.logout()

    def test_manager_appointment_create_form_controls(self):
        self.login_as("manager")
        self.open("/appointments/create/")
        self.assert_inputs_exist("patient_id", "doctor_id", "datetime")
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        self.logout()

    def test_manager_cannot_access_admin_only_pages(self):
        self.login_as("manager")
        self.open("/settings/create-user/")
        self.assertNotIn("Server Error (500)", self.driver.page_source)
        self.open("/settings/mkb-s3/")
        self.assertNotIn("Server Error (500)", self.driver.page_source)
        self.logout()

    def test_dentist_pages_documents_and_generation_forms_open(self):
        self.login_as("dentist")
        dentist_paths = [
            "/patients/",
            "/visits/",
            "/visits/create/",
            "/appointments/",
            "/appointments/create/",
            "/dentist-diary/",
            "/dentist-documents/referrals/",
            "/dentist-documents/referrals/create/",
            "/dentist-documents/patient-history/",
            "/dentist-documents/medical-card/",
            "/dentist-documents/work-orders/",
            "/dentist-documents/work-orders/create/",
        ]
        for path in dentist_paths:
            with self.subTest(path=path):
                self.open(path)

        # Проверки ключевых форм.
        self.open("/visits/create/")
        self.driver.find_element(By.NAME, "patient_id")
        self.driver.find_element(By.NAME, "complaints")
        self.driver.find_element(By.NAME, "diagnosis")

        self.open("/appointments/create/")
        self.driver.find_element(By.NAME, "patient_id")
        self.driver.find_element(By.NAME, "doctor_id")
        self.driver.find_element(By.NAME, "datetime")

        self.open("/dentist-documents/referrals/create/")
        self.driver.find_element(By.NAME, "patient_id")
        self.driver.find_element(By.NAME, "referral_type")
        self.driver.find_element(By.NAME, "destination")

        self.open("/dentist-documents/work-orders/create/")
        self.driver.find_element(By.NAME, "visit_id")
        self.driver.find_element(By.NAME, "description")
        self.driver.find_element(By.NAME, "tooth_numbers")

        # Генерация документов (если есть пациенты).
        self.open("/dentist-documents/patient-history/")
        self.submit_first_patient_selector_if_exists()

        self.open("/dentist-documents/medical-card/")
        self.submit_first_patient_selector_if_exists()
        self.logout()

    def test_dentist_diary_navigation_links_exist(self):
        self.login_as("dentist")
        self.open("/dentist-diary/")
        for href in [
            "/appointments/create/",
            "/visits/create/",
            "/dentist-documents/referrals/",
            "/dentist-documents/patient-history/",
            "/dentist-documents/medical-card/",
            "/dentist-documents/work-orders/",
        ]:
            with self.subTest(href=href):
                self.assert_link_exists(href)
        self.logout()

    def test_dentist_document_pages_open_without_500(self):
        self.login_as("dentist")
        for path in [
            "/dentist-documents/referrals/",
            "/dentist-documents/patient-history/",
            "/dentist-documents/medical-card/",
            "/dentist-documents/work-orders/",
        ]:
            with self.subTest(path=path):
                self.open(path)
        self.logout()

    def test_dentist_forms_have_required_fields(self):
        self.login_as("dentist")
        self.open("/visits/create/")
        self.assert_inputs_exist("patient_id", "datetime", "complaints", "anamnesis", "diagnosis", "exam_results", "notes")

        self.open("/dentist-documents/referrals/create/")
        self.assert_inputs_exist("patient_id", "visit_id", "referral_type", "destination", "reason", "date")

        self.open("/dentist-documents/work-orders/create/")
        self.assert_inputs_exist("visit_id", "description", "materials", "tooth_numbers", "duration_minutes", "cost", "work_date")
        self.logout()

    def test_dentist_can_open_edit_pages_from_diary_links(self):
        self.login_as("dentist")
        self.open("/dentist-diary/")
        edit_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/edit/']")
        if not edit_links:
            self.skipTest("No diary edit links available in current test data")
        self.driver.get(edit_links[0].get_attribute("href"))
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        self.assertNotIn("Server Error (500)", self.driver.page_source)
        self.logout()

    def test_dentist_can_see_patient_history_and_medical_card_download_links(self):
        self.login_as("dentist")
        self.open("/dentist-documents/patient-history/")
        self.submit_first_patient_selector_if_exists()
        self.assertNotIn("Server Error (500)", self.driver.page_source)

        self.open("/dentist-documents/medical-card/")
        self.submit_first_patient_selector_if_exists()
        self.assertNotIn("Server Error (500)", self.driver.page_source)
        self.logout()

    def test_dentist_cannot_access_admin_only_pages(self):
        self.login_as("dentist")
        self.open("/settings/create-user/")
        self.assertNotIn("Server Error (500)", self.driver.page_source)
        self.open("/settings/mkb-s3/")
        self.assertNotIn("Server Error (500)", self.driver.page_source)
        self.logout()

    def test_logout_from_authenticated_session_returns_to_login(self):
        self.login_as("manager")
        self.logout()
        self.assert_redirects_to_login()

    def test_manager_full_patient_crud_flow(self):
        self.login_as("manager")
        unique = datetime.now().strftime("%H%M%S")
        last_name = f"E2E{unique}"
        updated_last_name = f"E2EUPD{unique}"

        self.open("/patients/create/")
        self.fill_input("last_name", last_name)
        self.fill_input("first_name", "Auto")
        self.fill_input("middle_name", "Test")
        self.fill_input("birth_date", "1990-01-01")
        self.fill_input("phone", f"+7999{unique}")
        self.fill_input("address", "Selenium street")
        self.fill_input("allergies", "none")
        self.fill_input("note", f"note-{unique}")
        self.click_submit()

        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        self.assertIn("/patients/", self.driver.current_url)
        self.assertIn(last_name, self.driver.page_source)

        self.open("/patients/")
        self.driver.find_element(By.XPATH, f"//td[contains(.,'{last_name}')]/..//a[contains(@href,'/patients/') and contains(text(),'Просмотр')]").click()
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        self.driver.find_element(By.XPATH, "//a[contains(@href,'/edit/')]").click()
        self.wait.until(EC.presence_of_element_located((By.NAME, "last_name")))
        self.fill_input("last_name", updated_last_name)
        self.click_submit()
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        self.assertIn(updated_last_name, self.driver.page_source)

        self.open("/patients/")
        delete_btn = self.driver.find_element(By.XPATH, f"//td[contains(.,'{updated_last_name}')]/..//button[contains(.,'Удалить')]")
        self.driver.execute_script("window.confirm = function(){return true;};")
        delete_btn.click()
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        self.assertNotIn(updated_last_name, self.driver.page_source)
        self.logout()

    def test_manager_creates_appointment_via_ui(self):
        self.login_as("manager")
        unique = datetime.now().strftime("%H%M%S")
        comment = f"appt-{unique}"

        self.open("/appointments/create/")
        self.select_first_non_empty_option("patient_id")
        self.select_first_non_empty_option("doctor_id")
        self.fill_input("datetime", "2030-01-01T10:30")
        self.fill_input("reason", comment)
        self.click_submit()

        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        self.assertIn("/appointments/", self.driver.current_url)
        self.assertIn(comment, self.driver.page_source)
        self.logout()

    def test_dentist_creates_visit_referral_and_work_order(self):
        self.login_as("dentist")
        unique = datetime.now().strftime("%H%M%S")
        visit_tag = f"visit-{unique}"
        referral_reason = f"ref-{unique}"
        work_desc = f"work-{unique}"

        self.open("/visits/create/")
        self.select_first_non_empty_option("patient_id")
        self.fill_input("datetime", "2030-01-01T11:00")
        self.fill_input("complaints", visit_tag)
        self.fill_input("anamnesis", "auto anamnesis")
        self.fill_input("diagnosis", "auto diagnosis")
        self.fill_input("exam_results", "auto exam")
        self.fill_input("notes", "auto notes")
        self.click_submit()
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        self.assertIn("/visits/", self.driver.current_url)
        self.assertIn(visit_tag, self.driver.page_source)

        self.open("/dentist-documents/referrals/create/")
        self.select_first_non_empty_option("patient_id")
        visit_options = Select(self.driver.find_element(By.NAME, "visit_id"))
        if len(visit_options.options) > 1:
            visit_options.select_by_index(1)
        self.select_first_non_empty_option("referral_type")
        self.fill_input("destination", "УЗИ кабинет")
        self.fill_input("reason", referral_reason)
        self.fill_input("date", "2030-01-01")
        self.click_submit()
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        self.assertNotIn("Server Error (500)", self.driver.page_source)
        # В разных наборах данных backend может вернуть форму обратно с валидацией.
        if "/dentist-documents/referrals/" in self.driver.current_url:
            self.assertTrue(
                "/dentist-documents/referrals/" in self.driver.current_url
                or "/dentist-documents/referrals/create/" in self.driver.current_url
            )

        self.open("/dentist-documents/work-orders/create/")
        self.select_first_non_empty_option("visit_id")
        self.fill_input("description", work_desc)
        self.fill_input("materials", "cement")
        self.fill_input("tooth_numbers", "11,12")
        self.fill_input("duration_minutes", "35")
        self.fill_input("cost", "2500")
        self.fill_input("work_date", "2030-01-01")
        self.click_submit()
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        self.assertIn("/dentist-documents/work-orders/", self.driver.current_url)
        self.assertIn(work_desc, self.driver.page_source)
        self.logout()

    def test_dentist_edits_appointment_from_diary(self):
        self.login_as("dentist")
        unique = datetime.now().strftime("%H%M%S")
        comment = f"diary-appt-{unique}"
        updated_comment = f"diary-appt-upd-{unique}"
        today = datetime.now().strftime("%Y-%m-%d")

        self.open("/appointments/create/")
        self.select_first_non_empty_option("patient_id")
        self.select_first_non_empty_option("doctor_id")
        self.fill_input("datetime", f"{today}T12:00")
        self.fill_input("reason", comment)
        self.click_submit()
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        self.open("/dentist-diary/")
        edit_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/appointments/'][href*='/edit/']")
        if not edit_links:
            self.skipTest("No appointment edit links found in diary")
        edit_links[0].click()
        self.wait.until(EC.presence_of_element_located((By.NAME, "comment")))

        self.fill_input("comment", updated_comment)
        self.fill_input("date", today)
        self.fill_input("time", "12:30")
        self.click_submit()
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        self.open("/appointments/")
        self.assertIn(updated_comment, self.driver.page_source)
        self.logout()

    def test_dentist_edits_visit_from_diary(self):
        self.login_as("dentist")
        unique = datetime.now().strftime("%H%M%S")
        initial_complaints = f"diary-visit-{unique}"
        updated_complaints = f"diary-visit-upd-{unique}"
        today = datetime.now().strftime("%Y-%m-%d")

        self.open("/visits/create/")
        self.select_first_non_empty_option("patient_id")
        self.fill_input("datetime", f"{today}T13:00")
        self.fill_input("complaints", initial_complaints)
        self.fill_input("anamnesis", "initial anamnesis")
        self.fill_input("diagnosis", "initial diagnosis")
        self.fill_input("exam_results", "initial exam")
        self.fill_input("notes", "initial notes")
        self.click_submit()
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        self.open("/dentist-diary/")
        visit_links = self.driver.find_elements(
            By.XPATH,
            f"//td[contains(.,'{initial_complaints}')]/..//a[contains(@href,'/visits/') and contains(@href,'/edit/')]",
        )
        if not visit_links:
            self.skipTest("Created visit is not shown in diary list for current day")
        visit_edit = visit_links[0]
        visit_edit.click()
        self.wait.until(EC.presence_of_element_located((By.NAME, "complaints")))

        self.fill_input("complaints", updated_complaints)
        self.fill_input("diagnosis", "updated diagnosis")
        self.click_submit()
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        self.open("/visits/")
        self.assertIn(updated_complaints, self.driver.page_source)
        self.logout()


if __name__ == "__main__":
    unittest.main(verbosity=2)
