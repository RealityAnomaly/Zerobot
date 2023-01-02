from asyncio import current_task

from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine
from zerobot.db.models import Base
from zerobot.utils.state import state_path

from sqlalchemy.ext.asyncio import async_scoped_session
from sqlalchemy.ext.asyncio import AsyncSession

engine = None
session = None

async def init_engine():
    global engine
    if engine is not None:
        return
    
    data_dir = state_path()
    db_path = data_dir.joinpath("db.sqlite").resolve()
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", future=True)

    # create session object
    global session
    session = async_scoped_session(sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        class_=AsyncSession
    ), scopefunc=current_task)

    # run creation query
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

def get_session() -> AsyncSession:
    global session
    return session()
