from fastapi import APIRouter, Depends
from sqlmodel import func, select

from app.api.deps import SessionDep, require_permission
from app.core.permissions import Permission, Role
from app.models import Item, MetricsPublic, User

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get(
    "/",
    dependencies=[Depends(require_permission(Permission.METRICS_READ))],
    response_model=MetricsPublic,
)
def read_metrics(session: SessionDep) -> MetricsPublic:
    """
    Basic usage metrics (stub for a future insights dashboard).
    """
    users_by_role = dict.fromkeys(Role, 0)
    for role, count in session.exec(
        select(User.role, func.count()).group_by(User.role)
    ):
        users_by_role[Role(role)] = count
    items_total = session.exec(select(func.count()).select_from(Item)).one()
    return MetricsPublic(
        users_total=sum(users_by_role.values()),
        users_by_role=users_by_role,
        items_total=items_total,
    )
