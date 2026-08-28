from collections.abc import Callable
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

T = TypeVar("T")

Row = TypeVar("Row")


class SqlAlchemyRepository(Generic[T]):
    """DB-backed repository that maps domain entities to SQLAlchemy rows.

    ``to_row``/``from_row`` converters bridge the pydantic domain object and
    the ORM row (see ``app.repositories.mappers``); ``add`` upserts by key so
    services can both create and update through one call.
    """

    def __init__(
        self,
        session: Session,
        model,
        to_row: Callable[[T], Row],
        from_row: Callable[[Row], T],
    ) -> None:
        self._session = session
        self._model = model
        self._to_row = to_row
        self._from_row = from_row

    def add(self, key: str, item: T) -> T:
        row = self._to_row(item)
        if self._session.get(self._model, key) is None:
            self._session.add(row)
        else:
            row = self._session.merge(row)
        self._session.commit()
        return self._from_row(row)

    def get(self, key: str) -> T | None:
        row = self._session.get(self._model, key)
        return self._from_row(row) if row is not None else None

    def list(self) -> list[T]:
        return [self._from_row(row) for row in self._session.scalars(select(self._model)).all()]

    def delete(self, key: str) -> None:
        row = self._session.get(self._model, key)
        if row is not None:
            self._session.delete(row)
            self._session.commit()
