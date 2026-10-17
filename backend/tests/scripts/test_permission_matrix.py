from app.core.permissions import Permission
from scripts.permission_matrix import END, GRANTS, README, START, render_matrix


def test_every_permission_is_documented() -> None:
    assert set(GRANTS) == set(Permission)


def test_readme_matrix_matches_role_permissions() -> None:
    text = README.read_text()
    assert START in text and END in text, "README is missing the matrix markers"
    documented = text.split(START, 1)[1].split(END, 1)[0].strip()
    assert documented == render_matrix(), (
        "README permission matrix drifted from ROLE_PERMISSIONS; run "
        "`uv run python scripts/permission_matrix.py --write` in backend/"
    )
