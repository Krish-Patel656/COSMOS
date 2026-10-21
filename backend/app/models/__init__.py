"""ORM model registry.

Importing this module is what registers every mapper on ``Base.metadata``, so
``init_models`` and Alembic autogeneration both depend on it importing all model
modules.
"""

from app.models.astronomy import IngestRun, Planet, Star
from app.models.user import (
    Collection,
    CollectionItem,
    Favorite,
    SavedComparison,
    User,
)

__all__ = [
    "Collection",
    "CollectionItem",
    "Favorite",
    "IngestRun",
    "Planet",
    "SavedComparison",
    "Star",
    "User",
]
