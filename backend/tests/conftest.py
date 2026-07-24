import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings


def _test_database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        return url
    root, _, dbname = settings.database_url.rpartition("/")
    return f"{root}/{dbname}_test"


engine = create_engine(_test_database_url())
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def _setup_database():
    from app.constants import PLAN_LIMITS, PLAN_PRICES, SEED_MODULES
    from app.models import Base, Module, PlanConfig

    Base.metadata.create_all(bind=engine)

    # Popula o catálogo de módulos e planos no banco de teste — normalmente isso
    # acontece via seed_modules()/seed_plan_configs() ao importar app.main, mas
    # essas funções sempre usam o banco de DEV (SessionLocal fixo), não o de
    # teste. Sem isso, rotas que consultam Module (ex: module-config, checkout)
    # dão 404, e a tabela PlanConfig fica vazia (get_plan_limits cai no fallback
    # PLAN_LIMITS fixo, mas os testes de admin/planos precisam das linhas de verdade).
    session = TestingSessionLocal()
    try:
        for data in SEED_MODULES:
            session.add(Module(**data))
        for plan_name, limits in PLAN_LIMITS.items():
            session.add(PlanConfig(
                plan_name=plan_name,
                price=PLAN_PRICES.get(plan_name, 0),
                max_apps=limits["apps"],
                max_modules=limits["modules"],
                max_items=limits["items"],
                max_categories=limits["categories"],
                max_push_sends_per_month=limits["push_sends_per_month"],
            ))
        session.commit()
    finally:
        session.close()

    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session):
    # Importar app.main dispara create_all/seed_modules contra o banco de DEV
    # (app/database.py usa settings.database_url, não o banco de teste) — inofensivo
    # e idempotente, mas exige que o Postgres de dev esteja no ar ao rodar os testes.
    from app.database import get_db
    from app.main import app

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    # Rate limiting é por IP e o TestClient usa sempre o mesmo IP fake — sem
    # desligar aqui, os vários register_user/login de testes diferentes
    # estourariam o limite entre si.
    app.state.limiter.enabled = False
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def register_user(client):
    def _register(email="user@example.com", password="senha12345", full_name="Test User"):
        response = client.post(
            "/api/auth/register",
            json={"email": email, "password": password, "full_name": full_name},
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _register
