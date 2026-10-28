# Проверка адаптации через LLM

Запускать из `backend/worker` в Python-окружении с зависимостями из `requirements.txt`.
Ключ передаётся через переменную окружения `OPENAI_API_KEY`. Скрипт не загружает `.env`.
`OPENAI_BASE_URL` необязателен, по умолчанию используется `https://api.openai.com/v1`.
Модель задаётся явно через `--model`; она должна поддерживать Chat Completions с JSON mode.
В примерах используется `gpt-4.1-mini` — замените её на доступную модель провайдера.
Каждый запуск адаптации делает три платных API-вызова, отдельный Critic — один.

```powershell
python -m app.adapt_resume resume.txt vacancy.txt result.json --model gpt-4.1-mini
```

Входные файлы — полный текст в UTF-8 (допускается BOM).
JSON содержит `resume_text` и `review` (`passed`, `issues`).
Результат сохраняется и при `review.passed=false`: это завершённая проверка с замечаниями.
Код выхода 0 означает успешное выполнение, а не одобрение Critic.
При ошибке чтения, API или формата ответа процесс завершается с ненулевым кодом;
выходной файл не записывается до получения полного результата. Старый результат может остаться,
поэтому проверяйте код выхода. Существующий выходной файл заменяется при успешном запуске.
HTTP-таймаут берётся из настроек worker (`HTTP_TIME_OUT`, сейчас 20 секунд).

## Три ручных сценария

В `examples` находятся вымышленные данные. Оценивать нужно сам текст результата,
сопоставляя его с исходным резюме, а не только вердикт Critic.

### 1. Подходящий опыт

```powershell
python -m app.adapt_resume examples/resume.txt examples/vacancy_match.txt examples/results/match.json --model gpt-4.1-mini
```

Ожидание: Tailor выделяет разработку API на Python/FastAPI, PostgreSQL и тесты.
Контакты, работодатель, даты и образование сохранены. `review.passed=true`, `issues=[]`.

### 2. Отсутствующие навыки

```powershell
python -m app.adapt_resume examples/resume.txt examples/vacancy_gaps.txt examples/results/gaps.json --model gpt-4.1-mini
```

Ожидание: Kubernetes, AWS, Kafka и руководство командой не приписаны кандидату.
Подтверждённый опыт сохранён. Само отсутствие требований вакансии не является ошибкой адаптации.

### 3. Намеренно добавленный ложный факт

После успешного первого запуска создать копию адаптированного текста с одной добавленной строкой:

```powershell
$result = Get-Content examples/results/match.json -Raw -Encoding UTF8 | ConvertFrom-Json
$falseResume = $result.resume_text + "`nРуководила командой из пяти разработчиков."
Set-Content examples/results/false_resume.txt -Value $falseResume -Encoding UTF8
python -m app.adapt_resume examples/resume.txt examples/vacancy_match.txt examples/results/critic_false.json --model gpt-4.1-mini --tailored-resume examples/results/false_resume.txt
```

Этот режим вызывает только `CriticAgent`, без Matcher и Tailor, и сохраняет `CriticResult`
с полями `passed` и `issues`. Ожидание: `passed=false`, замечание явно указывает на
неподтверждённое руководство командой из пяти разработчиков.

Результаты LLM могут различаться между запусками. Эти три случая — ручная проверка,
а не гарантия качества на произвольных документах. Для отчёта сохраняйте JSON,
название модели, дату запуска и результат сравнения с исходным текстом.

## Автоматические тесты

```powershell
python -m unittest discover -s tests
```

Тесты используют подставные HTTP-ответы и проверяют код, а не качество реальной LLM.
