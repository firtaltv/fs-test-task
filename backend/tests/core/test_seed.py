import pytest
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.core.db import seed_local_users
from app.core.permissions import Role
from app.models import UserCreate
from tests.utils.utils import random_email, random_lower_string


@pytest.fixture
def seed_settings(monkeypatch: pytest.MonkeyPatch) -> dict[Role, str]:
    emails = {Role.MANAGER: random_email(), Role.MEMBER: random_email()}
    monkeypatch.setattr(settings, "SEED_MANAGER_EMAIL", emails[Role.MANAGER])
    monkeypatch.setattr(settings, "SEED_MANAGER_PASSWORD", random_lower_string())
    monkeypatch.setattr(settings, "SEED_MEMBER_EMAIL", emails[Role.MEMBER])
    monkeypatch.setattr(settings, "SEED_MEMBER_PASSWORD", random_lower_string())
    return emails


def test_seeds_manager_and_member_in_development(
    db: Session, monkeypatch: pytest.MonkeyPatch, seed_settings: dict[Role, str]
) -> None:
    monkeypatch.setattr(settings, "FASTAPI_ENV", "development")

    seed_local_users(db)
    seed_local_users(db)  # idempotent: a second run is a no-op

    for role, email in seed_settings.items():
        user = crud.get_user_by_email(session=db, email=email)
        assert user is not None
        assert user.role == role


def test_never_seeds_outside_development(
    db: Session, monkeypatch: pytest.MonkeyPatch, seed_settings: dict[Role, str]
) -> None:
    # Staging and production run without FASTAPI_ENV; the SEED_* variables
    # being set (e.g. a copied .env) must not create demo users there
    monkeypatch.setattr(settings, "FASTAPI_ENV", None)

    seed_local_users(db)

    for email in seed_settings.values():
        assert crud.get_user_by_email(session=db, email=email) is None


def test_existing_user_with_seed_email_is_left_untouched(
    db: Session, monkeypatch: pytest.MonkeyPatch, seed_settings: dict[Role, str]
) -> None:
    monkeypatch.setattr(settings, "FASTAPI_ENV", "development")
    email = seed_settings[Role.MANAGER]
    crud.create_user(
        session=db,
        user_create=UserCreate(email=email, password=random_lower_string()),
    )

    seed_local_users(db)

    user = crud.get_user_by_email(session=db, email=email)
    assert user is not None
    assert user.role == Role.MEMBER
