# П2 — объяснение первого FastAPI для начинающего

Этот документ объясняет текущие [main.py](../backend/app/main.py), [routers/health.py](../backend/app/routers/health.py) и [test_health.py](../backend/tests/test_health.py). Исполняемый код не изменяется. Номера строк относятся к версии на момент подготовки пояснения.

## 1. backend/app/main.py — собирает приложение

```python
from fastapi import FastAPI

from app.core.config import settings
from app.routers.health import router as health_router

app = FastAPI(
    title=settings.app_name,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
)
app.include_router(health_router)
```

| Строка | Что делает простыми словами |
|--------|-----------------------------|
| 1 | Импортирует FastAPI — класс для создания веб-приложения. |
| 2 | Пустая строка отделяет внешний импорт от импортов своего приложения. |
| 3 | Получает объект settings из core/config.py: название приложения и окружение. |
| 4 | Берёт router из routers/health.py и называет его здесь health_router. Это тот же объект, только с понятным местным именем. |
| 5 | Пустая строка отделяет импорты от создания приложения. |
| 6 | Создаёт объект FastAPI и сохраняет его в переменной app. Открытая скобка позволяет записать параметры на нескольких строках. |
| 7 | title задаёт название документации из settings.app_name. |
| 8 | docs_url задаёт адрес Swagger: /api/docs. |
| 9 | openapi_url задаёт адрес JSON-описания API: /api/openapi.json. Swagger использует его, чтобы показать маршруты. |
| 10 | redoc_url=None отключает вторую страницу документации ReDoc. |
| 11 | Закрывает вызов FastAPI(...). |
| 12 | Подключает health_router к приложению. Без этого /api/health не будет зарегистрирован. |

## 2. backend/app/routers/health.py — отвечает на запрос

```python
from fastapi import APIRouter

from app.core.config import settings
from app.schemas.health import HealthRead

router = APIRouter(prefix="/api")


@router.get("/health", response_model=HealthRead)
def read_health() -> HealthRead:
    return HealthRead(status="ok", environment=settings.environment)
```

| Строка | Что делает простыми словами |
|--------|-----------------------------|
| 1 | Импортирует APIRouter — инструмент для группы маршрутов. |
| 2 | Разделяет внешние и внутренние импорты. |
| 3 | Получает настройки приложения. |
| 4 | Получает схему ответа HealthRead с полями status: str и environment: str. |
| 5 | Отделяет импорты от остального кода. |
| 6 | Создаёт router. Префикс /api автоматически добавится перед адресами его маршрутов. |
| 7–8 | Пустые строки разделяют создание router и функцию. На результат запроса не влияют. |
| 9 | Декоратор регистрирует GET /health внутри router. С префиксом получается GET /api/health. response_model задаёт схему ответа и его проверку. |
| 10 | Объявляет функцию read_health. Обозначение → HealthRead в коде записано как -> HealthRead и указывает ожидаемый тип результата. |
| 11 | Возвращает объект HealthRead: status равен ok, environment берётся из settings. FastAPI преобразует объект в JSON. |

Ответ в локальном окружении:

```json
{"status":"ok","environment":"local"}
```

В config.py значение environment читается из переменной окружения ENVIRONMENT, по умолчанию local. Этот health проверяет доступность приложения, но не подключение к базе: базы в текущей версии нет.

## 3. backend/tests/test_health.py — проверяет поведение

```python
from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_ok():
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
```

| Строка | Что делает простыми словами |
|--------|-----------------------------|
| 1 | Импортирует TestClient — клиент, который вызывает приложение прямо из теста. |
| 2 | Отделяет внешние импорты от внутренних. |
| 3 | Импортирует тот же объект app, который запускает Uvicorn. |
| 4–5 | Пустые строки отделяют импорты от функции теста. |
| 6 | Объявляет тест. Pytest находит функцию по имени test_... в файле test_health.py. |
| 7 | Создаёт клиент для app, выполняет GET /api/health и сохраняет ответ в response. |
| 8 | assert проверяет, что код ответа равен 200. Если нет, pytest показывает ошибку. |
| 9 | Превращает JSON ответа в словарь Python. |
| 10 | Проверяет, что поле status равно ok. Отсутствие поля тоже приведёт к падению теста. |

Тест проверяет HTTP-код и status. Значение environment отдельной проверкой в этом тесте не проверяется.

## 4. Как uvicorn app.main:app находит файлы

Запуск выполняется из каталога backend:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

- uvicorn — сервер, который принимает реальные HTTP-запросы.
- app.main — путь импорта: каталог app, файл main.py.
- :app — имя переменной внутри main.py. Это объект FastAPI.
- При импорте main.py Python импортирует settings и health_router. В routers/health.py создаётся router и регистрируется функция read_health; затем main.py подключает router к app.
- --port 8001 задаёт порт. В этой рабочей среде для демонстрации использован 8001, потому что 8000 не удалось занять.
- --reload можно добавить для перезапуска при изменении файлов. В данной среде Windows он вызвал ошибку дочернего процесса, поэтому подтверждённый запуск выполнялся без него.

Запрос проходит так: браузер → Uvicorn → app → health_router → read_health → JSON-ответ.

## 5. Почему тест работает без запущенного сервера

TestClient получает объект app и обращается к нему внутри процесса Python через тестовый транспорт. Он не подключается к порту 8001, не запускает Uvicorn и не требует браузера. При этом FastAPI обрабатывает маршрут и формирует ответ.

Поэтому тест можно запустить при остановленном сервере. И наоборот: успешный TestClient-тест сам по себе не доказывает, что порт доступен в браузере. Для этого отдельно проверяется настоящий HTTP-запуск.

Команды из каталога backend после установки зависимостей:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m ruff check .
```

## 6. Три примера: что изменить и что сломается

| Изменение | Последствие | Как это обнаружится |
|-----------|-------------|---------------------|
| Удалить app.include_router(health_router) из main.py | Маршрут не попадёт в приложение, GET /api/health вернёт 404. | Проверка status_code == 200 упадёт. |
| В router заменить /health на /ping, оставив тест прежним | Новый адрес станет /api/ping, старый /api/health вернёт 404. | Тест всё ещё обращается к старому адресу и упадёт. |
| В read_health заменить status=ok на status=ready, сохранив строки в кавычках | Ответ останется корректным JSON и вернётся с кодом 200, но значение status изменится. | Проверка body["status"] == "ok" упадёт. |

В учебной демонстрации отдельно меняли ожидаемый код в самом тесте с 200 на 201: pytest показал assert 200 == 201. После возвращения 200 тест снова прошёл. Это подтверждает, что проверка замечает несовпадение.

## 7. Три главные мысли для пересказа

Это заготовка агента: автор проекта должен прочитать и пересказать её своими словами. Она не является подтверждением личного понимания автора.

1. main.py собирает приложение, а router связывает адрес запроса с функцией; схему ответа задаёт HealthRead.
2. В app.main:app слева указан путь к Python-модулю, справа — имя объекта приложения в нём.
3. TestClient вызывает приложение без отдельного сервера; assert проверяет ожидаемый код и содержимое ответа.
