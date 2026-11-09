from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings


def _is_postgres() -> bool:
    return settings.DATABASE_URL.startswith("postgresql")


def _uses_transaction_pooler() -> bool:
    url = settings.DATABASE_URL.lower()
    return "pooler.supabase.com" in url or "pgbouncer" in url or ":6543/" in url


def _engine_options() -> dict:
    options: dict = {"echo": False}
    if _is_postgres():
        options["pool_pre_ping"] = True
        # PgBouncer in transaction mode cannot keep server-side prepared
        # statements alive between transactions. asyncpg's client-side
        # statement cache must be disabled, or queries fail intermittently.
        if settings.DB_DISABLE_PREPARED_STATEMENTS or _uses_transaction_pooler():
            options["connect_args"] = {
                "statement_cache_size": 0,
                "timeout": settings.DB_CONNECT_TIMEOUT_SECONDS,
            }
    return options


engine = create_async_engine(settings.DATABASE_URL, **_engine_options())

AsyncSessionLocal = async_sessionmaker(
    engine, expire_on_commit=False
)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def check_database() -> None:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
