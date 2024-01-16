from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base, DeclarativeBase
from bot.config import config
from os import getenv
user = getenv("PG_USER")
password = getenv("PG_PASSWORD")
database = getenv("PG_DB")
host = getenv("PG_HOST")
port = getenv("PG_PORT")
url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"
print(url)

if host is not None:
    engine = create_async_engine(
        url
    )
else:
    engine = None
Base: DeclarativeBase = declarative_base()
asession_maker: async_sessionmaker[AsyncSession] = async_sessionmaker(bind=engine)


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def init():
    await create_tables()