from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from .main import app, Base, get_db

SQLALCHEMY_DATABASE_URL = "sqlite:///"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200


def test_get_image():
    response = client.get(
        "/image/5446e98c-6efa-4295-b92f-cd62867f7f26", headers={"x-forwarded-for": "127.0.0.1"}
    )
    assert response.status_code == 200


def test_get_image_bad_uuid():
    response = client.get("/image/test", headers={"x-forwarded-for": "127.0.0.1"})
    assert response.status_code == 422


def test_get_new_image():
    response = client.get("/new_image")
    assert response.status_code == 200


def test_track_some():
    # 5446e98c-6efa-4295-b92f-cd62867f7f26 created in test_get_image
    response = client.get("/track/5446e98c-6efa-4295-b92f-cd62867f7f26")
    assert response.status_code == 200
    assert response.text != '<div id="events"></div>'


def test_track_none():
    response = client.get("/track/5446e98c-6efa-4595-b92f-cd62867f7f26")
    assert response.status_code == 200
    assert response.text == '<div id="events"></div>'


def test_show_tracking():
    response = client.get("/track/5446e98c-6efa-4595-b92f-cd62867f7f26")
    assert response.status_code == 200

    # 5446e98c-6efa-4295-b92f-cd62867f7f26 created in test_get_image
    response = client.get("/track/5446e98c-6efa-4295-b92f-cd62867f7f26")
    assert response.status_code == 200
