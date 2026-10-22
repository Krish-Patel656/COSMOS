"""Registration, login and token refresh."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, SessionDep, get_user_by_email
from app.core.config import settings
from app.core.security import (
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models import User
from app.schemas.user import (
    RefreshRequest,
    TokenPair,
    UserCreate,
    UserLogin,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])

_INVALID_CREDENTIALS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Incorrect email or password",
    headers={"WWW-Authenticate": "Bearer"},
)


def _token_pair(user: User) -> TokenPair:
    return TokenPair(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserOut.model_validate(user),
    )


@router.post(
    "/register",
    response_model=TokenPair,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account",
)
async def register(payload: UserCreate, session: SessionDep) -> TokenPair:
    email = payload.email.lower()
    if await get_user_by_email(session, email):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "an account with that email already exists"
        )

    user = User(
        email=email,
        display_name=payload.display_name.strip(),
        hashed_password=hash_password(payload.password),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return _token_pair(user)


@router.post("/login", response_model=TokenPair, summary="Sign in")
async def login(payload: UserLogin, session: SessionDep) -> TokenPair:
    user = await get_user_by_email(session, payload.email)
    # Verify a hash even when the user does not exist, so that response timing
    # does not reveal whether an email is registered.
    hashed = user.hashed_password if user else hash_password("timing-equalising-placeholder")
    password_ok = verify_password(payload.password, hashed)

    if user is None or not password_ok or not user.is_active:
        raise _INVALID_CREDENTIALS
    return _token_pair(user)


@router.post("/refresh", response_model=TokenPair, summary="Exchange a refresh token")
async def refresh(payload: RefreshRequest, session: SessionDep) -> TokenPair:
    subject = decode_token(payload.refresh_token, expected_type=REFRESH_TOKEN_TYPE)
    if subject is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid or expired refresh token")
    try:
        user = await session.get(User, int(subject))
    except ValueError:
        user = None
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid or expired refresh token")
    return _token_pair(user)


@router.get("/me", response_model=UserOut, summary="The signed-in user")
async def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)
