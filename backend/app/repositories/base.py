from typing import Protocol, TypeVar, runtime_checkable

T = TypeVar("T")


@runtime_checkable
class EntityRepository(Protocol[T]):
    def add(self, key: str, entity: T) -> T: ...

    def get(self, key: str) -> T | None: ...

    def list(self) -> list[T]: ...

    def delete(self, key: str) -> None: ...