"""Database architecture base abstractions.

Provides repository interfaces to isolate database storage implementation
from core agent application logic.
"""

from abc import ABC, abstractmethod
from typing import Any, Generic, List, Optional, TypeVar

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """Abstract generic repository interface for data persistence operations."""

    @abstractmethod
    def get_by_id(self, entity_id: str) -> Optional[T]:
        """Retrieve an entity by its unique identifier.

        Args:
            entity_id: The unique identifier.

        Returns:
            Entity instance if found, None otherwise.
        """
        pass

    @abstractmethod
    def get_all(self) -> List[T]:
        """Retrieve all entities in the repository.

        Returns:
            List of entities.
        """
        pass

    @abstractmethod
    def save(self, entity: T) -> T:
        """Persist a new or updated entity.

        Args:
            entity: Entity to save.

        Returns:
            Saved entity.
        """
        pass

    @abstractmethod
    def delete(self, entity_id: str) -> bool:
        """Delete an entity by its unique identifier.

        Args:
            entity_id: Unique identifier of entity to delete.

        Returns:
            True if entity was deleted, False otherwise.
        """
        pass
