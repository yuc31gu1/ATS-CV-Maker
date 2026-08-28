# 0003 Background jobs run in-process against a Postgres job table, no Redis

We decided that heavy LLM stages (ANALYZE, TAILOR) run as background jobs in the FastAPI process, tracked by a generic typed `Job` table in Postgres, with the frontend polling `GET /jobs/{id}`. Fast deterministic stages (MATCH, GENERATE) stay synchronous. Redis was rejected for the MVP.

We rejected a separate worker process/container for the single-user, no-auth MVP, and a full Redis/Celery stack as unnecessary infrastructure. The in-process worker with a Postgres-backed job table satisfies MVP latency needs and leaves a clean seam to split the worker out later if load demands it.
