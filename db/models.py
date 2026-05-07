from sqlalchemy import (
    Column, Integer, String, DateTime, Text, ForeignKey, Table, Index
)
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class Theme(Base):
    __tablename__ = "themes"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)


class Source(Base):
    __tablename__ = "sources"
    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255))
    theme_override_id: Mapped[int | None] = mapped_column(ForeignKey("themes.id"))
    last_fetched: Mapped[datetime] = mapped_column(default=datetime(1970, 1, 1))
    update_interval_minutes: Mapped[int] = mapped_column(default=360)  # default 6h

    theme_override = relationship("Theme")
    __table_args__ = (Index("ix_sources_platform_external", "platform", "external_id", unique=True),)


class Post(Base):
    __tablename__ = "posts"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"))
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    text: Mapped[str | None] = mapped_column(Text)
    media_urls: Mapped[list[str] | None] = mapped_column(Text)  # store as JSON string or array; simplified
    publish_time: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    source = relationship("Source")
    __table_args__ = (Index("ix_posts_source_external", "source_id", "external_id", unique=True),
                      Index("ix_posts_publish_time", "publish_time"),)


class PostTheme(Base):
    __tablename__ = "post_themes"
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), primary_key=True)
    theme_id: Mapped[int] = mapped_column(ForeignKey("themes.id"), primary_key=True)


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), primary_key=True)