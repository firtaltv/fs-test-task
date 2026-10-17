# RBAC: notes, verification and limitations

How to run it and how it works are in the [README](README.md#role-based-access-control).
Design decisions:

- [ADR 0001: permission-based RBAC](docs/adr/0001-permission-based-rbac.md)
- [ADR 0002: backend-computed capabilities](docs/adr/0002-backend-computed-capabilities.md)

## Verification

**Test suites.**

- Backend: 102 pytest tests pass.
  - 37 of them are in `tests/api/routes/test_rbac.py`.
  - The rest are the template's tests updated for roles, plus seeding and README-drift tests.
- Frontend: 70 Playwright tests pass, 8 of them in `tests/rbac.spec.ts`.
- Every commit on the branch passes the checks on its own:
  - backend: ruff, mypy, ty, and the app boots;
  - frontend: biome, tsc and the production build.

**Backend mutation testing.** To make sure the RBAC tests can fail, each row
below is a deliberate bug. I introduced it, ran the tests and reverted it. Every
bug was caught.

| Deliberate bug | Tests failing |
|---|---|
| Manager also gets `users:create` | 1 |
| Member also gets `metrics:read` | 1 |
| `check_permission` never denies | 14 |
| Denials not logged | 12 |
| Concrete URL logged instead of the route template (would leak an email) | 2 |
| Last-admin guard removed | 3 |
| Inactive admins counted towards the last-admin rule | 3 |
| `UserUpdateMe` accepts `role` (self-promotion) | 4 |
| `UserRegister` accepts `role` (signup as admin) | 1 |
| Role frozen at a user's first request (stale privileges) | 1 |
| Bad token returns 403 instead of 401 | 3 |
| Inactive user returns 400 instead of 403 | 1 |
| `/users/me` returns admin permissions to everyone | 2 |
| Seeding guard removed (demo users created outside development) | 1 |
| README matrix edited by hand, or the map changed without regenerating it | 1 each |

Every denial test asserts three things:

- the authz-specific `detail` in the response;
- the WARNING log line naming the expected permission;
- that it sent a valid request body.

So a 422, or a 403 from some other check, can't pass as a denial. The same
review found four template tests that passed vacuously after `is_superuser` was
dropped (Pydantic silently ignored the old field). They now assert the role
explicitly.

**Frontend breakages.** Three deliberate bugs, each caught by the e2e specs:

| Deliberate bug | Tests failing |
|---|---|
| `/admin` route guard removed | 2 |
| Row actions menu shown regardless of permission | 1 |
| Sidebar ignores permissions | 1 |

**Clean-checkout run.** I cloned the branch into a temp directory, ran
`docker compose down -v`, then followed only the README quick start. That covered
migrate, seed, backend tests (100 passed at that commit), both dev servers,
logging in as each seeded role, and the e2e suite (70 passed). What tripped me
up, now covered in the README:

- **Backend test teardown deleted every user**, including the seeded ones.
  This was inherited from the template. It's fixed now: see
  "Pre-existing bugs fixed along the way".
- **Containers from another checkout block the run.** The checkout's folder name sets the Compose project name. Containers from a checkout with the same name, or anything already on port 5432, collide. Run `docker compose down` there first.
- **Playwright needs a browser once:** `bunx playwright install chromium`.
- **`changethis` warnings at startup are expected in development.**

## Pre-existing bugs fixed along the way

- **Session cache leaked between users.** Logging out didn't clear the React
  Query cache, so after logging in as someone else in the same tab, the UI could
  show the previous user's links and buttons. The backend still refused their
  requests. With permission-gated UI this became visible, so logout now clears
  the cache and login drops the cached current user.
- **Backend tests wiped the dev database.** The tests share the `app`
  database with local development, and their teardown deleted every user and
  item. It now snapshots existing ids after `init_db` and deletes only the
  rows created during the run.
- **Lint failed after an e2e run.** biome checked Playwright output
  (`test-results/`, `playwright/.auth/`). It now ignores them.

## Known limitations

- **Danger-zone tab for admins.** Admins see the "Danger zone" (delete account)
  tab in settings, even though the backend rejects their self-delete. The
  template meant to hide it but used `tabsConfig.slice(0, 3)`, which is all
  three tabs. The RBAC change removed that no-op branch (it compared roles,
  which components must not do) without changing behaviour. A real fix needs a
  signal from the backend, such as a `can_delete_self` flag on `/users/me`,
  because "admins can't delete themselves" is a role invariant, not a
  permission ([ADR 0002](docs/adr/0002-backend-computed-capabilities.md)).
- **Concurrent demotion race.** The last-admin rule counts active admins
  without locking. Two admins demoting each other at the same moment can both
  pass the check and leave zero admins. Closing it needs `SELECT ... FOR UPDATE`
  on the active admin rows before counting, which I judged not worth the
  complexity at this scope. Recovery is manual
  (`UPDATE "user" SET role = 'admin' WHERE email = ...`), because `init_db`
  doesn't re-promote an existing `FIRST_SUPERUSER`.
- **Lossy downgrade.** Downgrading migration `b7e4c1d9a2f3` maps only admins
  back to `is_superuser = true`, so managers come back as regular users.
- **Stale UI until refetch.** If an admin changes someone's role, that user's
  UI updates on their next `/users/me` fetch. Until then the backend refuses
  their requests and the UI shows a 403 toast.
- **Inactive users with a live token** get a 403 toast on each request instead of being
  logged out, because 403 means "authenticated but not allowed".
- **Explicit nulls in `PATCH /users/{id}`.** `{"role": null}` is ignored, but
  `{"is_active": null}` or `{"email": null}` still reach the NOT NULL columns
  and return 500. This was already in the template and is left out of this change.
- **Logged path.** Denial logs record the route template, so path parameters
  such as an email never reach the logs. The template doesn't include the
  `/api/v1` prefix.

## Future work

- **404 instead of 403 for other users' items.** `GET/PUT/DELETE /items/{id}`
  returns 404 for a missing item but 403 for someone else's, so a member can
  probe which item ids exist. Returning 404 for both, for callers without
  `items:manage_all`, would close that. Item semantics were kept as-is here.
- **Split `system:manage`.** It covers the test-email and password-reset-preview
  endpoints. Split it if those ever need different audiences.

## Naming left as-is to keep the diff small

These still say "superuser" but mean "the seeded admin":

- Backend test fixture `superuser_token_headers` and helper
  `get_superuser_token_headers`.
- Settings and env vars `FIRST_SUPERUSER` and `FIRST_SUPERUSER_PASSWORD`
  (`.env`, compose files, deploy workflows, deployment docs).
- Frontend e2e config `firstSuperuser` / `firstSuperuserPassword`.

## Time

The brief was a ~1 hour timebox. This is the scope that fits it:

- the permissions module;
- the role column and migration;
- the `require_permission` dependency;
- converting the routes;
- the metrics stub;
- `/users/me` permissions;
- the focused backend RBAC tests.

Everything else went beyond it:

- the frontend (guards, Access denied, role UI, metrics page);
- the e2e specs;
- the mutation-testing passes;
- restructuring the commit history so every commit passes on its own;
- local seeding;
- the clean-checkout verification;
- the generated README matrix;
- the ADRs.

They're listed separately so a reviewer can judge the core on its own.
