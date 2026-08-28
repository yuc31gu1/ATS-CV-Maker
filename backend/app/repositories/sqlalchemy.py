from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

T = TypeVar("T")


class SqlAlchemyRepository(Generic[T]):
    """DB-backed repository; a test/in-memory swap-in satisfies the same protocol."""

    def __init__(self, session: Session, model) -> None:
        self._session = session
        self._model = model

    def add(self, key: str, item: T) -> T:
        self._session.add(item)
        self._session.commit()
        return item

    def get(self, key: str) -> T | None:
        return self._session.get(self._model, key)

    def list(self) -> list[T]:
        return list(self._session.scalars(select(self._model)).all())

    def delete(self, key: str) -> None:
        item = self.get(key)
        if item is not None:
            self._session.delete(item)
            self._session.commit()