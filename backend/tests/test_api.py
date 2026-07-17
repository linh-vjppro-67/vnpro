import os
os.environ["DATABASE_URL"] = "sqlite:///./test_pro_erp.db"
os.environ["SECRET_KEY"] = "test-secret-key"

from fastapi.testclient import TestClient
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.main import app
from app.models import User
from app.core.security import get_password_hash

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
with SessionLocal() as db:
    db.add(User(email="admin@test.vn", full_name="Admin", role="SYSTEM_ADMIN", department="IT", hashed_password=get_password_hash("Demo@123")))
    db.commit()

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_login_and_me():
    login = client.post("/auth/login", json={"email": "admin@test.vn", "password": "Demo@123"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["role"] == "SYSTEM_ADMIN"


def test_login_preflight_allows_local_dev_origin():
    response = client.options(
        "/auth/login",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
