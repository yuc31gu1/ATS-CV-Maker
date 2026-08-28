def _payload() -> dict:
    return {
        "schema_version": 1,
        "personal_information": {
            "full_name": "Ada Lovelace",
            "email": "ada@example.com",
        },
        "summary": "Deterministic document pipelines.",
        "skills": {"languages": ["Python"], "frameworks": ["FastAPI"]},
        "experience": [
            {
                "company": "Analytical Engines Ltd",
                "title": "Engineer",
                "start_date": "2021-03",
                "end_date": "2024-05",
                "bullets": ["Shipped the PDF pipeline"],
            }
        ],
        "education": [
            {
                "school": "University of London",
                "degree": "BSc",
                "start_date": "2016-09",
                "end_date": "2020-06",
            }
        ],
        "projects": [
            {"name": "ATS CV Maker", "description": "Resume pipeline", "technologies": ["Python"]}
        ],
        "certifications": [{"name": "AWS Solutions Architect", "issuer": "AWS", "date": "2023-01"}],
    }


def test_create_resume_returns_201_with_id(resume_client) -> None:
    resp = resume_client.post("/api/resumes", json=_payload())
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"]
    assert body["personal_information"]["full_name"] == "Ada Lovelace"
    assert body["experience"][0]["start_date"] == "2021-03"


def test_get_resume_roundtrips_created(resume_client) -> None:
    created = resume_client.post("/api/resumes", json=_payload()).json()
    resp = resume_client.get(f"/api/resumes/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["summary"] == "Deterministic document pipelines."


def test_list_resumes(resume_client) -> None:
    first = resume_client.post("/api/resumes", json=_payload()).json()
    second = resume_client.post(
        "/api/resumes", json={**_payload(), "summary": "Second"}
    ).json()
    body = resume_client.get("/api/resumes").json()
    assert {r["id"] for r in body} == {first["id"], second["id"]}


def test_update_resume(resume_client) -> None:
    created = resume_client.post("/api/resumes", json=_payload()).json()
    resp = resume_client.put(
        f"/api/resumes/{created['id']}", json={**_payload(), "summary": "Updated"}
    )
    assert resp.status_code == 200
    assert resp.json()["summary"] == "Updated"
    fetched = resume_client.get(f"/api/resumes/{created['id']}").json()
    assert fetched["summary"] == "Updated"


def test_rejects_malformed_resume_with_invalid_resume_code(resume_client) -> None:
    resp = resume_client.post(
        "/api/resumes", json={**_payload(), "experience": [{"company": "No title"}]}
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["code"] == "INVALID_RESUME"
    assert body["error"]["message"] == "invalid resume"


def test_rejects_bad_date_with_invalid_resume_code(resume_client) -> None:
    resp = resume_client.post(
        "/api/resumes", json={**_payload(), "experience": [{"start_date": "March 2021"}]}
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "INVALID_RESUME"


def test_get_missing_resume_returns_not_found(resume_client) -> None:
    resp = resume_client.get("/api/resumes/nope")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_update_missing_resume_returns_not_found(resume_client) -> None:
    resp = resume_client.put("/api/resumes/nope", json=_payload())
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_schema_version_roundtrips(resume_client) -> None:
    created = resume_client.post(
        "/api/resumes", json={**_payload(), "schema_version": 2}
    ).json()
    fetched = resume_client.get(f"/api/resumes/{created['id']}").json()
    assert fetched["schema_version"] == 2