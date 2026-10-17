"""Role-based access control: the permission matrix and its escalation paths.

Every denial asserts the authz-specific detail *and* the WARNING log line for
the expected permission, so a request rejected for another reason (a 422 from
an invalid body, a 404, a different check) can never pass as a denial.
"""

import logging
import uuid
from collections.abc import Callable, Generator
from datetime import timedelta
from typing import Any, NamedTuple

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.core.permissions import ROLE_PERMISSIONS, Permission, Role
from app.core.security import create_access_token
from app.models import User
from tests.utils.item import create_random_item
from tests.utils.user import create_random_user, create_user_with_role
from tests.utils.utils import random_email, random_lower_string

API = settings.API_V1_STR
DENIED = "The user doesn't have enough privileges"


class RoleUser(NamedTuple):
    user: User
    headers: dict[str, str]


@pytest.fixture(scope="module")
def users_by_role(client: TestClient, db: Session) -> dict[Role, RoleUser]:
    return {
        role: RoleUser(*create_user_with_role(client=client, db=db, role=role))
        for role in Role
    }


@pytest.fixture
def sole_admin(client: TestClient, db: Session) -> Generator[RoleUser]:
    """A fresh admin who is the only *active* admin for the duration of the test.

    Other admins are deactivated rather than deleted, which also proves that
    inactive admins don't count towards the last-admin rule.
    """
    others = db.exec(select(User).where(User.role == Role.ADMIN, User.is_active)).all()
    for other in others:
        other.is_active = False
        db.add(other)
    db.commit()
    yield RoleUser(*create_user_with_role(client=client, db=db, role=Role.ADMIN))
    for other in others:
        other.is_active = True
        db.add(other)
    db.commit()


def denial_logs(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [
        r
        for r in caplog.records
        if r.name == "app.api.deps" and r.levelno == logging.WARNING
    ]


# --- Permission matrix -------------------------------------------------------

# (method, path, body) for each protected action. "{target}" is replaced by the
# id of a fresh member created for each case; bodies are always valid, so a
# denial can only come from the authz check.
Action = tuple[str, str, Callable[[], dict[str, Any] | None]]

LIST_USERS: Action = ("GET", "/users/", lambda: None)
READ_OTHER_USER: Action = ("GET", "/users/{target}", lambda: None)
CREATE_USER: Action = (
    "POST",
    "/users/",
    lambda: {"email": random_email(), "password": random_lower_string()},
)
UPDATE_OTHER_USER: Action = (
    "PATCH",
    "/users/{target}",
    lambda: {"full_name": "Renamed"},
)
DELETE_OTHER_USER: Action = ("DELETE", "/users/{target}", lambda: None)
READ_METRICS: Action = ("GET", "/metrics/", lambda: None)


def allowed(role: Role, action: Action, name: str) -> Any:
    return pytest.param(role, action, None, id=f"{role} can {name}")


def denied(role: Role, action: Action, permission: Permission, name: str) -> Any:
    return pytest.param(role, action, permission, id=f"{role} cannot {name}")


@pytest.mark.parametrize(
    ("role", "action", "denied_permission"),
    [
        allowed(Role.ADMIN, LIST_USERS, "list users"),
        allowed(Role.MANAGER, LIST_USERS, "list users"),
        denied(Role.MEMBER, LIST_USERS, Permission.USERS_READ, "list users"),
        allowed(Role.ADMIN, READ_OTHER_USER, "read another user"),
        allowed(Role.MANAGER, READ_OTHER_USER, "read another user"),
        denied(
            Role.MEMBER, READ_OTHER_USER, Permission.USERS_READ, "read another user"
        ),
        allowed(Role.ADMIN, CREATE_USER, "create users"),
        denied(Role.MANAGER, CREATE_USER, Permission.USERS_CREATE, "create users"),
        denied(Role.MEMBER, CREATE_USER, Permission.USERS_CREATE, "create users"),
        allowed(Role.ADMIN, UPDATE_OTHER_USER, "update another user"),
        denied(
            Role.MANAGER,
            UPDATE_OTHER_USER,
            Permission.USERS_UPDATE,
            "update another user",
        ),
        denied(
            Role.MEMBER,
            UPDATE_OTHER_USER,
            Permission.USERS_UPDATE,
            "update another user",
        ),
        allowed(Role.ADMIN, DELETE_OTHER_USER, "delete another user"),
        denied(
            Role.MANAGER,
            DELETE_OTHER_USER,
            Permission.USERS_DELETE,
            "delete another user",
        ),
        denied(
            Role.MEMBER,
            DELETE_OTHER_USER,
            Permission.USERS_DELETE,
            "delete another user",
        ),
        allowed(Role.ADMIN, READ_METRICS, "read metrics"),
        allowed(Role.MANAGER, READ_METRICS, "read metrics"),
        denied(Role.MEMBER, READ_METRICS, Permission.METRICS_READ, "read metrics"),
    ],
)
def test_permission_matrix(
    client: TestClient,
    db: Session,
    caplog: pytest.LogCaptureFixture,
    users_by_role: dict[Role, RoleUser],
    role: Role,
    action: Action,
    denied_permission: Permission | None,
) -> None:
    method, path, body = action
    target = create_random_user(db)
    caplog.set_level(logging.WARNING, logger="app.api.deps")

    r = client.request(
        method,
        f"{API}{path.format(target=target.id)}",
        headers=users_by_role[role].headers,
        json=body(),
    )

    if denied_permission is None:
        assert r.status_code == 200, r.json()
        assert denial_logs(caplog) == []
    else:
        assert r.status_code == 403
        assert r.json() == {"detail": DENIED}
        [log] = denial_logs(caplog)
        assert f"permission={denied_permission}" in log.getMessage()


# --- Escalation paths --------------------------------------------------------


def test_member_cannot_set_own_role_via_update_me(
    client: TestClient, db: Session, users_by_role: dict[Role, RoleUser]
) -> None:
    member = users_by_role[Role.MEMBER]
    r = client.patch(
        f"{API}/users/me",
        headers=member.headers,
        json={"full_name": "Still a member", "role": Role.ADMIN},
    )
    # The request itself succeeds (the legitimate field is applied), so this
    # can't pass because of a 422; only the role is ignored
    assert r.status_code == 200
    assert r.json()["full_name"] == "Still a member"
    assert r.json()["role"] == Role.MEMBER
    db.refresh(member.user)
    assert member.user.role == Role.MEMBER


def test_signup_with_role_creates_member(client: TestClient, db: Session) -> None:
    email = random_email()
    r = client.post(
        f"{API}/users/signup",
        json={"email": email, "password": random_lower_string(), "role": Role.ADMIN},
    )
    assert r.status_code == 200
    assert r.json()["role"] == Role.MEMBER
    user = db.exec(select(User).where(User.email == email)).one()
    assert user.role == Role.MEMBER


def test_manager_cannot_promote_self(
    client: TestClient,
    db: Session,
    caplog: pytest.LogCaptureFixture,
    users_by_role: dict[Role, RoleUser],
) -> None:
    manager = users_by_role[Role.MANAGER]
    caplog.set_level(logging.WARNING, logger="app.api.deps")
    r = client.patch(
        f"{API}/users/{manager.user.id}",
        headers=manager.headers,
        json={"role": Role.ADMIN},
    )
    assert r.status_code == 403
    assert r.json() == {"detail": DENIED}
    [log] = denial_logs(caplog)
    assert f"permission={Permission.USERS_UPDATE}" in log.getMessage()
    db.refresh(manager.user)
    assert manager.user.role == Role.MANAGER


# --- Last admin --------------------------------------------------------------


@pytest.mark.parametrize(
    "change",
    [
        pytest.param({"role": Role.MEMBER}, id="demote"),
        pytest.param({"role": Role.MANAGER}, id="demote to manager"),
        pytest.param({"is_active": False}, id="deactivate"),
    ],
)
def test_sole_admin_cannot_remove_own_admin_access(
    client: TestClient, db: Session, sole_admin: RoleUser, change: dict[str, Any]
) -> None:
    r = client.patch(
        f"{API}/users/{sole_admin.user.id}", headers=sole_admin.headers, json=change
    )
    assert r.status_code == 409
    assert r.json() == {"detail": "Cannot demote or deactivate the last active admin"}
    db.refresh(sole_admin.user)
    assert sole_admin.user.role == Role.ADMIN
    assert sole_admin.user.is_active is True


def test_admin_can_step_down_when_another_admin_exists(
    client: TestClient, db: Session, sole_admin: RoleUser
) -> None:
    other, _ = create_user_with_role(client=client, db=db, role=Role.ADMIN)
    r = client.patch(
        f"{API}/users/{sole_admin.user.id}",
        headers=sole_admin.headers,
        json={"role": Role.MEMBER},
    )
    assert r.status_code == 200
    assert r.json()["role"] == Role.MEMBER
    db.refresh(other)
    assert other.role == Role.ADMIN


def test_admin_can_demote_another_admin(
    client: TestClient, db: Session, sole_admin: RoleUser
) -> None:
    other, _ = create_user_with_role(client=client, db=db, role=Role.ADMIN)
    r = client.patch(
        f"{API}/users/{other.id}",
        headers=sole_admin.headers,
        json={"role": Role.MEMBER},
    )
    assert r.status_code == 200
    assert r.json()["role"] == Role.MEMBER


# --- Stale privileges --------------------------------------------------------


def test_demoted_manager_loses_access_on_next_request(
    client: TestClient, db: Session, superuser_token_headers: dict[str, str]
) -> None:
    manager, headers = create_user_with_role(client=client, db=db, role=Role.MANAGER)
    assert client.get(f"{API}/users/", headers=headers).status_code == 200

    r = client.patch(
        f"{API}/users/{manager.id}",
        headers=superuser_token_headers,
        json={"role": Role.MEMBER},
    )
    assert r.status_code == 200

    # Same token: the role is read from the DB on every request, not the JWT
    r = client.get(f"{API}/users/", headers=headers)
    assert r.status_code == 403
    assert r.json() == {"detail": DENIED}


# --- Authentication ----------------------------------------------------------


@pytest.mark.parametrize(
    "headers",
    [
        pytest.param({}, id="no token"),
        pytest.param({"Authorization": "Bearer not-a-jwt"}, id="malformed token"),
        pytest.param(
            {
                "Authorization": "Bearer "
                + create_access_token(uuid.uuid4(), timedelta(minutes=5))
            },
            id="token for unknown user",
        ),
        pytest.param(
            {
                "Authorization": "Bearer "
                + create_access_token(uuid.uuid4(), timedelta(minutes=-5))
            },
            id="expired token",
        ),
    ],
)
def test_unauthenticated_request_returns_401(
    client: TestClient, headers: dict[str, str]
) -> None:
    r = client.get(f"{API}/users/me", headers=headers)
    assert r.status_code == 401
    assert r.headers["WWW-Authenticate"] == "Bearer"


def test_inactive_user_returns_403(client: TestClient, db: Session) -> None:
    user, headers = create_user_with_role(client=client, db=db, role=Role.MEMBER)
    user.is_active = False
    db.add(user)
    db.commit()

    r = client.get(f"{API}/users/me", headers=headers)
    assert r.status_code == 403
    assert r.json() == {"detail": "Inactive user"}


# --- /users/me -------------------------------------------------------------


@pytest.mark.parametrize("role", list(Role))
def test_me_returns_exactly_the_role_permissions(
    client: TestClient, users_by_role: dict[Role, RoleUser], role: Role
) -> None:
    r = client.get(f"{API}/users/me", headers=users_by_role[role].headers)
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == role
    assert len(body["permissions"]) == len(set(body["permissions"]))
    assert set(body["permissions"]) == ROLE_PERMISSIONS[role]


# --- Observability -----------------------------------------------------------


def test_route_level_denial_is_logged_without_pii(
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
    users_by_role: dict[Role, RoleUser],
) -> None:
    member = users_by_role[Role.MEMBER]
    caplog.set_level(logging.WARNING, logger="app.api.deps")
    victim = random_email()

    r = client.post(
        f"{API}/password-recovery-html-content/{victim}", headers=member.headers
    )

    assert r.status_code == 403
    [log] = denial_logs(caplog)
    message = log.getMessage()
    assert f"user_id={member.user.id}" in message
    assert f"permission={Permission.SYSTEM_MANAGE}" in message
    assert "method=POST" in message
    # The route template is logged, never the concrete path or any email
    assert "path=/password-recovery-html-content/{email}" in message
    assert victim not in message
    assert member.user.email not in message


def test_object_level_denial_is_logged(
    client: TestClient,
    db: Session,
    caplog: pytest.LogCaptureFixture,
    users_by_role: dict[Role, RoleUser],
) -> None:
    member = users_by_role[Role.MEMBER]
    item = create_random_item(db)
    caplog.set_level(logging.WARNING, logger="app.api.deps")

    r = client.get(f"{API}/items/{item.id}", headers=member.headers)

    assert r.status_code == 403
    [log] = denial_logs(caplog)
    message = log.getMessage()
    assert f"user_id={member.user.id}" in message
    assert f"permission={Permission.ITEMS_MANAGE_ALL}" in message
    assert "method=GET path=/items/{id}" in message
