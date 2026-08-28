import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def temp_storage(tmp_path):
    from app.storage.local import LocalStorageService

    return LocalStorageService(tmp_path / "storage")


@pytest.fixture
def in_memory_repository():
    from app.repositories.in_memory import InMemoryRepository

    return InMemoryRepository()