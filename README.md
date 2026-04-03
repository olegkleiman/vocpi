# VOCPI - OCPI Implementation

FastAPI-based implementation of OCPI 2.2.1 (Open Charge Point Interface) for electric vehicle charging stations in Israel.

## Features

- Token authorization
- Session management
- Partner management
- PostgreSQL with async SQLAlchemy
- Connection pooling for performance

## Requirements

- Python 3.11+
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
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
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

## How to deploy (to EC2)
1. Theoretically, it could be accompilshed with SSH client (with .pem), but use MobaXTerm for more comfortable experience
2. Install git at the targer EC2
3. Clone the repository (at the root) 
3.1. cd vocpi\
4. docker build -t vocpi-image .
5. docker run -d --name vocpi-container -p 8000:8000 --env-file .env vocpi-image
6. Test it: curl http://3.120.176.1:8000/docs


## License

MIT


