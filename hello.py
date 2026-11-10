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
# Prompt log — 4-сабақ

| Қадам | Сұраныс | Нәтиже |
|-------|---------|--------|
| П1 | Қабат картасын тексеру және Mermaid сызбасын қосу. | Екі әрекет, бес қабат және әр әрекетке HTTP қатесі көрсетілді. |
| П2 | Backend қаңқасын және Ruff баптауын дайындау. | Алты пакет, конфигурация және тәуелділік файлдары дайындалды. |
| П3 | Конфигурация айнымалыларының қызметін түсіндіру. | Айнымалылардың мақсаты, әдепкі мәндері және үш ортаға арналған баптаулар сипатталды. |

## П3. Баптаулар

1. `APP_NAME` — жоба атауы. `ENVIRONMENT` — іске қосу ортасы. `DATABASE_URL` — дерекқорға қосылу жолы. `CORS_ORIGINS` — рұқсат етілген frontend мекенжайларының JSON тізімі.
2. `.env.example` ішіндегі `replace-me` — үлгі мәні. Нақты құпия мәндер жергілікті `.env` файлында сақталады.
3. `DATABASE_URL` орта айнымалыларында да, `.env` файлында да болмаса, конфигурация жүктелгенде валидация қатесі шығады. Қалған үш баптаудың әдепкі мәні бар.
4. `local`, `test` және `server` орталарында дерекқорға қосылу жолы мен рұқсат етілген frontend мекенжайлары ортаға сай беріледі.
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
    "$python_cmd" -c "from app.core.config import settings; print('config ok')"
    "$python_cmd" -m ruff check .
)

echo 'Для prompt log ответь своими словами. После каждой строки нажимай Enter.'
printf 'П1. Что ты приняла или отклонила в карте и почему? '
IFS= read -r p1 </dev/tty
printf 'П2. Что ты приняла или отклонила в каркасе и почему? '
IFS= read -r p2 </dev/tty
printf 'П3. Как ты объяснишь настройки своими словами? '
IFS= read -r p3 </dev/tty

printf '\n## Өз шешімім\n\n- П1 — %s\n- П2 — %s\n- П3 — %s\n' \
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
        --body 'Қабат картасы, Mermaid сызбасы, backend қаңқасы және prompt log.'
else
    echo 'Ветка и тег отправлены. Для PR открой ссылку из вывода git push.'
fi
)
       
  
