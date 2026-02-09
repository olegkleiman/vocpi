import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase

pg_password = os.getenv("PG_PASSWORD")
pg_username = os.getenv("PG_USERNAME")

DATABASE_URL = f"postgresql+asyncpg://{pg_username}:{pg_password}@voicp-instance.c2niqycso7s9.us-east-1.rds.amazonaws.com:5432/postgres"

engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600
)
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with SessionLocal() as session:
        yield session