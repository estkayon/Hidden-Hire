def test_mark_and_undo_applied(client):
    marked = client.post("/api/applied/new").json()
    assert marked["applied_at"] is not None

    job = client.get("/api/jobs/new").json()
    assert job["applied_at"] is not None
    assert job["saved"] is False
    assert [
        j["id"]
        for j in client.get("/api/jobs", params={"applied": "true"}).json()["jobs"]
    ] == ["new"]
    assert client.delete("/api/saved/new").status_code == 409

    client.delete("/api/applied/new")
    job = client.get("/api/jobs/new").json()
    assert job["applied_at"] is None
    assert job["saved"] is True
    assert client.get("/api/jobs", params={"applied": "true"}).json()["jobs"] == []


def test_applied_on_missing_job_is_404(client):
    assert client.post("/api/applied/nope").status_code == 404
