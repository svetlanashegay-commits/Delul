# Keycloak для Delul

`python keycloak/start.py` запускает локальный Keycloak, импортирует realm delul. Контейнер доступен только на 127.0.0.1:8080. Для разработки используется HTTP; для внешнего сервера нужен HTTPS и production-конфигурация.

Realm: student, teacher, admin. Новая регистрация получает student, offline_access, uma_authorization. Public client delul-web, стандартный Authorization Code flow, PKCE S256, audience delul-api только в access token. Время access token — 300 секунд. JWKS кэшируется API; принимается только RS256, проверяются issuer, audience и обязательные claims. Приоритет ролей admin → teacher → student.

Демо-пользователи нового импорта: student@demo.kz, teacher@demo.kz, admin@demo.kz. Начальный пароль demo-pass-123. В существующем realm изменённый пароль сохраняется. Пароль администратора operator создаётся случайно и хранится только в игнорируемом .env.

Регистрироваться и менять пароль нужно в Keycloak. API собственных паролей не принимает и не хранит. См. ../README.md для запуска API и миграций. После обновления файлов запущенный сервер нужно перезапустить. Изменение JSON не обновляет существующий realm: настройки существующего клиента меняются в админ-консоли; данные realm и пользователей удалять не нужно.

Официальная документация: https://www.keycloak.org/server/importExport и https://pyjwt.readthedocs.io/en/stable/api.html
