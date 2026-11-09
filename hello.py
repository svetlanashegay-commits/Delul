docs/layers.md — үлгі
# Қабат картасы (4-сабақ)
| Қабат      | Мұғалім жаңа тест құрады               | Оқушы тестті тапсырады                                 |
|------------|----------------------------------------|--------------------------------------------------------|
| Router     | POST /api/tests (teacher)              | POST /api/tests/{test_id}/attempts (student)           |
| Schema     | TestCreate → TestRead                  | AttemptCreate → AttemptResult                          |
| Service    | Сұрақтарды тексереді, сақтауды сұрайды | Жауаптарды тексереді, балл есептейді                   |
| Repository | TestRepository.create                  | TestRepository.get_published; AttemptRepository.create |
| Model      | tests, questions, answer_options       | test_attempts, attempt_answers                         |
| Қате→HTTP  | Сұрақ жоқ → 422                        | Тест табылмады → 404                                   |
## Біздің ереже
- Router-де SQL жоқ, service-те HTTPException жоқ
- Құпиялар тек .env-те

  backend/
├── app/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py       
│   ├── models/
│   │   └── __init__.py
│   ├── repositories/
│   │   └── __init__.py
│   ├── routers/
│   │   └── __init__.py
│   ├── schemas/
│   │   └── __init__.py
│   └── services/
│       └── __init__.py
├── .env.example             
├── .gitignore                
├── pyproject.toml             
├── requirements-dev.txt       
└── requirements.txt       
  
