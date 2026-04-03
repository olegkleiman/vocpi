# Stage 1: Documentation Builder
FROM python:3.11-slim AS docs_builder
WORKDIR /docs_gen
COPY docs/ .
# Run your doc generator (e.g., Sphinx or MkDocs)
RUN pip install mkdocs && mkdocs build

# Stage 2: Final Production Image
FROM python:3.11-slim 

# Create a non-privileged user for security
RUN useradd -m vocpiuser

WORKDIR /app

# Install libpq (Postgres client libs) and a C compiler so psycopg can build if needed
RUN apt-get update \
	&& apt-get install -y --no-install-recommends gcc libpq-dev \
	&& rm -rf /var/lib/apt/lists/*

# 1. Copy ONLY the requirements first
COPY requirements.txt . 

RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
	&& pip install --no-cache-dir -r requirements.txt \
	&& rm -rf /root/.cache/pip

# 2. Install dependencies (this layer is cached until requirements.txt changes)
RUN pip install --no-cache-dir -r requirements.txt 

COPY . . 

EXPOSE 8000 

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]