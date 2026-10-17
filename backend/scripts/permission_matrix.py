"""Render the role -> permission matrix from ROLE_PERMISSIONS as Markdown.

    uv run python scripts/permission_matrix.py           # print the table
    uv run python scripts/permission_matrix.py --write   # update README.md
    uv run python scripts/permission_matrix.py --check   # exit 1 on drift

The README holds the table between the START and END markers below;
tests/scripts/test_permission_matrix.py fails if it drifts from the code.
"""

import argparse
import sys
from pathlib import Path

from app.core.permissions import ROLE_PERMISSIONS, Permission, Role

README = Path(__file__).resolve().parents[2] / "README.md"
START = "<!-- permission-matrix:start -->"
END = "<!-- permission-matrix:end -->"

# What each permission unlocks, for the docs only; enforcement lives in the
# routes. Every Permission must have an entry, or rendering fails.
GRANTS: dict[Permission, str] = {
    Permission.USERS_READ: "List users and view any user (`GET /users/`, `GET /users/{id}`)",
    Permission.USERS_CREATE: "Create users with any role (`POST /users/`)",
    Permission.USERS_UPDATE: "Update any user, including role and active flag (`PATCH /users/{id}`)",
    Permission.USERS_DELETE: "Delete other users (`DELETE /users/{id}`)",
    Permission.ITEMS_MANAGE_ALL: "List, view, update and delete everyone's items (`/items/`)",
    Permission.METRICS_READ: "View usage metrics (`GET /metrics/`)",
    Permission.SYSTEM_MANAGE: "Admin tools: test email, password-reset email preview",
}


def render_matrix() -> str:
    roles = list(Role)
    header = "| Permission | Grants | " + " | ".join(r.capitalize() for r in roles)
    divider = "|---|---|" + "|".join(":-:" for _ in roles)
    rows = [
        f"| `{permission}` | {GRANTS[permission]} | "
        + " | ".join("✓" if permission in ROLE_PERMISSIONS[r] else "–" for r in roles)
        for permission in Permission
    ]
    return "\n".join([f"{header} |", f"{divider}|", *(f"{row} |" for row in rows)])


def replace_block(text: str, table: str) -> str:
    before, rest = text.split(START, 1)
    _, after = rest.split(END, 1)
    return f"{before}{START}\n{table}\n{END}{after}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="update README.md")
    mode.add_argument("--check", action="store_true", help="exit 1 on drift")
    args = parser.parse_args()

    table = render_matrix()
    if not (args.write or args.check):
        print(table)  # noqa: T201
        return 0
    text = README.read_text()
    updated = replace_block(text, table)
    if args.check:
        if updated != text:
            print("README permission matrix is out of date; run --write")  # noqa: T201
            return 1
        return 0
    README.write_text(updated)
    return 0


if __name__ == "__main__":
    sys.exit(main())
