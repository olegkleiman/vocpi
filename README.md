# VOCPI - OCPI Implementation

FastAPI-based implementation of OCPI 2.2.1 (Open Charge Point Interface) for electric vehicle charging stations in Israel.

## Features

- Token authorization
- Session management
- Partner management
- PostgreSQL with async SQLAlchemy
- Connection pooling for performance

## Requirements

- Python 3.13+
- PostgreSQL

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Set environment variables:

```bash
export PG_USERNAME=your_username
export PG_PASSWORD=your_password
export DEFAULT_PARTNER_ID=your_partner_id
```

## Database Setup

Run SQL migrations in `src/sql/`:

```bash
psql -h your-host -U your-user -d postgres -f src/sql/partners.sql
psql -h your-host -U your-user -d postgres -f src/sql/tokens.sql
psql -h your-host -U your-user -d postgres -f src/sql/sessions.sql
```

## Running

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8080 --reload
```

## API Endpoints

- `GET /docs` - Swagger API documentation

## Project Structure

```
vocpi/
├── src/
│   ├── main.py           # FastAPI app
│   ├── router.py         # Route registration
│   ├── database.py       # DB connection
│   ├── models.py         # SQLAlchemy models
│   ├── cache.py          # Valkey client
│   ├── routes/
│   │   └── modules/
│   │       ├── tokens/
│   │       └── sessions/
│   └── sql/              # Database schemas
└── requirements.txt
```

## License

MIT
