# main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import sys
import traceback
import json
from urllib.parse import parse_qs

app = FastAPI(
    title="API системы управления стоматологической клиникой",
    description="REST API для автоматизации работы стоматологической клиники",
    version="1.0.0"
)

# Включаем отладку
app.debug = True

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== ДИНАМИЧЕСКИЙ ИМПОРТ РОУТЕРОВ =====
def include_router_safe(module_name, router_name, prefix, tags):
    """Безопасное подключение роутера"""
    try:
        # Динамический импорт
        module = __import__(f"app.api.{module_name}", fromlist=[router_name])
        router = getattr(module, router_name)
        app.include_router(router, prefix=prefix, tags=tags)
        print(f"✅ Роутер '{module_name}' успешно подключен")
        return True
    except ModuleNotFoundError:
        print(f"⚠️  Роутер '{module_name}' не найден (пропускаем)")
        return False
    except Exception as e:
        print(f"❌ Ошибка подключения роутера '{module_name}': {str(e)[:100]}")
        return False

# ===== ПОДКЛЮЧЕНИЕ РОУТЕРОВ =====
print("=" * 60)
print("ПОДКЛЮЧЕНИЕ МОДУЛЕЙ API...")
print("=" * 60)

# Основные модули (должны быть) - ДОБАВЛЯЕМ VISITS ЗДЕСЬ!
routers_to_load = [
    ("auth", "router", "/auth", ["🔐 Аутентификация"]),
    ("patients", "router", "/patients", ["👥 Пациенты"]),
    ("appointments", "router", "/appointments", ["📅 Записи на прием"]),
    ("dentist", "router", "/dentist", ["👨‍⚕️ Функционал стоматолога"]),
    ("admin", "router", "/admin", ["⚙️ Администрирование"]),
    ("visits", "router", "/visits", ["🏥 Визиты"]),  # ← ДОБАВЛЕНО ЗДЕСЬ!
]

# Дополнительные модули (могут отсутствовать)
optional_routers = [
    ("dentist_diary", "router", "/dentist-diary", ["📓 Дневник врача"]),
    ("documents", "router", "/documents", ["📄 Документы"]),
    ("mkb_s3_api", "router", "/mkb-s3", ["🏷️ МКБ-С-3 Классификация"]),
    ("referrals", "router", "/referrals", ["🏥 Направления"]),
    ("work_crud", "router", "/works", ["🛠️ Работы"]),
]

# Новые CRUD модули
crud_routers = [
    ("research_crud", "router", "/research", ["🔬 Исследования"]),
    ("prescription_crud", "router", "/prescriptions", ["💊 Назначения"]),
    ("tooth_crud", "router", "/teeth", ["🦷 Зубы"]),
]

# Загружаем основные роутеры
print("\n📦 ОСНОВНЫЕ МОДУЛИ:")
print("-" * 30)
for module_name, router_name, prefix, tags in routers_to_load:
    include_router_safe(module_name, router_name, prefix, tags)

# Загружаем дополнительные роутеры
print("\n📦 ДОПОЛНИТЕЛЬНЫЕ МОДУЛИ:")
print("-" * 30)
for module_name, router_name, prefix, tags in optional_routers:
    include_router_safe(module_name, router_name, prefix, tags)

# Загружаем новые CRUD роутеры
print("\n📦 НОВЫЕ CRUD МОДУЛИ:")
print("-" * 30)
for module_name, router_name, prefix, tags in crud_routers:
    include_router_safe(module_name, router_name, prefix, tags)

print("=" * 60)

# ===== БАЗА ДАННЫХ =====
try:
    from app.db.database import init_db, close_db
    
    @app.on_event("startup")
    async def startup_event():
        """Инициализация соединения с БД при старте сервера."""
        print("🔄 Инициализация базы данных...")
        try:
            init_db()
            print("✅ База данных инициализирована")
        except Exception as e:
            print(f"❌ Ошибка инициализации БД: {e}")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Корректное закрытие соединения с БД при остановке сервера."""
        print("🔄 Закрытие соединения с БД...")
        try:
            close_db()
            print("✅ Соединение с БД закрыто")
        except Exception as e:
            print(f"⚠️  Ошибка закрытия БД: {e}")
            
except ImportError as e:
    print(f"⚠️  Модуль базы данных не найден: {e}")
    
    # Заглушки для событий
    @app.on_event("startup")
    async def startup_event():
        print("⚠️  База данных не подключена")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        print("⚠️  База данных не подключена")

# ===== СЛУЖЕБНЫЕ ЭНДПОИНТЫ =====

@app.get("/", 
         summary="Главная страница", 
         description="Основная информация о системе управления стоматологической клиникой")
async def root():
    """Корневой эндпоинт API"""
    return {
        "message": "API системы управления стоматологической клиникой",
        "version": "1.0.0",
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_json": "/openapi.json"
        },
        "health_check": "/health",
        "debug_routes": "/debug/routes",
        "modules": [
            "auth", "patients", "appointments", "dentist", "admin", "visits",  # ← ДОБАВЛЕНО
            "dentist-diary", "documents", "mkb-s3", "referrals",
            "research", "prescriptions", "teeth", "works"
        ]
    }

@app.get("/health", 
         summary="Проверка здоровья", 
         description="Проверка работоспособности API и подключения к БД")
async def health_check():
    """Проверка состояния сервиса"""
    return {
        "status": "healthy",
        "service": "dental_clinic_api",
        "version": "1.0.0",
        "timestamp": "2024-12-10T23:00:00Z",  # Можно заменить на datetime.now()
        "database": "connected" if 'init_db' in globals() else "not_configured"
    }

@app.get("/debug/routes", 
         summary="Отладка маршрутов", 
         description="Показать все зарегистрированные маршруты API",
         include_in_schema=False)
async def debug_routes():
    """Отладочный эндпоинт для просмотра всех маршрутов"""
    routes = []
    for route in app.routes:
        route_info = {
            "path": route.path,
            "methods": getattr(route, "methods", []),
            "name": getattr(route, "name", ""),
            "tags": getattr(route, "tags", [])
        }
        routes.append(route_info)
    return {"routes": routes}

@app.get("/api/summary",
         summary="Сводка по API",
         description="Информация о всех доступных эндпоинтах")
async def api_summary():
    """Сводная информация о всех эндпоинтах API"""
    endpoints = []
    for route in app.routes:
        if hasattr(route, "methods"):
            endpoint_info = {
                "path": route.path,
                "methods": list(route.methods),
                "tags": getattr(route, "tags", []),
                "summary": getattr(route, "summary", ""),
                "description": getattr(route, "description", "")
            }
            endpoints.append(endpoint_info)
    
    return {
        "total_endpoints": len(endpoints),
        "endpoints_by_method": {
            "GET": len([e for e in endpoints if "GET" in e["methods"]]),
            "POST": len([e for e in endpoints if "POST" in e["methods"]]),
            "PUT": len([e for e in endpoints if "PUT" in e["methods"]]),
            "DELETE": len([e for e in endpoints if "DELETE" in e["methods"]])
        },
        "endpoints": endpoints
    }

# ===== ОБРАБОТЧИК ОШИБОК =====

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Глобальный обработчик исключений"""
    error_details = {
        "error": str(exc),
        "type": type(exc).__name__,
        "path": request.url.path,
        "method": request.method,
        "traceback": traceback.format_exc() if app.debug else None
    }
    print(f"❌ Ошибка: {error_details}")
    
    # Определяем статус код
    status_code = 500
    if hasattr(exc, 'status_code'):
        status_code = exc.status_code
    
    return JSONResponse(
        status_code=status_code,
        content={
            "error": "Внутренняя ошибка сервера",
            "details": str(error_details)  # Преобразуем в строку
        }
    )

# ===== ОБРАБОТЧИК 404 =====

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Обработчик 404 ошибок"""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Ресурс не найден",
            "path": request.url.path,
            "available_endpoints": [
                "/docs", "/redoc", "/health", "/api/summary"
            ]
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Обработчик ошибок валидации"""
    # Обрабатываем случай, когда body может быть bytes
    body = exc.body
    if isinstance(body, bytes):
        try:
            # Пробуем декодировать как JSON
            body = json.loads(body.decode('utf-8'))
        except:
            try:
                # Пробуем декодировать как form-urlencoded
                decoded = body.decode('utf-8')
                parsed = parse_qs(decoded)
                # Преобразуем в простой словарь
                body = {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}
            except:
                body = None
    
    return JSONResponse(
        status_code=422,
        content={
            "error": "Ошибка валидации данных",
            "details": exc.errors(),
            "body": body
        }
    )

# ===== ТОЧКА ВХОДА =====

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("🚀 ЗАПУСК API СТОМАТОЛОГИЧЕСКОЙ КЛИНИКИ")
    print("=" * 60)
    print("📚 Документация:")
    print("   • Swagger UI: http://localhost:8000/docs")
    print("   • ReDoc:     http://localhost:8000/redoc")
    print("   • OpenAPI:   http://localhost:8000/openapi.json")
    print("\n🔧 Утилиты:")
    print("   • Health:    http://localhost:8000/health")
    print("   • Debug:     http://localhost:8000/debug/routes")
    print("   • Summary:   http://localhost:8000/api/summary")
    print("\n📦 Основные модули:")
    print("   • Аутентификация: /auth")
    print("   • Пациенты:      /patients")
    print("   • Записи:        /appointments")
    print("   • Визиты:        /visits")  # ← ДОБАВЛЕНО
    print("   • Стоматолог:    /dentist")
    print("   • Админ:         /admin")
    print("\n🆕 Новые CRUD модули:")
    print("   • Исследования:  /research")
    print("   • Назначения:    /prescriptions")
    print("   • Зубы:         /teeth")
    print("   • Работы:       /works")
    print("=" * 60)
    
    try:
        uvicorn.run(
            "main:app", 
            host="0.0.0.0", 
            port=8000, 
            reload=True,
            log_level="info"
        )
    except Exception as e:
        print(f"❌ Ошибка запуска сервера: {e}")
        print("=" * 60)
        traceback.print_exc()