import logging
from collections.abc import Callable, Generator
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlmodel import Session

from app.core import security
from app.core.config import settings
from app.core.db import engine
from app.core.permissions import Permission, has_permission
from app.models import TokenPayload, User

logger = logging.getLogger(__name__)

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)


def get_db() -> Generator[Session]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db)]
TokenDep = Annotated[str, Depends(reusable_oauth2)]


def get_current_user(session: SessionDep, token: TokenDep) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except InvalidTokenError, ValidationError:
        raise credentials_exception
    user = session.get(User, token_data.sub)
    if not user:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user"
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def check_permission(
    request: Request,
    user: User,
    permission: Permission,
    detail: str = "The user doesn't have enough privileges",
) -> None:
    """Raise 403 unless the user's role grants the permission.

    Use directly for object-level checks inside a route; use
    require_permission for route-level checks.
    """
    if has_permission(user.role, permission):
        return
    # The route template, not the concrete URL, so path params (e.g. an
    # email) never reach the logs
    route = request.scope.get("route")
    logger.warning(
        "Authorization denied: user_id=%s permission=%s method=%s path=%s",
        user.id,
        permission,
        request.method,
        getattr(route, "path", "<unknown>"),
    )
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def require_permission(permission: Permission) -> Callable[..., User]:
    """Route-level guard: dependencies=[Depends(require_permission(...))]."""

    def dependency(request: Request, current_user: CurrentUser) -> User:
        check_permission(request, current_user, permission)
        return current_user

    return dependency
