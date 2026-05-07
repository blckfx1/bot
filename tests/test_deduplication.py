import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from db.models import Base, Post, Source
from db.crud import insert_post

DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture
async def session():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as sess:
        yield sess
    await engine.dispose()

async def test_insert_duplicate(session):
    src = Source(platform="tg", external_id="chan", title="Chan")
    session.add(src)
    await session.commit()
    post_data = {
        "source_id": src.id,
        "external_id": "123",
        "title": "Title",
        "text": "Text",
        "media_urls": [],
        "publish_time": None
    }
    p1 = await insert_post(session, post_data)
    assert p1 is not None
    p2 = await insert_post(session, post_data)
    assert p2 is None