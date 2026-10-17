"""Replace is_superuser with role

Superusers become admins, everyone else becomes a member.

The downgrade is lossy: only admins map back to is_superuser=True, so
managers come back as regular users.

Revision ID: b7e4c1d9a2f3
Revises: fe56fa70289e
Create Date: 2026-10-17 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7e4c1d9a2f3'
down_revision = 'fe56fa70289e'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'user',
        sa.Column('role', sa.String(length=32), nullable=False, server_default='member'),
    )
    op.execute("UPDATE \"user\" SET role = 'admin' WHERE is_superuser")
    op.drop_column('user', 'is_superuser')


def downgrade():
    op.add_column(
        'user',
        sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute("UPDATE \"user\" SET is_superuser = true WHERE role = 'admin'")
    op.drop_column('user', 'role')
