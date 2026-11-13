import os
import json
from typing import AsyncGenerator, Any, List
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import TypeDecorator, String, Text
from sqlalchemy.pool import NullPool
from server.app.core.config import settings

_is_serverless = bool(
    os.environ.get("VERCEL")
    or os.environ.get("VERCEL_ENV")
    or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
    or not os.access(".", os.W_OK)
)

def get_clean_database_url() -> str:
    raw_url = os.environ.get("DATABASE_URL") or settings.DATABASE_URL or ""
    if not raw_url:
        return "sqlite+aiosqlite:////tmp/agentlink.db" if _is_serverless else "sqlite+aiosqlite:///./agentlink.db"
    
    # Normalize postgres:// and postgresql:// to postgresql+asyncpg://
    if raw_url.startswith("postgres://"):
        raw_url = "postgresql+asyncpg://" + raw_url[len("postgres://"):]
    elif raw_url.startswith("postgresql://") and not raw_url.startswith("postgresql+"):
        raw_url = "postgresql+asyncpg://" + raw_url[len("postgresql://"):]
        
    # Check if asyncpg is available for postgresql
    if "postgresql" in raw_url:
        try:
            import asyncpg  # noqa
        except ImportError:
            print("asyncpg not installed, falling back to SQLite in /tmp", flush=True)
            return "sqlite+aiosqlite:////tmp/agentlink.db"
            
    return raw_url

# Custom cross-platform Vector column type
class VectorType(TypeDecorator):
    """
    Stores 384-dimensional vectors.
    Uses pgvector's VECTOR(384) in PostgreSQL,
    and JSON serialized string in SQLite / other engines.
    """
    impl = Text
    cache_ok = True

    def __init__(self, dim: int = 384, **kwargs: Any):
        super().__init__(**kwargs)
        self.dim = dim

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            try:
                from pgvector.sqlalchemy import Vector
                return dialect.type_descriptor(Vector(self.dim))
            except ImportError:
                return dialect.type_descriptor(Text())
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, list):
            if dialect.name == "postgresql":
                return value
            return json.dumps(value)
        return value

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                return []
        if isinstance(value, list):
            return value
        return list(value)

class Base(DeclarativeBase):
    pass

_engine = None
_session_maker = None

def get_engine():
    global _engine
    if _engine is None:
        db_url = get_clean_database_url()
        connect_args = {}
        if "sqlite" in db_url:
            connect_args["check_same_thread"] = False
        try:
            _engine = create_async_engine(
                db_url,
                echo=False,
                connect_args=connect_args,
                poolclass=NullPool,
                future=True
            )
        except Exception as e:
            print(f"Error creating engine for {db_url}: {e}, falling back to SQLite /tmp", flush=True)
            _engine = create_async_engine(
                "sqlite+aiosqlite:////tmp/agentlink.db",
                echo=False,
                connect_args={"check_same_thread": False},
                poolclass=NullPool,
                future=True
            )
    return _engine

def get_session_maker():
    global _session_maker
    if _session_maker is None:
        _session_maker = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False
        )
    return _session_maker

class EngineProxy:
    def __getattr__(self, name):
        return getattr(get_engine(), name)

engine = EngineProxy()

class SessionMakerProxy:
    def __call__(self, *args, **kwargs):
        return get_session_maker()(*args, **kwargs)

AsyncSessionLocal = SessionMakerProxy()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db() -> None:
    eng = get_engine()
    async with eng.begin() as conn:
        if eng.dialect.name == "postgresql":
            try:
                from sqlalchemy import text
                await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))
                await conn.execute(text('CREATE EXTENSION IF NOT EXISTS vector;'))
            except Exception as ext_err:
                print(f"Postgres extension notice: {ext_err}", flush=True)
        await conn.run_sync(Base.metadata.create_all)
