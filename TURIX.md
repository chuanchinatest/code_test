# TURIX.md — Notification System

## Overview

A full-stack notification service built with Python FastAPI backend and a modern frontend (TBD). The system provides RESTful APIs for sending, managing, and tracking notifications across multiple channels (email, SMS, push, in-app). Designed for high availability, extensibility, and real-time delivery.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, Uvicorn |
| Database | PostgreSQL (primary), Redis (cache + pub/sub) |
| Message Queue | Celery + Redis/RabbitMQ (async tasks) |
| Frontend | TBD (React/Vue recommended) |
| DevOps | Docker, Docker Compose, GitHub Actions |
| Monitoring | Prometheus + Grafana (planned) |

---

## Build & Run

### Prerequisites

- Python 3.11+
- Docker & Docker Compose (recommended)
- Node.js 18+ (for frontend)

### Quick Start (Docker)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend
```

### Local Development

```bash
# Backend
cd notification_system/backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run Celery worker (for async tasks)
celery -A app.celery worker --loglevel=info

# Frontend (when scaffolded)
cd notification_system/frontend
npm install
npm run dev
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Lint & format
ruff check .
ruff format .

# Type check
mypy app/
```

---

## Architecture

```
notification_system/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── config.py            # Pydantic settings (env vars)
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── notifications.py   # Notification CRUD endpoints
│   │   │   │   ├── templates.py       # Message template endpoints
│   │   │   │   ├── channels.py        # Channel config endpoints
│   │   │   │   └── users.py           # User preference endpoints
│   │   │   └── deps.py          # FastAPI dependencies (DB, auth)
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── security.py      # JWT/auth utilities
│   │   │   └── exceptions.py    # Custom exception handlers
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── notification.py  # SQLAlchemy models
│   │   │   ├── template.py
│   │   │   └── user.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── notification.py  # Pydantic request/response schemas
│   │   │   └── template.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── notification.py  # Business logic
│   │   │   ├── email.py         # Email channel provider
│   │   │   ├── sms.py           # SMS channel provider
│   │   │   └── push.py          # Push notification provider
│   │   ├── tasks/
│   │   │   ├── __init__.py
│   │   │   └── notification.py  # Celery async tasks
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── session.py       # SQLAlchemy session factory
│   │   │   └── base.py          # Base model & migrations
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── helpers.py
│   ├── alembic/                 # Database migrations
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py          # Pytest fixtures
│   │   ├── test_api/
│   │   │   └── test_notifications.py
│   │   └── test_services/
│   │       └── test_notification.py
│   ├── Dockerfile
│   ├── requirements.txt         # Production deps
│   ├── requirements-dev.txt     # Dev + test deps
│   └── pyproject.toml           # Tool configs (ruff, mypy, pytest)
│
├── frontend/                    # Frontend app (TBD — React/Vue)
│
├── docker-compose.yml           # Local dev stack
├── docker-compose.prod.yml      # Production stack
├── .github/
│   └── workflows/
│       ├── ci.yml               # Lint, test, build on PR
│       └── deploy.yml           # Deploy to staging/prod
├── .env.example                 # Required env vars template
├── .pre-commit-config.yaml      # Pre-commit hooks
├── .gitignore
├── server.log                   # Runtime log (gitignored)
├── notification.log             # App log (gitignored)
└── TURIX.md                     # This file
```

### Data Flow

```
Client Request
    → FastAPI Router (app/api/v1/)
    → Pydantic Validation (app/schemas/)
    → Service Layer (app/services/)
    → Celery Task (app/tasks/) [async]
    → Channel Provider (email/sms/push)
    → Database (PostgreSQL)
```

### Async Processing

Heavy operations (sending notifications, batch processing) are offloaded to Celery workers:

- **Queue**: `notifications` — individual notification delivery
- **Queue**: `batches` — bulk/batch operations
- **Queue**: `retries` — failed delivery retries with exponential backoff

---

## API Design Conventions

### URL Structure

- Base path: `/api/v1`
- Resource names: plural nouns, kebab-case
- Examples:
  - `GET /api/v1/notifications` — list
  - `POST /api/v1/notifications` — create
  - `GET /api/v1/notifications/{id}` — detail
  - `PATCH /api/v1/notifications/{id}` — partial update
  - `DELETE /api/v1/notifications/{id}` — delete

### Response Format

```json
{
  "code": 200,
  "message": "success",
  "data": { ... },
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 100
  }
}
```

### Error Format

```json
{
  "code": 400,
  "message": "Validation error",
  "detail": [
    { "field": "email", "msg": "Invalid email format" }
  ]
}
```

### HTTP Status Codes

| Code | Usage |
|------|-------|
| 200 | OK (GET, PATCH) |
| 201 | Created (POST) |
| 204 | No Content (DELETE) |
| 400 | Bad Request (validation error) |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 409 | Conflict (duplicate resource) |
| 422 | Unprocessable Entity |
| 500 | Internal Server Error |

---

## Development Conventions

### Python Style

- **Formatter**: `ruff` (replaces black + isort)
- **Linter**: `ruff`
- **Type Checker**: `mypy` — all functions must have type hints
- **Line length**: 88 characters
- **Import style**: absolute imports preferred

### Code Patterns

```python
# Service layer: pure business logic, no HTTP concerns
class NotificationService:
    async def send(self, dto: NotificationCreate) -> Notification:
        ...

# Router: thin layer, delegates to services
@router.post("/notifications", response_model=NotificationResponse)
async def create_notification(
    dto: NotificationCreate,
    service: NotificationService = Depends(get_notification_service),
) -> NotificationResponse:
    ...
```

### Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`

Examples:
- `feat(notifications): add email channel support`
- `fix(api): handle missing template id gracefully`
- `test(services): add notification service unit tests`

### Branch Strategy

- `main` — production-ready, protected
- `develop` — integration branch
- `feat/<name>` — new features
- `fix/<name>` — bug fixes
- `hotfix/<name>` — production hotfixes

---

## Testing Strategy

### Test Pyramid

| Layer | Tool | Coverage Target |
|-------|------|-----------------|
| Unit | pytest | 80%+ |
| Integration | pytest + TestClient | 60%+ |
| E2E | pytest + httpx | Key flows |

### Test Structure

```python
# tests/conftest.py
@pytest.fixture
def client() -> TestClient:
    return TestClient(app)

@pytest.fixture
def db_session() -> Session:
    # Setup test DB, yield session, teardown
    ...

# tests/test_api/test_notifications.py
def test_create_notification(client: TestClient) -> None:
    response = client.post("/api/v1/notifications", json={...})
    assert response.status_code == 201
```

### Running Tests

```bash
# All tests
pytest

# Specific module
pytest tests/test_api/

# With debugger
pytest --pdb

# Parallel execution
pytest -n auto
```

---

## Deployment

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# App
APP_ENV=development
DEBUG=true
SECRET_KEY=your-secret-key

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/notifications

# Redis
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Email (SMTP)
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=...
SMTP_PASSWORD=...

# SMS (Twilio)
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=...
```

### Docker Deployment

```bash
# Build & run production stack
docker-compose -f docker-compose.prod.yml up -d --build

# Scale workers
docker-compose -f docker-compose.prod.yml up -d --scale celery-worker=3
```

### CI/CD Pipeline (GitHub Actions)

```yaml
# .github/workflows/ci.yml
name: CI
on: [pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r requirements-dev.txt
      - run: ruff check .
      - run: mypy app/
      - run: pytest --cov=app --cov-report=xml
      - uses: codecov/codecov-action@v3
```

---

## Pre-commit Hooks

Required before every commit:

```bash
# Install hooks
pre-commit install

# Run manually on all files
pre-commit run --all-files
```

Configured in `.pre-commit-config.yaml`:
- `ruff` — lint & format
- `mypy` — type check
- `pytest` — quick test run (staged files only)

---

## Notes & Gotchas

### Current State

- Project is in **early scaffolding stage**
- `backend/` and `frontend/` are empty — use the architecture above when creating files
- No `requirements.txt`, `pyproject.toml`, or test config yet

### Common Issues

1. **Database migrations**: Always run `alembic revision --autogenerate -m "msg"` after model changes, never edit existing migrations
2. **Celery tasks**: Use `delay()` or `apply_async()` for fire-and-forget; use `.get()` only in tests
3. **Async SQLAlchemy**: Use `AsyncSession`, not `Session`, in FastAPI dependencies
4. **Environment variables**: Never commit `.env`; use `.env.example` for documentation

### Performance Considerations

- Use Redis caching for template lookups (frequent reads, rare writes)
- Batch database writes when processing bulk notifications
- Implement rate limiting per channel to avoid provider throttling

### Security Checklist

- [ ] JWT secret rotated regularly
- [ ] API rate limiting enabled
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention (SQLAlchemy ORM)
- [ ] XSS prevention (frontend)
- [ ] Sensitive data encrypted at rest

---

## Roadmap

| Phase | Features |
|-------|----------|
| v0.1 | Basic REST API, email channel, PostgreSQL storage |
| v0.2 | SMS + push channels, Celery async processing |
| v0.3 | Message templates, user preferences |
| v0.4 | Real-time WebSocket notifications |
| v0.5 | Admin dashboard (frontend) |
| v1.0 | Monitoring, analytics, multi-tenant support |
