# Карта слоёв (урок 4)

```mermaid
flowchart LR
    Browser["Браузер"] --> Router["Маршрутизатор"]
    Router --> Logic["Схема / Сервис"]
    Logic --> Repository["Репозиторий"]
    Repository --> Model["Модель (PostgreSQL)"]
    Core["Ядро (настройки, база данных)"] -.-> Router
    Core -.-> Repository
```

| Слой      | Преподаватель создаёт новый тест                           | Студент проходит тест                                                |
|------------|----------------------------------------------------|-----------------------------------------------------------------------|
| Router     | POST /api/tests · роль teacher                     | POST /api/tests/{test_id}/attempts · роль student                      |
| Schema     | Вход TestCreate → ответ TestRead                | Вход AttemptCreate → ответ AttemptResult                           |
| Service    | Назначает преподавателя владельцем теста, задаёт статус черновика    | Проверяет ответы и рассчитывает баллы                               |
| Repository | TestRepository.create сохраняет тест и вопросы | TestRepository.get_published читает, AttemptRepository.create сохраняет |
| Model      | Таблицы tests, questions, answer_options         | Таблицы test_attempts и attempt_answers                          |
| Ошибка→HTTP  | Список вопросов пуст → 422                          | Опубликованный тест не найден → 404                                       |

## Наши правила

- В маршрутизаторе нет SQL, в сервисе нет HTTPException
- Секреты хранятся только в .env
EOF

if [[ ! -e backend/app/core/config.py ]]; then
    cat > backend/app/core/config.py <<'EOF'
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[3] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Delul"
    environment: Literal["local", "test", "server"] = "local"
    database_url: str
    cors_origins: list[str] = Field(default_factory=list)


settings = Settings()
EOF
fi

if [[ ! -e .env.example ]]; then
    cat > .env.example <<'EOF'
APP_NAME=Delul
ENVIRONMENT=local
DATABASE_URL=postgresql+psycopg://delul:replace-me@localhost:5432/delul
CORS_ORIGINS=["http://localhost:3000"]
EOF
fi

add_line() {
    local file="$1" line="$2"
    touch "$file"
    if ! grep -Fxq -- "$line" "$file"; then
        printf '\n%s\n' "$line" >> "$file"
    fi
}

add_dependency() {
    local file="$1" name="$2" requirement="$3"
    touch "$file"
    if ! grep -Eiq "^${name}([^[:alnum:]_-]|$)" "$file"; then
        add_line "$file" "$requirement"
    fi
}

add_line .gitignore '.env'
add_line .gitignore '.venv/'
add_dependency backend/requirements.txt fastapi fastapi
add_dependency backend/requirements.txt 'pydantic[-_]settings' 'pydantic-settings>=2,<3'
add_line backend/requirements-dev.txt '-r requirements.txt'
add_dependency backend/requirements-dev.txt ruff ruff
add_dependency backend/requirements-dev.txt pytest pytest

if [[ ! -e backend/pyproject.toml ]]; then
    cat > backend/pyproject.toml <<'EOF'
[tool.ruff]
target-version = "py310"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I"]
EOF
fi

git check-ignore .env
if [[ ! -e .env ]]; then
    cp .env.example .env
fi

cat > docs/prompt-log.md <<'EOF'
# Журнал запросов — урок 4

| Шаг | Запрос | Результат |
|-------|---------|--------|
| П1 | Проверить карту слоёв и добавить схему Mermaid. | Показаны два действия, пять слоёв и ошибка HTTP для каждого действия. |
| П2 | Подготовить каркас серверной части и настройки Ruff. | Подготовлены шесть пакетов, конфигурация и файлы зависимостей. |
| П3 | Объяснить назначение переменных конфигурации. | Описаны назначение переменных, значения по умолчанию и настройки для трёх сред. |

## П3. Настройки

1. `APP_NAME` — название проекта. `ENVIRONMENT` — среда запуска. `DATABASE_URL` — строка подключения к базе данных. `CORS_ORIGINS` — список разрешённых адресов клиентской части в формате JSON.
2. `replace-me` в `.env.example` — пример значения. Настоящие секретные значения хранятся в локальном файле `.env`.
3. Если `DATABASE_URL` отсутствует и в переменных окружения, и в файле `.env`, при загрузке конфигурации возникает ошибка валидации. Остальные три настройки имеют значения по умолчанию.
4. Для сред `local`, `test` и `server` строка подключения к базе данных и разрешённые адреса клиентской части задаются в соответствии со средой.
EOF

echo 'Проверь значения в локальном .env. После сохранения нажми Enter.'
IFS= read -r </dev/tty

python_cmd=python
if ! command -v python >/dev/null 2>&1; then
    python_cmd=python3
fi

if [[ -z "${VIRTUAL_ENV:-}" ]]; then
    if [[ ! -d .venv ]]; then
        "$python_cmd" -m venv .venv
    fi
    if [[ -f .venv/Scripts/python.exe ]]; then
        python_cmd="$root/.venv/Scripts/python.exe"
    else
        python_cmd="$root/.venv/bin/python"
    fi
fi

(
    cd backend
    "$python_cmd" -m pip install -r requirements-dev.txt
    "$python_cmd" -c "from app.core.config import settings; print('конфигурация загружена')"
    "$python_cmd" -m ruff check .
)

echo 'Для журнала запросов ответь своими словами. После каждой строки нажимай Enter.'
printf 'П1. Что ты приняла или отклонила в карте и почему? '
IFS= read -r p1 </dev/tty
printf 'П2. Что ты приняла или отклонила в каркасе и почему? '
IFS= read -r p2 </dev/tty
printf 'П3. Как ты объяснишь настройки своими словами? '
IFS= read -r p3 </dev/tty

printf '\n## Моё решение\n\n- П1 — %s\n- П2 — %s\n- П3 — %s\n' \
    "$p1" "$p2" "$p3" >> docs/prompt-log.md

files=(
    .gitignore .env.example docs/layers.md docs/prompt-log.md
    backend/requirements.txt backend/requirements-dev.txt backend/pyproject.toml
    backend/app/__init__.py backend/app/core/config.py
    backend/app/{core,routers,schemas,services,repositories,models}/__init__.py
)

git status --short -- "${files[@]}"
printf 'Для коммита и отправки на GitHub введи yes и нажми Enter. '
IFS= read -r answer </dev/tty
[[ "$answer" == yes ]] || exit 0

if [[ "$(git branch --show-current)" != "$branch" ]]; then
    git switch -c "$branch"
fi

git add -- "${files[@]}"
git diff --cached --check -- "${files[@]}"
git commit --only -m "$message" -- "${files[@]}"
git tag lesson-04
git push --atomic -u origin "$branch" refs/tags/lesson-04

if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    gh pr create --head "$branch" --title "$message" \
        --body 'Карта слоёв, схема Mermaid, каркас серверной части и журнал запросов.'
else
    echo 'Ветка и тег отправлены. Для PR открой ссылку из вывода git push.'
fi
)
       
  
