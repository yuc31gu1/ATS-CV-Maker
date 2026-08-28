import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories.in_memory import InMemoryRepository
from app.repositories.resume import InMemoryResumeRepository
from app.services.resume import ResumeService, get_resume_service
from app.storage.local import LocalStorageService


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def resume_service() -> ResumeService:
    service = ResumeService(InMemoryResumeRepository())
    app.dependency_overrides[get_resume_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_resume_service, None)


@pytest.fixture
def resume_client(client, resume_service) -> TestClient:
    return client


@pytest.fixture
def temp_storage(tmp_path) -> LocalStorageService:
    return LocalStorageService(tmp_path / "storage")


@pytest.fixture
def in_memory_repository() -> InMemoryRepository:
    return InMemoryRepository()