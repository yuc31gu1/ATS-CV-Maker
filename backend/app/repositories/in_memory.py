from typing import Generic, TypeVar

T = TypeVar("T")


class InMemoryRepository(Generic[T]):
    """In-memory repository for unit tests; DB-backed repos swap in later."""

    def __init__(self) -> None:
        self._items: dict[str, T] = {}

    def add(self, key: str, item: T) -> T:
        self._items[key] = item
        return item

    def get(self, key: str) -> T | None:
        return self._items.get(key)

    def list(self) -> list[T]:
        return list(self._items.values())

    def delete(self, key: str) -> None:
        self._items.pop(key, None)

    def clear(self) -> None:
        self._items.clear()