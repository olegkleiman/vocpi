import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.exc import DisconnectionError, OperationalError
import urllib.parse
from sqlalchemy import select
from aiocache import cached
from aiocache.serializers import PickleSerializer

from .models.sqlalchemy.models import OCPILocation, EVSEModel, OCPIPartnerModel
from .exceptions import PartnerNotFoundError

raw_password = os.getenv("PG_PASSWORD")
if not raw_password:
    raise ValueError("DB password is missing!")

pg_username = os.getenv("PG_USERNAME", "postgres")
if not pg_username:
    raise ValueError("DB username is missing!")

pg_host = os.getenv("PG_HOST")
if not pg_host:
    raise ValueError("DB host is missing!")

pg_port = os.getenv("PG_PORT")
if not pg_port:
    raise ValueError("DB port is missing!")

pg_db = os.getenv("PG_DB")
if not pg_db:
    raise ValueError("DB name is missing!")

pg_useSSL= os.getenv("PG_USE_SSL")
if not pg_useSSL:
    raise ValueError("DB SSL setting is missing!")

safe_password = urllib.parse.quote_plus(raw_password)
pg_password = safe_password

DATABASE_URL = f"postgresql+psycopg://{pg_username}:{pg_password}@{pg_host}:{pg_port}/{pg_db}"

engine = create_async_engine(
    DATABASE_URL,
    pool_size=5,        # Number of permanent connections
    max_overflow=10,    # How many extra can be opened during peaks
    pool_pre_ping=True, 
    pool_recycle=300,   # Close connections after 5 mins
    connect_args={
        "connect_timeout": 10,
        "gssencmode": "disable",  # Skips GSSAPI negotiation lag
        "application_name": "vocpi_app",
        "keepalives": 1,
        "keepalives_idle": 60,
        "keepalives_interval": 10,
        "keepalives_count": 5,
        "sslmode": pg_useSSL
    }
)
SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

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


@cached(ttl=600, key="{location_id}:{evse_id}", serializer=PickleSerializer())
async def get_partner(db,
                    location_id: str,
                    evse_id: str) :
            
        # select * from ocpi_partners p
        # JOIN ocpi_locations l 
        # ON p.id = l.partner_id 
        # JOIN ocpi_evses e
        # ON l.id = e.location_id
        # where l.location_id = 'xxx'
        # and e.evse_id = 'yyy'

        stmt = (
            select(OCPIPartnerModel)
            .join(OCPILocation, OCPIPartnerModel.id == OCPILocation.partner_id)
            .join(EVSEModel, OCPILocation.id== EVSEModel.location_id)  
            .where(OCPILocation.location_id == location_id,
                   EVSEModel.evse_id == evse_id)
        )

        result = await db.execute(stmt)
        partner_row = result.first()

        if not partner_row:
            raise PartnerNotFoundError(f"Partner not found for location {location_id}, evse {evse_id}")

        partner_object = partner_row[0]
        return partner_object.base_url, partner_object.token, partner_object.version

async def save_tariff():
    pass
