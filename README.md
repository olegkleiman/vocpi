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

DB access my be configured to use Supabase: https://supabase.com/dashboard/project/ihlyyhcigfxxqxdjchkj
or any other PG on cloud or local container

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

### Provisioning
- Create EC2 instance with key pair and save .pem locally.
- Include public IP to the settings of this instance.

Theoretically, all deployment steps bellow could be accompilshed with SSH client (with .pem), but use MobaXTerm for more comfortable experience.

2. Install git at the targer EC2
2. Clone the repository (at the root) 
2.1. cd vocpi\

3. Docker
Optional (OpenTelemetry with Jaegger)
(Optional, from ~/vocpi) 4.1  docker run -d --name otel-collector --network vocpi-net -p 4317:4317 -p 4318:4318 -v $(pwd)/otel/otel-collector.yaml:/etc/otelcol-contrib/config.yaml otel/opentelemetry-collector-contrib:latest
(Optional) 4.2. docker network create vocpi-net
(Optional) 4.3. docker run -d --name jaeger --network vocpi-net -p 16686:16686 jaegertracing/all-in-one:latest

4.3. docker build -t vocpi-image .
4.4. docker run -d --name vocpi-container -p 8000:8000 -e OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317 --env-file .env vocpi-image
4.5. docker network connect vocpi-net vocpi-container || true
4.6. Test it: curl http://3.120.176.1:8000/docs

5. With nginx
5.1. Install nginx at the targer EC2


## License

MIT


