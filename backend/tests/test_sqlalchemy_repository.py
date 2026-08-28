from datetime import UTC, datetime

import pytest
from pydantic import BaseModel
from sqlalchemy import String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.domain.analysis import (
    Importance,
    JobAnalysis,
    JobDescription,
    JobRequirement,
    RequirementCategory,
)
from app.domain.jobs import Job
from app.domain.matching import EvidenceMatch, MatchResult, MatchStatus
from app.repositories import mappers
from app.repositories.sqlalchemy import SqlAlchemyRepository


def now() -> datetime:
    return datetime(2026, 8, 28, 12, 0, 0, tzinfo=UTC)


class RepoBase(DeclarativeBase):
    pass


class ItemRow(RepoBase):
    __tablename__ = "items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[int] = mapped_column(nullable=False)


class Item(BaseModel):
    id: str
    name: str
    value: int


def item_to_row(entity: Item) -> ItemRow:
    return ItemRow(id=entity.id, name=entity.name, value=entity.value)


def item_from_row(row: ItemRow) -> Item:
    return Item(id=row.id, name=row.name, value=row.value)


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite://")
    RepoBase.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()


@pytest.fixture
def repo(session: Session) -> SqlAlchemyRepository[Item]:
    return SqlAlchemyRepository(session, ItemRow, item_to_row, item_from_row)


def test_repository_roundtrip_maps_domain_objects(repo: SqlAlchemyRepository[Item]):
    item = Item(id="item-1", name="Ada", value=7)

    stored = repo.add("item-1", item)

    assert stored == item
    fetched = repo.get("item-1")
    assert fetched == item
    assert fetched is not item
    assert [r.id for r in repo.list()] == ["item-1"]
    repo.delete("item-1")
    assert repo.get("item-1") is None


def test_repository_add_upserts_existing_row(repo: SqlAlchemyRepository[Item]):
    repo.add("item-1", Item(id="item-1", name="Ada", value=1))
    repo.add("item-1", Item(id="item-1", name="Ada", value=2))

    stored = repo.get("item-1")
    assert stored.value == 2
    assert len(repo.list()) == 1


def test_repository_get_missing_returns_none(repo: SqlAlchemyRepository[Item]):
    assert repo.get("missing") is None


def test_job_description_mapper_roundtrip():
    entity = JobDescription(
        id="jd-1",
        company="Acme",
        role="Engineer",
        location="Remote",
        jd_text="Role: Engineer",
        created_at=now(),
    )

    row = mappers.job_description_to_row(entity)
    assert row.id == entity.id
    assert row.jd_text == entity.jd_text

    assert mappers.job_description_from_row(row) == entity


def test_job_analysis_mapper_roundtrip():
    requirement = JobRequirement(
        requirement="Experience with Python",
        category=RequirementCategory.REQUIRED,
        importance=Importance.HIGH,
        context="Experience with Python",
    )
    entity = JobAnalysis(
        id="jd-1",
        job_description_id="jd-1",
        role="Backend Engineer",
        seniority="Senior",
        requirements=[requirement],
        created_at=now(),
    )

    row = mappers.job_analysis_to_row(entity)
    assert row.requirements[0]["requirement"] == "Experience with Python"

    assert mappers.job_analysis_from_row(row) == entity


def test_job_mapper_roundtrip():
    entity = Job(
        id="job-1",
        type="ANALYZE",
        status="SUCCEEDED",
        payload={"job_description_id": "jd-1"},
        result={"role": "Engineer"},
        error_code=None,
        error_message=None,
        created_at=now(),
        updated_at=now(),
    )

    row = mappers.job_to_row(entity)
    assert row.payload == {"job_description_id": "jd-1"}
    assert row.result == {"role": "Engineer"}

    assert mappers.job_from_row(row) == entity


def test_match_result_mapper_roundtrip():
    evidence_match = EvidenceMatch(
        requirement="Experience with FastAPI",
        category=RequirementCategory.REQUIRED,
        importance=Importance.HIGH,
        status=MatchStatus.STRONG_MATCH,
        matched_skill="fastapi",
        ambiguous=False,
        rationale="Skill 'fastapi' is listed and substantiated.",
        evidence_ids=["experience:0:bullet:0"],
        evidence=["Built the ordering API with FastAPI"],
    )
    entity = MatchResult(
        job_description_id="jd-1",
        resume_id="resume-1",
        matches=[evidence_match],
        created_at=now(),
    )

    row = mappers.match_result_to_row(entity)
    assert row.id == "jd-1"
    assert row.job_description_id == "jd-1"
    assert row.matches[0]["status"] == "STRONG_MATCH"

    assert mappers.match_result_from_row(row) == entity