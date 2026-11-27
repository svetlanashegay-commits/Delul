# API и матрица прав

Все защищённые маршруты требуют Bearer access token Keycloak. Без токена или при неверной подписи/iss/aud/exp — 401; нет нужной роли — 403; сервер ключей недоступен — 503. Роли изменяются только в Keycloak. Регистрация и восстановление пароля выполняются на странице Keycloak.

| Метод | Путь | Кто | Ответ |
|---|---|---|---|
| GET | /api/health | Анонимный | 200, состояние БД; 503 при недоступной БД |
| GET | /api/auth/me | student, teacher, admin | 200; профиль создаётся по issuer и sub |
| GET | /api/users | admin | 200, список с limit/offset |
| GET | /api/users/{user_id} | admin | 200 / 404 |
| PATCH | /api/users/{user_id} | admin | 200, имя/группа; роль менять нельзя (400) |
| DELETE | /api/users/{user_id} | admin | 204; себя удалить нельзя (400) |
| GET | /api/quizzes | student, teacher, admin | 200; student — опубликованные, teacher — свои и опубликованные, admin — все |
| POST | /api/quizzes | teacher, admin | 201 |
| GET | /api/quizzes/{quiz_id} | student, teacher, admin | 200 / 404; студенту не выдаются правильные ответы |
| PATCH | /api/quizzes/{quiz_id} | teacher-владелец, admin | 200; чужой — 403 |
| DELETE | /api/quizzes/{quiz_id} | teacher-владелец, admin | 204; чужой — 403 |
| POST | /api/quizzes/{quiz_id}/questions | teacher-владелец, admin | 201; опубликованный тест — 400 |
| PATCH | /api/questions/{question_id} | teacher-владелец, admin | 200 |
| DELETE | /api/questions/{question_id} | teacher-владелец, admin | 204 |
| POST | /api/quizzes/{quiz_id}/publish | teacher-владелец, admin | 200; без вопросов — 400 |
| POST | /api/quizzes/{quiz_id}/attempts | student | 201; accepted_rules=true; повторная попытка — 409 |
| GET | /api/attempts/me | student | 200, собственные попытки |
| GET | /api/attempts/{attempt_id} | student-владелец | 200; X-Attempt-Token |
| PATCH | /api/attempts/{attempt_id}/answers | student-владелец | 200; attempt_token |
| POST | /api/attempts/{attempt_id}/heartbeat | student-владелец | 200; attempt_token |
| POST | /api/attempts/{attempt_id}/events | student-владелец | 200; attempt_token |
| POST | /api/attempts/{attempt_id}/submit | student-владелец | 200; attempt_token |
| GET | /api/quizzes/{quiz_id}/attempts | teacher-владелец, admin | 200, результаты и события |

Связь данных: users → quizzes → questions → answer_options; users и quizzes → attempts → attempt_answers/results/attempt_events. categories группирует quizzes. Старые auth_sessions не используются для авторизации; сохранены в истории БД без активных cookie endpoints. Все таблицы описаны в er-diagram.md.
