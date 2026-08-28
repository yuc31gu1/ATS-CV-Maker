from typing import Protocol, TypeVar

from app.db import Base

T = TypeVar("T", bound=Base)


class EntityRepository(Protocol[T]):
    def add(self, entity: T) -> T: ...

    def get(self, entity_id: str) -> T | None: ...

    def list(self) -> list[T]: ...

    def delete(self, entity_id: str) -> None: ...