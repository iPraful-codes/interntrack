import pytest

from app import create_app


@pytest.fixture()
def client(tmp_path):
    app = create_app({"DATABASE": str(tmp_path / "test.db"), "TESTING": True})
    return app.test_client()


def make(client, **overrides):
    payload = {"company": "Acme", "role": "Junior Developer", **overrides}
    return client.post("/api/applications", json=payload)


def test_create_and_list(client):
    res = make(client, location="Remote")
    assert res.status_code == 201
    assert res.get_json()["status"] == "Applied"
    assert len(client.get("/api/applications").get_json()) == 1


@pytest.mark.parametrize(
    "overrides",
    [{"company": ""}, {"status": "Ghosted"}, {"applied_on": "13/01/2026"}, {"link": "javascript:alert(1)"}],
)
def test_invalid_input_is_rejected(client, overrides):
    res = make(client, **overrides)
    assert res.status_code == 400
    assert res.get_json()["errors"]


def test_filter_and_search(client):
    make(client, company="Acme", status="Applied")
    make(client, company="Globex", role="Data Intern", status="Interview")
    assert len(client.get("/api/applications?status=Interview").get_json()) == 1
    assert len(client.get("/api/applications?q=data").get_json()) == 1


def test_update_and_delete(client):
    app_id = make(client).get_json()["id"]
    res = client.put(f"/api/applications/{app_id}", json={"status": "Offer"})
    assert res.get_json()["status"] == "Offer"
    assert client.delete(f"/api/applications/{app_id}").status_code == 204
    assert client.delete(f"/api/applications/{app_id}").status_code == 404
    assert client.put("/api/applications/999", json={"status": "Offer"}).status_code == 404


def test_stats(client):
    for status in ("Applied", "Applied", "Interview", "Wishlist"):
        make(client, status=status)
    stats = client.get("/api/stats").get_json()
    assert stats["total"] == 4
    assert stats["by_status"]["Applied"] == 2
    assert stats["interview_rate"] == 33.3
    assert sum(w["n"] for w in stats["weekly"]) == 3
