"""Per-user saved content: favourites, collections and comparisons."""

from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import joinedload, selectinload

from app.api.deps import CurrentUser, SessionDep
from app.models import Collection, CollectionItem, Favorite, Planet, SavedComparison, Star
from app.schemas.astronomy import PlanetWithStar, StarSummary
from app.schemas.user import (
    CollectionCreate,
    CollectionItemCreate,
    CollectionOut,
    CollectionUpdate,
    ComparisonCreate,
    ComparisonOut,
    FavoriteCreate,
    FavoriteOut,
)
from app.services.presentation import to_planet_card

router = APIRouter(prefix="/me", tags=["account"])


async def _assert_target_exists(session, target_type: str, slug: str) -> None:
    """Reject favourites pointing at things that do not exist.

    Without this a typo silently creates a dangling favourite that renders as a
    blank card forever.
    """
    model = Planet if target_type == "planet" else Star
    exists = await session.scalar(select(func.count()).where(model.slug == slug.lower()))
    if not exists:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no {target_type} with slug {slug!r}")


# --- Favourites -----------------------------------------------------------


@router.get("/favorites", response_model=list[FavoriteOut], summary="List favourites")
async def list_favorites(
    user: CurrentUser,
    session: SessionDep,
    target_type: Annotated[str | None, Query(pattern="^(planet|star)$")] = None,
) -> list[FavoriteOut]:
    statement = select(Favorite).where(Favorite.user_id == user.id)
    if target_type:
        statement = statement.where(Favorite.target_type == target_type)
    statement = statement.order_by(Favorite.created_at.desc())
    rows = (await session.execute(statement)).scalars().all()
    return [FavoriteOut.model_validate(row) for row in rows]


@router.post(
    "/favorites",
    response_model=FavoriteOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a favourite",
)
async def add_favorite(
    payload: FavoriteCreate, user: CurrentUser, session: SessionDep
) -> FavoriteOut:
    slug = payload.target_slug.lower()
    await _assert_target_exists(session, payload.target_type, slug)

    existing = (
        await session.execute(
            select(Favorite).where(
                Favorite.user_id == user.id,
                Favorite.target_type == payload.target_type,
                Favorite.target_slug == slug,
            )
        )
    ).scalars().first()
    if existing is not None:
        # Idempotent: starring something twice is a double-click, not an error.
        return FavoriteOut.model_validate(existing)

    favorite = Favorite(
        user_id=user.id,
        target_type=payload.target_type,
        target_slug=slug,
        note=payload.note,
    )
    session.add(favorite)
    await session.commit()
    await session.refresh(favorite)
    return FavoriteOut.model_validate(favorite)


@router.delete(
    "/favorites/{target_type}/{target_slug}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a favourite",
)
async def remove_favorite(
    target_type: str, target_slug: str, user: CurrentUser, session: SessionDep
) -> Response:
    if target_type not in ("planet", "star"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "target_type must be planet or star")
    await session.execute(
        delete(Favorite).where(
            Favorite.user_id == user.id,
            Favorite.target_type == target_type,
            Favorite.target_slug == target_slug.lower(),
        )
    )
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/favorites/planets",
    response_model=list[PlanetWithStar],
    summary="Favourited planets, resolved",
)
async def favorite_planets(user: CurrentUser, session: SessionDep) -> list[PlanetWithStar]:
    """Resolve favourited planet slugs to full records in one round trip."""
    slugs = (
        await session.execute(
            select(Favorite.target_slug).where(
                Favorite.user_id == user.id, Favorite.target_type == "planet"
            )
        )
    ).scalars().all()
    if not slugs:
        return []
    rows = (
        await session.execute(
            select(Planet)
            .options(joinedload(Planet.star))
            .where(Planet.slug.in_(slugs))
            .order_by(Planet.habitability_score.desc().nulls_last())
        )
    ).scalars().unique().all()
    return [to_planet_card(planet) for planet in rows]


@router.get(
    "/favorites/stars",
    response_model=list[StarSummary],
    summary="Favourited stars, resolved",
)
async def favorite_stars(user: CurrentUser, session: SessionDep) -> list[StarSummary]:
    slugs = (
        await session.execute(
            select(Favorite.target_slug).where(
                Favorite.user_id == user.id, Favorite.target_type == "star"
            )
        )
    ).scalars().all()
    if not slugs:
        return []
    rows = (
        await session.execute(
            select(Star).where(Star.slug.in_(slugs)).order_by(Star.distance_ly.asc().nulls_last())
        )
    ).scalars().all()
    return [StarSummary.model_validate(star) for star in rows]


# --- Collections ----------------------------------------------------------


async def _get_owned_collection(session, user_id: int, collection_id: int) -> Collection:
    collection = (
        await session.execute(
            select(Collection)
            .options(selectinload(Collection.items))
            .where(Collection.id == collection_id, Collection.user_id == user_id)
            # The session is configured with expire_on_commit=False, so without
            # populate_existing a re-read after inserting an item would return the
            # identity-mapped instance with its stale (pre-insert) items list — the
            # new item would be saved but invisible in the response.
            .execution_options(populate_existing=True)
        )
    ).scalars().first()
    if collection is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "collection not found")
    return collection


@router.get("/collections", response_model=list[CollectionOut], summary="List collections")
async def list_collections(user: CurrentUser, session: SessionDep) -> list[CollectionOut]:
    rows = (
        await session.execute(
            select(Collection)
            .options(selectinload(Collection.items))
            .where(Collection.user_id == user.id)
            .order_by(Collection.updated_at.desc())
        )
    ).scalars().all()
    return [CollectionOut.model_validate(row) for row in rows]


@router.post(
    "/collections",
    response_model=CollectionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a collection",
)
async def create_collection(
    payload: CollectionCreate, user: CurrentUser, session: SessionDep
) -> CollectionOut:
    duplicate = await session.scalar(
        select(func.count())
        .select_from(Collection)
        .where(Collection.user_id == user.id, Collection.name == payload.name)
    )
    if duplicate:
        raise HTTPException(status.HTTP_409_CONFLICT, "you already have a collection with that name")

    collection = Collection(
        user_id=user.id,
        name=payload.name,
        description=payload.description,
        is_public=payload.is_public,
        share_token=secrets.token_urlsafe(32) if payload.is_public else None,
    )
    session.add(collection)
    await session.commit()
    return CollectionOut.model_validate(
        await _get_owned_collection(session, user.id, collection.id)
    )


@router.patch(
    "/collections/{collection_id}", response_model=CollectionOut, summary="Update a collection"
)
async def update_collection(
    collection_id: int, payload: CollectionUpdate, user: CurrentUser, session: SessionDep
) -> CollectionOut:
    collection = await _get_owned_collection(session, user.id, collection_id)

    if payload.name is not None:
        collection.name = payload.name
    if payload.description is not None:
        collection.description = payload.description
    if payload.is_public is not None:
        collection.is_public = payload.is_public
        # Minting the token on first publish, and dropping it on unpublish,
        # means an old share link stops working rather than silently resuming if
        # the collection is made public again later.
        collection.share_token = secrets.token_urlsafe(32) if payload.is_public else None

    await session.commit()
    return CollectionOut.model_validate(
        await _get_owned_collection(session, user.id, collection_id)
    )


@router.delete(
    "/collections/{collection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a collection",
)
async def delete_collection(
    collection_id: int, user: CurrentUser, session: SessionDep
) -> Response:
    collection = await _get_owned_collection(session, user.id, collection_id)
    await session.delete(collection)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/collections/{collection_id}/items",
    response_model=CollectionOut,
    summary="Add an item to a collection",
)
async def add_collection_item(
    collection_id: int,
    payload: CollectionItemCreate,
    user: CurrentUser,
    session: SessionDep,
) -> CollectionOut:
    collection = await _get_owned_collection(session, user.id, collection_id)
    slug = payload.target_slug.lower()
    await _assert_target_exists(session, payload.target_type, slug)

    if any(
        item.target_type == payload.target_type and item.target_slug == slug
        for item in collection.items
    ):
        return CollectionOut.model_validate(collection)

    session.add(
        CollectionItem(
            collection_id=collection.id,
            target_type=payload.target_type,
            target_slug=slug,
            note=payload.note,
            position=len(collection.items),
        )
    )
    await session.commit()
    return CollectionOut.model_validate(
        await _get_owned_collection(session, user.id, collection_id)
    )


@router.delete(
    "/collections/{collection_id}/items/{item_id}",
    response_model=CollectionOut,
    summary="Remove an item from a collection",
)
async def remove_collection_item(
    collection_id: int, item_id: int, user: CurrentUser, session: SessionDep
) -> CollectionOut:
    await _get_owned_collection(session, user.id, collection_id)
    await session.execute(
        delete(CollectionItem).where(
            CollectionItem.id == item_id, CollectionItem.collection_id == collection_id
        )
    )
    await session.commit()
    return CollectionOut.model_validate(
        await _get_owned_collection(session, user.id, collection_id)
    )


# --- Saved comparisons ----------------------------------------------------


@router.get("/comparisons", response_model=list[ComparisonOut], summary="List saved comparisons")
async def list_comparisons(user: CurrentUser, session: SessionDep) -> list[ComparisonOut]:
    rows = (
        await session.execute(
            select(SavedComparison)
            .where(SavedComparison.user_id == user.id)
            .order_by(SavedComparison.created_at.desc())
        )
    ).scalars().all()
    return [ComparisonOut.model_validate(row) for row in rows]


@router.post(
    "/comparisons",
    response_model=ComparisonOut,
    status_code=status.HTTP_201_CREATED,
    summary="Save a comparison",
)
async def save_comparison(
    payload: ComparisonCreate, user: CurrentUser, session: SessionDep
) -> ComparisonOut:
    slugs = [slug.lower() for slug in dict.fromkeys(payload.planet_slugs)]
    if len(slugs) < 2:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "need at least two distinct planets")

    found = (
        await session.execute(select(Planet.slug).where(Planet.slug.in_(slugs)))
    ).scalars().all()
    missing = set(slugs) - set(found)
    if missing:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"unknown planet slug(s): {', '.join(sorted(missing))}"
        )

    comparison = SavedComparison(
        user_id=user.id,
        name=payload.name,
        planet_slugs=slugs,
        share_token=secrets.token_urlsafe(32),
    )
    session.add(comparison)
    await session.commit()
    await session.refresh(comparison)
    return ComparisonOut.model_validate(comparison)


@router.delete(
    "/comparisons/{comparison_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a saved comparison",
)
async def delete_comparison(
    comparison_id: int, user: CurrentUser, session: SessionDep
) -> Response:
    comparison = (
        await session.execute(
            select(SavedComparison).where(
                SavedComparison.id == comparison_id, SavedComparison.user_id == user.id
            )
        )
    ).scalars().first()
    if comparison is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "comparison not found")
    await session.delete(comparison)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
