"""ORM models for accounts, favourites, collections and saved comparisons."""

from __future__ import annotations

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    favorites: Mapped[list[Favorite]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    collections: Mapped[list[Collection]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    comparisons: Mapped[list[SavedComparison]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Favorite(Base, TimestampMixin):
    """A starred planet or star.

    Target identity is stored as a (type, slug) pair rather than two nullable
    foreign keys: slugs are stable across re-ingestion while surrogate ids are
    not, so a favourite survives a full catalogue refresh.
    """

    __tablename__ = "favorites"
    __table_args__ = (
        UniqueConstraint("user_id", "target_type", "target_slug", name="uq_favorite_target"),
        CheckConstraint("target_type IN ('planet', 'star')", name="ck_favorite_target_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    target_type: Mapped[str] = mapped_column(String(16), nullable=False)
    target_slug: Mapped[str] = mapped_column(String(180), index=True, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped[User] = relationship(back_populates="favorites")


class Collection(Base, TimestampMixin):
    """A user-curated set of planets and stars, e.g. "worlds to watch"."""

    __tablename__ = "collections"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_collection_name_per_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    share_token: Mapped[str | None] = mapped_column(
        String(43), unique=True, index=True, nullable=True
    )

    user: Mapped[User] = relationship(back_populates="collections")
    items: Mapped[list[CollectionItem]] = relationship(
        back_populates="collection",
        cascade="all, delete-orphan",
        order_by="CollectionItem.position",
        lazy="selectin",
    )


class CollectionItem(Base, TimestampMixin):
    __tablename__ = "collection_items"
    __table_args__ = (
        UniqueConstraint(
            "collection_id", "target_type", "target_slug", name="uq_collection_item"
        ),
        CheckConstraint("target_type IN ('planet', 'star')", name="ck_item_target_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    collection_id: Mapped[int] = mapped_column(
        ForeignKey("collections.id", ondelete="CASCADE"), index=True, nullable=False
    )
    target_type: Mapped[str] = mapped_column(String(16), nullable=False)
    target_slug: Mapped[str] = mapped_column(String(180), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    collection: Mapped[Collection] = relationship(back_populates="items")


class SavedComparison(Base, TimestampMixin):
    """A saved side-by-side comparison of two to four worlds."""

    __tablename__ = "saved_comparisons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    planet_slugs: Mapped[list] = mapped_column(JSON, nullable=False)
    share_token: Mapped[str | None] = mapped_column(
        String(43), unique=True, index=True, nullable=True
    )

    user: Mapped[User] = relationship(back_populates="comparisons")
