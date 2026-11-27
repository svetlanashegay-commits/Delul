# Delul — тестирование студентов

Проект для преподавателей, создающих тесты, и студентов, проходящих их.

## Урок 10: Keycloak
Вход, регистрация, пароли и роли управляются Keycloak. API принимает только Bearer access token (RS256, JWKS, issuer, audience, срок действия). Локальные register/login/session удалены. В актуальной таблице users нет password_hash. Исторические миграции оставлены для обновления существующей базы.

## Запуск
1. Запустить Docker Desktop.
2. В корне проекта: `python keycloak/start.py`.
3. Настроить локальный `.env` по `keycloak/backend.env.example`, указать DATABASE_URL своей PostgreSQL. Пароли и `.env` не публиковать.
4. Установить зависимости: `python -m pip install -r backend/requirements-dev.txt`.
5. Из backend: `python -m alembic upgrade head`.
6. При переносе прежних пользователей явно связать их: `python manage.py link-keycloak EMAIL SUBJECT`. Subject взять из Keycloak Users; совпадение email не связывает аккаунты автоматически.
7. Запустить из backend: `python -m uvicorn app.main:app --port 8001`.
8. Swagger: http://127.0.0.1:8001/api/docs — Authorize (PKCE). Страница тестирования: http://127.0.0.1:8001/test.

Вход демо-пользователей нового realm: student@demo.kz, teacher@demo.kz, admin@demo.kz; начальный пароль demo-pass-123. В уже запущенном realm пароль мог быть изменён. Пароль operator создаётся отдельно и хранится только в keycloak/.env.

## Проверка
Из backend: `python -m pytest -q` и `python -m ruff check .`. Тесты используют SQLite в памяти и искусственные RSA ключи, настоящий Keycloak не требуется.

См. [матрицу прав](docs/api.md), [проверочный лист](docs/lesson-10-checklist.md), [модель данных](docs/er-diagram.md).

Одна попытка обеспечивается сервером и ограничением UNIQUE. Уход из вкладки регистрируется, но не доказывает списывание. Веб-страница не может запретить Google Объектив или съёмку другим устройством.
