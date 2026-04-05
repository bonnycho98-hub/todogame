"""add need is_archived

Revision ID: b3f9a1c2d4e5
Revises: 6c6edb007ef7
Create Date: 2026-04-05 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'b3f9a1c2d4e5'
down_revision = '6c6edb007ef7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'needs',
        sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='false')
    )


def downgrade():
    op.drop_column('needs', 'is_archived')
