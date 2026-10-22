"""Shared FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import CacheBackend, get_cache
from app.core.security import decode_token
from app.db.session import get_session
from app.models import User

# auto_error=False so optional-auth endpoints can distinguish "no credentials"
# from "bad credentials" instead of 403-ing anonymous visitors.
_bearer = HTTPBearer(auto_error=False, description="JWT access token")

SessionDep = Annotated[AsyncSession, Depends(get_session)]
CacheDep = Annotated[CacheBackend, Depends(get_cache)]
_CredentialsDep = Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user_optional(
    session: SessionDep, credentials: _CredentialsDep = None
) -> User | None:
    """Resolve the signed-in user, or ``None`` for anonymous requests."""
    if credentials is None or not credentials.credentials:
        return None
    subject = decode_token(credentials.credentials)
    if subject is None:
        return None
    try:
        user_id = int(subject)
    except ValueError:
        return None
    user = await session.get(User, user_id)
    return user if user and user.is_active else None


async def get_current_user(
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> User:
    """Require an authenticated, active user."""
    if user is None:
        raise _UNAUTHORIZED
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_current_user_optional)]


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()
