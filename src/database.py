import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase

pg_password = os.getenv("PG_PASSWORD")
pg_username = os.getenv("PG_USERNAME")

DATABASE_URL = f"postgresql+asyncpg://{pg_username}:{pg_password}@voicp-instance.c2niqycso7s9.us-east-1.rds.amazonaws.com:5432/postgres"

engine = create_async_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with SessionLocal() as session:
        yield session