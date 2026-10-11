import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def _a_moment(link=3):
    r = client.get("/scenarios", params={"link_id": link}).json()
    return r["featured"][0]["timestamp"]


def test_health_and_links():
    with TestClient(app) as c:
        assert c.get("/health").json()["status"] == "ok"
        assert len(c.get("/links").json()["links"]) >= 5


def test_predict_queue_shape():
    ts = _a_moment()
    r = client.post("/predict/queue", json={"link_id": 3, "timestamp": ts})
    assert r.status_code == 200, r.text
    b = r.json()
    assert 0 <= b["risk"] <= 1 and b["label"] in {"low", "moderate", "high"}
    assert set(b["horizon_risk"]) == {"5", "10", "15", "20", "25", "30"}
    assert 1 <= len(b["reasons"]) <= 3 and len(b["history"]) == 12


def test_errors():
    assert client.post("/predict/queue", json={"link_id": 999, "timestamp": "2025-02-12T17:05:00"}).status_code == 404
    assert client.post("/predict/queue", json={"link_id": 3, "timestamp": "2025-02-12T17:03:00"}).status_code == 422
    assert client.post("/predict/queue", json={"link_id": 3, "timestamp": "2020-01-01T10:00:00"}).status_code == 422
    assert client.post("/predict/queue", json={"link_id": -1, "timestamp": "2025-02-12T17:05:00"}).status_code == 422


def test_reconstruct():
    r = client.post("/reconstruct", json={"link_id": 3, "start": "2025-02-12T16:00:00", "end": "2025-02-12T18:00:00", "mask_rate": 0.25})
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["n_masked_speed"] > 0 and b["rmse"]["speed"] is not None
    too_long = client.post("/reconstruct", json={"link_id": 3, "start": "2025-02-12T01:00:00", "end": "2025-02-12T20:00:00"})
    assert too_long.status_code == 422
