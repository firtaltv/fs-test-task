import logging

from sqlmodel import Session, create_engine, select

from app import crud
from app.core.config import settings
from app.core.permissions import Role
from app.models import User, UserCreate

logger = logging.getLogger(__name__)

engine = create_engine(str(settings.DATABASE_URL), pool_pre_ping=True)


# make sure all SQLModel models are imported (app.models) before initializing DB
# otherwise, SQLModel might fail to initialize relationships properly
# for more details: https://github.com/fastapi/full-stack-fastapi-template/issues/28


def init_db(session: Session) -> None:
    # Tables should be created with Alembic migrations
    # But if you don't want to use migrations, create
    # the tables un-commenting the next lines
    # from sqlmodel import SQLModel

    # This works because the models are already imported and registered from app.models
    # SQLModel.metadata.create_all(engine)

    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            role=Role.ADMIN,
        )
        user = crud.create_user(session=session, user_create=user_in)
    seed_local_users(session)


def seed_local_users(session: Session) -> None:
    """Seed one manager and one member for local development.

    Idempotent: an existing user with a seed email is left untouched. Never
    runs outside FASTAPI_ENV=development, even if the SEED_* variables are
    set, so staging and production only ever get the first superuser.
    """
    if settings.FASTAPI_ENV != "development":
        return
    seeds = [
        (settings.SEED_MANAGER_EMAIL, settings.SEED_MANAGER_PASSWORD, Role.MANAGER),
        (settings.SEED_MEMBER_EMAIL, settings.SEED_MEMBER_PASSWORD, Role.MEMBER),
    ]
    for email, password, role in seeds:
        if not email or not password:
            continue
        if crud.get_user_by_email(session=session, email=email):
            continue
        crud.create_user(
            session=session,
            user_create=UserCreate(email=email, password=password, role=role),
        )
        logger.info("Seeded local %s user", role)
