# Auth API

A RESTful authentication API built with FastAPI, SQLAlchemy, and PostgreSQL. Provides user registration, JWT-based login, and user management endpoints.

---

## Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI 0.135 |
| ORM | SQLAlchemy 2.0 |
| Database | PostgreSQL (SQLite for testing) |
| Auth | python-jose (JWT / HS256) |
| Password hashing | Argon2 (argon2-cffi) |
| Validation | Pydantic v2 |
| Server | Uvicorn |

---

## Setup

### 1. Create and activate virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql+psycopg2://<user>:<password>@<host>:5432/<dbname>
SECRET_KEY=<your-secret-key>
```

### 4. Run the development server

```bash
uvicorn app.main:app --reload
```

Interactive docs available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## Running Tests

```bash
pytest tests/
pytest tests/test_auth.py  # single file
```

Tests use an in-memory SQLite database and override the DB dependency automatically via `conftest.py`.

