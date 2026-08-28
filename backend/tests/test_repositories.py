from app.repositories.base import EntityRepository


def test_in_memory_repository_roundtrip(in_memory_repository):
    in_memory_repository.add("resume-1", {"id": "resume-1", "name": "Ada"})
    assert in_memory_repository.get("resume-1") == {"id": "resume-1", "name": "Ada"}
    assert len(in_memory_repository.list()) == 1
    in_memory_repository.delete("resume-1")
    assert in_memory_repository.get("resume-1") is None


def test_in_memory_repository_missing_key_returns_none(in_memory_repository):
    assert in_memory_repository.get("nope") is None


def test_in_memory_repository_satisfies_repository_protocol(in_memory_repository):
    assert isinstance(in_memory_repository, EntityRepository)