# RBAC: notes, known limitations and future work

What was deliberately left out or deferred in the RBAC change.

## Known limitations

- **Concurrent demotion race.** The last-admin rule in `PATCH /users/{id}`
  counts active admins without locking. Two admins demoting each other at the
  same moment can both pass the check and leave zero admins. Closing it needs
  `SELECT ... FOR UPDATE` on the active admin rows before counting; judged not
  worth the complexity at this scope. Recovery today is manual
  (`UPDATE "user" SET role = 'admin' WHERE email = ...`); `init_db` does not
  re-promote an existing `FIRST_SUPERUSER`.
- **Lossy downgrade.** Downgrading the `b7e4c1d9a2f3` migration maps only
  admins back to `is_superuser = true`; managers come back as regular users.
- **Explicit nulls in `PATCH /users/{id}`.** `{"role": null}` is ignored, but
  `{"is_active": null}` or `{"email": null}` still reach the NOT NULL columns
  and return 500. Pre-existing in the template, left out of this change.
- **Logged path.** Denial logs record the route template (so path params such
  as an email never reach the logs), without the `/api/v1` prefix.

## Future work

- **404 instead of 403 for other users' items.** `GET/PUT/DELETE /items/{id}`
  returns 404 for a missing item but 403 for someone else's, which lets a
  member probe which item ids exist. Returning 404 for both (for callers
  without `items:manage_all`) would close that; item semantics were kept as-is
  here.
- **Admin-tools permission.** `system:manage` covers the test-email and
  password-recovery-preview endpoints. Split it if those ever need different
  audiences.

## Naming left as-is to keep the diff small

These still say "superuser" but mean "the seeded admin":

- Backend test fixture `superuser_token_headers` and helper
  `get_superuser_token_headers`.
- Settings / env vars `FIRST_SUPERUSER` and `FIRST_SUPERUSER_PASSWORD`
  (`.env`, compose files, deploy workflows, deployment docs).
- Frontend e2e config `firstSuperuser` / `firstSuperuserPassword`.

## Unrelated issue noticed, not fixed here

- `frontend/src/routes/_layout/settings.tsx` uses `tabsConfig.slice(0, 3)`
  for privileged users, which is all three tabs, so admins still see the
  "Danger zone" tab even though the backend rejects their self-delete.
