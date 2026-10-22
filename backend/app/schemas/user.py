"""Request and response schemas for accounts and saved content."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Auth -----------------------------------------------------------------


class UserCreate(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=10, max_length=128)

    @field_validator("password")
    @classmethod
    def _password_strength(cls, value: str) -> str:
        """Reject passwords that are long but trivially guessable.

        A length floor alone lets "passwordpassword" through, so also require
        some variety of character classes.
        """
        classes = sum(
            (
                any(c.islower() for c in value),
                any(c.isupper() for c in value),
                any(c.isdigit() for c in value),
                any(not c.isalnum() for c in value),
            )
        )
        if classes < 2:
            raise ValueError(
                "password must combine at least two of: lowercase, uppercase, digits, symbols"
            )
        return value


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(ORMModel):
    id: int
    email: EmailStr
    display_name: str
    created_at: datetime


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token lifetime in seconds")
    user: UserOut


class RefreshRequest(BaseModel):
    refresh_token: str


# --- Favourites -----------------------------------------------------------

TargetType = str


class FavoriteCreate(BaseModel):
    target_type: TargetType = Field(pattern="^(planet|star)$")
    target_slug: str = Field(min_length=1, max_length=180)
    note: str | None = Field(default=None, max_length=1000)


class FavoriteOut(ORMModel):
    id: int
    target_type: str
    target_slug: str
    note: str | None
    created_at: datetime


# --- Collections ----------------------------------------------------------


class CollectionItemCreate(BaseModel):
    target_type: TargetType = Field(pattern="^(planet|star)$")
    target_slug: str = Field(min_length=1, max_length=180)
    note: str | None = Field(default=None, max_length=1000)


class CollectionItemOut(ORMModel):
    id: int
    target_type: str
    target_slug: str
    position: int
    note: str | None


class CollectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    is_public: bool = False


class CollectionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    is_public: bool | None = None


class CollectionOut(ORMModel):
    id: int
    name: str
    description: str | None
    is_public: bool
    share_token: str | None
    items: list[CollectionItemOut]
    created_at: datetime
    updated_at: datetime


# --- Saved comparisons ----------------------------------------------------


class ComparisonCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    planet_slugs: list[str] = Field(min_length=2, max_length=4)


class ComparisonOut(ORMModel):
    id: int
    name: str
    planet_slugs: list[str]
    share_token: str | None
    created_at: datetime
