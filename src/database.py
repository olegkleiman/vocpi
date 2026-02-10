import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.exc import DisconnectionError, OperationalError

pg_password = os.getenv("PG_PASSWORD")
pg_username = os.getenv("PG_USERNAME")

if not pg_password or not pg_username:
    raise ValueError("PG_PASSWORD and PG_USERNAME environment variables must be set")

DATABASE_URL = f"postgresql+asyncpg://{pg_username}:{pg_password}@voicp-instance.c2niqycso7s9.us-east-1.rds.amazonaws.com:5432/postgres"

engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={
        "server_settings": {
            "application_name": "vocpi_app",
            "tcp_keepalives_idle": "60",
            "tcp_keepalives_interval": "10",
            "tcp_keepalives_count": "5"
        }
    }
)
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db():
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            async with SessionLocal() as session:
                yield session
                break
        except (DisconnectionError, OperationalError) as e:
            if attempt == max_retries - 1:
                raise e
            await asyncio.sleep(retry_delay * (2 ** attempt))
        except Exception as e:
            raise e