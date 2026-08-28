from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from app.errors import NotFoundError, ResourceValidationError, register_exception_handlers


def test_app_error_returns_structured_error():
    router = APIRouter()

    @router.get("/boom")
    def boom() -> None:
        raise NotFoundError("resume not found", details={"id": "abc"})

    app = FastAPI()
    app.include_router(router)
    register_exception_handlers(app)

    resp = TestClient(app).get("/boom")
    assert resp.status_code == 404
    assert resp.json() == {
        "error": {"code": "NOT_FOUND", "message": "resume not found", "details": {"id": "abc"}}
    }


def test_validation_error_uses_dedicated_code():
    router = APIRouter()

    @router.get("/bad")
    def bad() -> None:
        raise ResourceValidationError("invalid job description")

    app = FastAPI()
    app.include_router(router)
    register_exception_handlers(app)

    resp = TestClient(app).get("/bad")
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_unhandled_exception_masks_internals():
    router = APIRouter()

    @router.get("/crash")
    def crash() -> None:
        raise RuntimeError("secret internal detail")

    app = FastAPI()
    app.include_router(router)
    register_exception_handlers(app)

    resp = TestClient(app, raise_server_exceptions=False).get("/crash")
    assert resp.status_code == 500
    body = resp.json()
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert "secret internal detail" not in body["error"]["message"]