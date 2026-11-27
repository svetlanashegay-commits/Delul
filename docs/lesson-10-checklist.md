# Проверка урока 10

| № | Проверка | Как проверить |
|---|---|---|
| 1 | Realm delul, роли student/teacher/admin | keycloak/realm-delul.json |
| 2 | Новая регистрация получает только student | defaultRole и тест realm |
| 3 | Public client, PKCE S256, audience delul-api | realm, Swagger Authorize |
| 4 | RS256, issuer, audience, exp, обязательные claims | tests/test_keycloak.py |
| 5 | Без токена и с испорченным токеном — 401 | API auth tests |
| 6 | Нет роли приложения — 403 | API auth tests |
| 7 | JWKS недоступен — 503 | API auth tests |
| 8 | users.keycloak_id, нет password_hash | alembic upgrade head; tests/test_migrations.py |
| 9 | Admin управляет пользователями, student не создаёт тест | матрица API и тесты CRUD |
| 10 | Старого входа нет; тесты не требуют Keycloak | POST /api/auth/login — 404; pytest -q |

Миграции 0004 и 0005 продолжают уже существующую историю проекта (0003 занят защитой попыток). Старые ID и результаты сохраняются; email сам по себе не даёт доступ к старому профилю.
