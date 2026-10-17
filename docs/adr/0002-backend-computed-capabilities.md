# ADR 0002: The backend computes capabilities and returns them on /users/me

- **Status:** Accepted
- **Date:** 2026-10-17

## Context

The React frontend has to hide links, buttons and whole pages the current user
can't use. The backend remains the only enforcement point, but the UI should
agree with it, including on a hard refresh and right after a role change.
Whatever the frontend relies on must not create a second copy of the
role → permission map ([ADR 0001](0001-permission-based-rbac.md)) that could
drift from the backend's.

## Options

1. **Return only the role; the frontend maps it to capabilities.** This is
   simple on the wire, but it duplicates `ROLE_PERMISSIONS` in TypeScript. Every
   grant change must then be made twice, and if the two copies disagree the UI
   misleads users.
2. **Put permissions (or the role) in the JWT claims.** No extra request is
   needed, but the claims are frozen for the token's lifetime (eight days by
   default). A demoted user keeps seeing admin UI until the token expires, and
   the backend would have to choose between trusting stale claims and
   re-reading the database anyway.
3. **A separate `/users/me/permissions` endpoint.** It keeps `UserPublic`
   unchanged but costs an extra request and a second cache entry that can fall
   out of sync with the user.
4. **Add the computed permissions to the existing `/users/me` response.** The
   frontend already fetches and caches this response as `["currentUser"]`.

## Decision

Option 4. `GET /users/me` returns `UserMe`, which is `UserPublic` plus
`permissions: list[Permission]`, computed from `ROLE_PERMISSIONS` on every
request. The `Permission` enum appears in the OpenAPI schema, so the generated
TypeScript client exposes a typed `Permission` union.

The frontend gates UI with `usePermission(perm)` and `can(user, perm)`. Route
guards (`requirePermission` in `beforeLoad`) read the same cached query. `role`
is still returned, but only for display.

## Consequences

- There is one source of truth. A grant change on the backend reaches the UI on
  the next `/users/me` fetch, with no frontend change.
- A misspelled permission in the frontend fails to compile.
- The UI can be stale until `["currentUser"]` is refetched. The backend still
  rejects the request, and the frontend shows a toast on 403. The cache is
  cleared on logout and login, and refreshed after editing your own account.
- The user list doesn't carry permissions on every row, because only `UserMe`
  has the field.
- Role-invariant rules (an admin can't delete themselves) aren't permissions,
  so they aren't visible to the frontend this way. The Danger-zone tab
  limitation in NOTES.md follows from that.
