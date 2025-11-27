# NeuroView

## Описание
NeuroView — платформа для проведения технических и soft skills интервью с использованием мультиагентной AI-системы. Бэкенд построен на FastAPI и управляет интервью, хранением данных, античитом и генерацией отчетов. Фронтенд — Next.js приложение для кандидатов, HR и администраторов. Кодовые задания выполняются в изолированных Docker-контейнерах с ограничениями по ресурсам.

## Возможности платформы
- Автоматические интервью с адаптивным сценарием: агенты (`general`, `technical`, `coding` `report`) подбирают вопросы под профиль кандидата и анализируют ответы.
- Поддержка кодовых заданий с запуском Python, JavaScript, Java, C++, Go, Rust и SQL внутри изолированных контейнеров, включающих контроль CPU, памяти, сети и времени выполнения.
- Генерация PDF-отчетов (ReportLab) с оценками по компетенциям, деталями интервью, кодом кандидата и рекомендациями для HR.
- Панель HR/админа: управление вакансиями, приглашениями, расписанием интервью, просмотр отчетов и статусов кандидатов.
- Интеграция с внешними LLM-провайдерами (OpenAI, Anthropic) через единый клиент.

## Античит система
Античит реализован сервисом `backend/services/anticheat_service.py` и состоит из нескольких уровней проверки:
- **Мониторинг активности браузера**: отслеживание переключений вкладок, потери фокуса, копирования и вставки; автоматические предупреждения и досрочное завершение после превышения лимита.
- **Темп ответов**: анализ time-to-answer, скорости печати и вариативности, выявление подозрительно быстрых реакций.
- **AI-детекция**: анализ текста ответов (модель `ai_detection_service`) для определения вероятности использования сторонних подсказчиков.
- **Множественные устройства**: фиксация параллельных сессий и повышение suspicion score.
- **Паттерны печати**: оценка стабильности и скорости набора, чтобы отличить копирование от реального ввода.
Все факторы агрегируются в `suspicion_score` (0–1) с рекомендациями `low/medium/high_risk`, которые доступны HR в отчете и интерфейсе.

## Генерация отчетов
`backend/utils/report_generator.py` формирует PDF-файлы с поддержкой кириллицы:
- Собирает структурированные данные интервью (вопросы, ответы, код, оценки).
- Использует дизайн, вдохновленный Apple Human Interface Guidelines: минимализм, акцент на типографике, единая цветовая гамма.
- Встраивает блоки: информация о кандидате, суммарные метрики, подробные вопросы/ответы, оценка компетенций, античит выводы.
- Сохраняет отчеты в `backend/reports/` с транслитерацией имен файлов, предотвращая проблемы с путями.

## Архитектура
- **Backend**: FastAPI, SQLAlchemy, Alembic миграции, SQLite (по умолчанию) или внешняя БД; Redis для кеша; DockerCodeExecutor для запуска кода. Сервисы организованы по доменам (`services/agents`, `services/interview_service.py`, `services/anticheat_service.py` и др.).
- **Frontend**: Next.js 14, TypeScript, Tailwind CSS, серверные компоненты и клиентские хуки (`app/` структура). Предоставляет рабочие пространства для кандидата, HR и администратора.
- **Инфраструктура**: `docker-compose.yml` поднимает backend, frontend, Redis и Nginx. Backend монтирует `/var/run/docker.sock` для запуска песочниц. Для production рекомендуется собирать образы без прямых volume с исходниками.
- **Выполнение кода**: `DockerCodeExecutor` динамически вытягивает официальные образы языков, монтирует временную директорию в `/code`, ограничивает ресурсы и выключает сеть. После выполнения контейнер удаляется, временные файлы стираются.

## Требования
- Docker 24+ и Docker Compose Plugin.
- Python 3.11 (для локального запуска backend).
- Node.js 18+ и npm 9+ (для локального запуска frontend).
- Учетки/ключи LLM-провайдеров (OpenAI, Anthropic) при рабочем режиме.

## Переменные окружения
Создайте файл `.env` в корне или задайте переменные в среде:
- `OPENAI_API_KEY` — ключ OpenAI.
- `ANTHROPIC_API_KEY` — ключ Anthropic (опционально).
- `DEFAULT_LLM_PROVIDER` — `openai` или `anthropic`.
- `DATABASE_URL` — строка подключения (по умолчанию SQLite `sqlite:///./neuroview.db`).
- Frontend использует `NEXT_PUBLIC_API_URL` для обращения к API (в docker-compose по умолчанию `http://localhost:8000`; при работе через Nginx установите `http://localhost` или домен прокси).

## Пример `.env`
Создайте файл в корне репозитория:
```
# NeuroView Backend Configuration
SCIBOX_API_KEY=API_KEY
SCIBOX_BASE_URL=https://llm.t1v.scibox.tech/v1
SCIBOX_MODEL=qwen3-32b-awq
SCIBOX_TEMPERATURE=0.2
SCIBOX_MAX_TOKENS=2000
SCIBOX_TIMEOUT=60
RETRY_ATTEMPTS=3
RETRY_DELAY=1.0
ENVIRONMENT=development

```
Значения можно переопределить в `docker-compose.yml` или через переменные среды в CI/CD.

## Инструкция по запуску
1. Установите Docker Desktop и включите Docker Compose Plugin.
2. Склонируйте репозиторий и перейдите в каталог:
   ```
   git clone https://github.com/NiQkir1/NeuroView.T1Moscow.git
   cd NeuroView.T1Moscow
   ```
3. Создайте `.env` (см. пример выше) и при необходимости `.env.local` для фронтенда.
4. Соберите и поднимите сервисы:
   ```
   docker compose up --build
   ```
5. Проверьте доступность:
   - API: `http://localhost:8000/health`
   - Frontend: `http://localhost:3000`
   - Nginx gateway: `http://localhost`
6. Для остановки выполните `docker compose down`. Чтобы очистить тома Redis: `docker compose down -v`.
7. Для локальной разработки без Docker используйте разделы ниже (backend/frontend).

## Запуск через Docker
1. Скопируйте пример переменных: `cp backend/env.example .env` и заполните значения (или экспортируйте вручную для compose).
2. Запустите сборку и контейнеры:
   ```
   docker compose up --build
   ```
3. Сервисы:
   - Backend: `http://localhost:8000`
   - Frontend: `http://localhost:3000`
   - Nginx Gateway: `http://localhost`
4. Для production рекомендуются изменения:
   - Удалить монтирование исходников (`./backend:/app`, `./frontend:/app`) и собирать артефакты внутри Dockerfile.
   - Настроить SSL и домены в `api-gateway/nginx.conf`.
   - Обновить `NEXT_PUBLIC_API_URL` на адрес Nginx или публичный домен.

## Локальный запуск backend (без Docker)
1. Перейдите в `backend/` и создайте виртуальное окружение:
   ```
   python -m venv venv
   venv\Scripts\activate  # Windows
   source venv/bin/activate  # Linux/macOS
   ```
2. Установите зависимости:
   ```
   pip install -r requirements.txt
   ```
3. Примените миграции или инициализируйте БД `python main.py` (при первом запуске создается admin).
4. Запустите сервер:
   ```
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```
5. Убедитесь, что Docker установлен и доступен, чтобы `DockerCodeExecutor` смог создавать песочницы. Иначе будет использован небезопасный fallback через subprocess (только Python/JavaScript).

## Локальный запуск frontend
1. Перейдите в `frontend/`.
2. Установите зависимости:
   ```
   npm install
   ```
3. Создайте `.env.local` при необходимости и задайте `NEXT_PUBLIC_API_URL`.
4. Запустите дев-сервер:
   ```
   npm run dev
   ```
5. Откройте `http://localhost:3000`. Для корректной работы требуется запущенный backend и Redis.

## Работа с отчетами и файлами
- PDF-отчеты сохраняются в `backend/reports/`. Файлы именуются по шаблону `report_{CandidateName}_{timestamp}.pdf`.
- Образцы отчетов доступны в каталоге `backend/reports/` и в интерфейсе HR (раздел Reports).
- Для регенерации отчета из JSON используйте `backend/generate_demo_report.py` либо API-эндпоинты из `report_service`.

## Тестирование и проверка
- Здоровье сервисов: `GET /health`.
- Автотесты не входят в репозиторий; рекомендуется добавить pytest для сервисов и Playwright/RTL для фронта.
- После изменений запускайте линтеры (`pylint`, `isort`, `flake8`) и форматирование (`black`) в backend, а также `npm run lint` для frontend.


