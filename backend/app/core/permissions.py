"""Role-based access control.

This module is the single source of truth for what each role may do. Routes
depend on permissions, never on roles, so adding a role means adding an enum
member and a row in ROLE_PERMISSIONS - nothing else.
"""

from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"
    MANAGER = "manager"
    MEMBER = "member"


class Permission(StrEnum):
    USERS_READ = "users:read"
    USERS_CREATE = "users:create"
    USERS_UPDATE = "users:update"
    USERS_DELETE = "users:delete"
    ITEMS_MANAGE_ALL = "items:manage_all"
    METRICS_READ = "metrics:read"
    SYSTEM_MANAGE = "system:manage"


# Actions every authenticated user may perform on their own resources (own
# profile, own items) are not permissions; they only require CurrentUser.
ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.ADMIN: frozenset(Permission),
    Role.MANAGER: frozenset({Permission.USERS_READ, Permission.METRICS_READ}),
    Role.MEMBER: frozenset(),
}


def permissions_for(role: Role) -> frozenset[Permission]:
    return ROLE_PERMISSIONS[role]


def has_permission(role: Role, permission: Permission) -> bool:
    return permission in permissions_for(role)
