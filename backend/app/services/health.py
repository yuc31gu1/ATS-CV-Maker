from sqlalchemy import Engine, text

from app.db import engine


class HealthService:
    def __init__(self, db_engine: Engine) -> None:
        self._engine = db_engine

    def database_ok(self) -> bool:
        try:
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False


def get_health_service() -> HealthService:
    return HealthService(engine)