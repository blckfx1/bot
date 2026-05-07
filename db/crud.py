from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import List, Optional

from db.models import User, Source, Post, PostTheme, UserSubscription, Theme


async def get_or_create_user(session: AsyncSession, tg_id: int) -> User:
    stmt = select(User).where(User.tg_id == tg_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        user = User(tg_id=tg_id)
        session.add(user)
        await session.commit()
    return user


async def get_user_subscriptions(session: AsyncSession, user_id: int) -> List[Source]:
    stmt = select(Source).join(UserSubscription).where(UserSubscription.user_id == user_id)
    result = await session.execute(stmt)
    return result.scalars().all()


async def add_subscription(session: AsyncSession, user_id: int, source_id: int) -> bool:
    existing = await session.execute(
        select(UserSubscription).where(UserSubscription.user_id == user_id, UserSubscription.source_id == source_id)
    )
    if existing.scalar_one_or_none():
        return False
    sub = UserSubscription(user_id=user_id, source_id=source_id)
    session.add(sub)
    await session.commit()
    return True


async def remove_subscription(session: AsyncSession, user_id: int, source_id: int):
    await session.execute(
        delete(UserSubscription).where(UserSubscription.user_id == user_id, UserSubscription.source_id == source_id)
    )
    await session.commit()


async def get_sources_by_theme(session: AsyncSession, theme_name: str, limit: int = 50) -> List[Source]:
    # Get theme id
    theme_stmt = select(Theme).where(Theme.name == theme_name)
    theme = await session.execute(theme_stmt)
    theme_obj = theme.scalar_one_or_none()
    if not theme_obj:
        return []
    # Sources that have this theme as override OR (if no override) we consider that any source can produce multiple themes.
    # For simplicity: we allow subscription to any source; theme filtering during classification.
    # But here we return sources that are likely to produce that theme: either override equals theme_id, or no override (then manual curation required).
    stmt = select(Source).where((Source.theme_override_id == theme_obj.id) | (Source.theme_override_id.is_(None)))
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_source(session: AsyncSession, source_id: int) -> Optional[Source]:
    return await session.get(Source, source_id)


async def get_sources_due_for_fetch(session: AsyncSession, current_time: datetime) -> List[Source]:
    stmt = select(Source).where(
        (current_time - Source.last_fetched).text(">= make_interval(secs => Source.update_interval_minutes * 60)")
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def update_source_last_fetched(session: AsyncSession, source_id: int, fetch_time: datetime):
    stmt = select(Source).where(Source.id == source_id)
    source = await session.execute(stmt)
    source = source.scalar_one()
    source.last_fetched = fetch_time
    await session.commit()


async def insert_post(session: AsyncSession, post_data: dict) -> Optional[Post]:
    # Check uniqueness
    existing = await session.execute(
        select(Post).where(Post.source_id == post_data["source_id"], Post.external_id == post_data["external_id"])
    )
    if existing.scalar_one_or_none():
        return None
    post = Post(**post_data)
    session.add(post)
    await session.commit()
    await session.refresh(post)
    return post


async def add_post_themes(session: AsyncSession, post_id: int, theme_names: List[str]):
    for tname in theme_names:
        theme_stmt = select(Theme).where(Theme.name == tname)
        theme = await session.execute(theme_stmt)
        theme_obj = theme.scalar_one_or_none()
        if theme_obj:
            pt = PostTheme(post_id=post_id, theme_id=theme_obj.id)
            session.add(pt)
    await session.commit()


async def get_subscribed_users_for_source(session: AsyncSession, source_id: int) -> List[User]:
    stmt = select(User).join(UserSubscription).where(UserSubscription.source_id == source_id)
    result = await session.execute(stmt)
    return result.scalars().all()