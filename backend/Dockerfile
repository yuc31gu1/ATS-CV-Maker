FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# LaTeX tooling for deterministic document generation (spec PRD, T6):
# pdflatex plus the template packages (geometry, lmodern, enumitem,
# titlesec, hyperref, glyphtounicode) and poppler-utils for PDF validation.
RUN apt-get update && apt-get install -y --no-install-recommends \
    texlive-latex-base \
    texlive-latex-recommended \
    texlive-latex-extra \
    texlive-fonts-recommended \
    texlive-plain-generic \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml alembic.ini ./
COPY alembic ./alembic
COPY app ./app

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]