(
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
root="$PWD"
message="4-сабақ: қабат картасы, backend қаңқасы"

if git ls-files --error-unmatch -- .env >/dev/null 2>&1; then
    echo 'Остановлено: .env уже отслеживается Git.'
    exit 1
fi
if git show-ref --verify --quiet refs/tags/lesson-04; then
    echo 'Остановлено: тег lesson-04 уже существует.'
    exit 1
fi

mkdir -p docs backend/app/{core,routers,schemas,services,repositories,models}
touch backend/app/__init__.py
touch backend/app/{core,routers,schemas,services,repositories,models}/__init__.py

cat > docs/layers.md <<'EOF'
docs/layers.md — үлгі

# Қабат картасы (4-сабақ)

```mermaid
flowchart LR
    Browser["Браузер"] --> Router["Router"]
    Router --> Logic["Schema / Service"]
    Logic --> Repository["Repository"]
    Repository --> Model["Model (PostgreSQL)"]
    Core["Core (config, database)"] -.-> Router
    Core -.-> Repository
```

| Қабат      | Мұғалім жаңа тест құрады                           | Оқушы тестті тапсырады                                                |
|------------|----------------------------------------------------|-----------------------------------------------------------------------|
| Router     | POST /api/tests · teacher рөлі                     | POST /api/tests/{test_id}/attempts · student рөлі                      |
| Schema     | TestCreate кірісі → TestRead жауабы                | AttemptCreate кірісі → AttemptResult жауабы                           |
| Service    | Мұғалімді тест иесі етеді, жоба күйін белгілейді    | Жауаптарды тексереді және ұпай есептейді                               |
| Repository | TestRepository.create тест пен сұрақтарды сақтайды | TestRepository.get_published оқиды, AttemptRepository.create сақтайды |
| Model      | tests, questions, answer_options кестелері         | test_attempts және attempt_answers кестелері                          |
| Қате→HTTP  | Сұрақтар тізімі бос → 422                          | Жарияланған тест табылмады → 404                                       |

## Біздің ереже

- Router-де SQL жоқ, service-те HTTPException жоқ
- Құпиялар тек .env-те
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

add_line .gitignore '.env'
add_line .gitignore '.venv/'
if ! grep -Eiq '^fastapi([[:space:]<>=!~;\[]|$)' backend/requirements.txt 2>/dev/null; then
    add_line backend/requirements.txt 'fastapi'
fi
if ! grep -Eiq '^pydantic[-_]settings([[:space:]<>=!~;\[]|$)' backend/requirements.txt; then
    add_line backend/requirements.txt 'pydantic-settings>=2,<3'
fi
add_line backend/requirements-dev.txt '-r requirements.txt'
if ! grep -Eiq '^ruff([[:space:]<>=!~;\[]|$)' backend/requirements-dev.txt; then
    add_line backend/requirements-dev.txt 'ruff'
fi
if ! grep -Eiq '^pytest([[:space:]<>=!~;\[]|$)' backend/requirements-dev.txt; then
    add_line backend/requirements-dev.txt 'pytest'
fi

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
# Prompt log — 4-сабақ

| Қадам | Сұраныс | Нәтиже |
|-------|---------|--------|
| П1 | Қабат картасын тексеру және Mermaid сызбасын қосу. | Картада екі әрекет, бес қабат және HTTP қателері көрсетілді. |
| П2 | Backend қаңқасын және Ruff баптауын дайындау. | Алты пакет, баптау және тәуелділік файлдары дайындалды. |
| П3 | Конфигурациядағы айнымалыларды түсіндіру. | Айнымалылардың қызметі, әдепкі мәндері және орталар арасындағы айырмашылық қарастырылды. |
EOF

echo 'Проверь локальный .env в редакторе. Значение replace-me замени своими настройками.'
echo 'После сохранения нажми Enter.'
IFS= read -r </dev/tty

lesson_python=python
if [[ -z "${VIRTUAL_ENV:-}" ]]; then
    if [[ ! -d .venv ]]; then
        python -m venv .venv
    fi
    if [[ -f .venv/Scripts/python.exe ]]; then
        lesson_python="$root/.venv/Scripts/python.exe"
    else
        lesson_python="$root/.venv/bin/python"
    fi
fi

(
    cd backend
    "$lesson_python" -m pip install -r requirements-dev.txt
    "$lesson_python" -c "from app.core.config import settings; print('config ok')"
    "$lesson_python" -m ruff check .
)

echo 'Заполни журнал прямо здесь. После каждого ответа нажимай Enter.'
ask() {
    local answer=''
    while [[ -z "${answer//[[:space:]]/}" ]]; do
        printf '%s\n> ' "$1" >&2
        IFS= read -r answer </dev/tty || return 1
    done
    printf '%s' "$answer"
}

p1=$(ask 'П1. Какую правку карты ты приняла или отклонила и почему?')
p2=$(ask 'П2. Какое решение по каркасу ты приняла или отклонила и почему?')
p3=$(ask 'П3. Своими словами: для чего нужны APP_NAME, ENVIRONMENT, DATABASE_URL и CORS_ORIGINS, где хранятся секреты, что бывает без значения и что меняется между local, test и server?')

printf '\n## Өз шешімім\n\n- П1 — %s\n- П2 — %s\n- П3 — %s\n' \
    "$p1" "$p2" "$p3" >> docs/prompt-log.md

files=(
    .gitignore .env.example docs/layers.md docs/prompt-log.md
    backend/requirements.txt backend/requirements-dev.txt backend/pyproject.toml
    backend/app/__init__.py backend/app/core/config.py
    backend/app/{core,routers,schemas,services,repositories,models}/__init__.py
)

git status --short -- "${files[@]}"
printf 'Чтобы сделать коммит и отправить его на GitHub, введи yes: '
IFS= read -r answer </dev/tty
if [[ "$answer" != yes ]]; then
    echo 'Файлы готовы. Коммит ещё не сделан.'
    exit 0
fi

branch=lesson-04-work
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
        --body 'Қабат картасы, Mermaid сызбасы, backend қаңқасы және prompt log.'
else
    echo 'Ветка и тег отправлены. Открой ссылку из git push и создай PR из lesson-04-work.'
fi
)       
  
