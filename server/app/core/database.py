import json
from typing import AsyncGenerator, Any, List
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import TypeDecorator, String, Text
from sqlalchemy.pool import NullPool
from server.app.core.config import settings

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

# Database Engine
connect_args = {}
if "sqlite" in settings.DATABASE_URL:
    connect_args["check_same_thread"] = False

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args=connect_args,
    poolclass=NullPool,
    future=True
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db() -> None:
    async with engine.begin() as conn:
        # If postgres, enable uuid and vector extensions
        if engine.dialect.name == "postgresql":
            from sqlalchemy import text
            await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))
            await conn.execute(text('CREATE EXTENSION IF NOT EXISTS vector;'))
        await conn.run_sync(Base.metadata.create_all)

