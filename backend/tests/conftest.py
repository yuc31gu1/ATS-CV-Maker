import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories.in_memory import InMemoryRepository
from app.storage.local import LocalStorageService


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def temp_storage(tmp_path) -> LocalStorageService:
    return LocalStorageService(tmp_path / "storage")


@pytest.fixture
def in_memory_repository() -> InMemoryRepository:
    return InMemoryRepository()