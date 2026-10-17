# ADR 0001: Permission-based RBAC with a static role → permission map

- **Status:** Accepted
- **Date:** 2026-10-17

## Context

The template had one privilege flag, `user.is_superuser`. It was checked in two
different ways: a `get_current_active_superuser` dependency on some routes, and
inline `if current_user.is_superuser` checks in about six places. We need three
roles (admin, manager, member) with different access to user management,
metrics and items. The authorization code must follow one readable pattern, and
adding a role later must not mean editing ten or more files.

## Options

1. **Role column + role checks in routes.** Routes compare roles directly
   (`if user.role in (ADMIN, MANAGER)`). This is the fastest to write, but it
   repeats the `is_superuser` sprawl: every new role means editing every
   comparison, and a missed one is an escalation hole or a false denial.
2. **Role column + static role → permission map; routes depend on
   permissions.** One module defines `Role`, `Permission` and
   `ROLE_PERMISSIONS`. Routes declare `require_permission(Permission.X)` and
   never mention roles. Changing who may do what is a one-line, reviewable diff
   in a single file.
3. **Roles and permissions tables in the database.** This is the most
   flexible: grants change at runtime without a deploy. It needs tables,
   seeding, an admin API or UI to manage grants, caching, and more tests.
   Permissions also stop being visible in code review.

## Decision

Option 2. `backend/app/core/permissions.py` is the only place that maps roles to
permissions. Route-level checks use the `require_permission` dependency.
Decisions that depend on the loaded record (item ownership, reading another
user) call the same check through `check_permission`, so every denial shares one
code path, one status code and one log line.

The role is stored as `VARCHAR(32)` and validated against the `Role` enum, not
as a native Postgres ENUM, so adding a role needs no migration.

Two rules refer to `Role.ADMIN` on purpose: admins can't delete themselves, and
the last active admin can't be demoted. They protect the existence of an admin
rather than describing a capability, so they aren't permissions.

## Consequences

- Adding a role means one enum member and one map row on the backend, plus a
  label on the frontend that the compiler enforces.
- Changing grants needs a deploy, which is acceptable at this scale.
- Routes depend on permissions rather than roles, so moving to option 3 later
  wouldn't touch any route. Only the source of `ROLE_PERMISSIONS` would change.
- The README permission matrix is generated from the map, and a test fails if
  the two drift apart.
