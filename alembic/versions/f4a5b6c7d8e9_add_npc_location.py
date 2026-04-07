"""add location to npcs

Revision ID: f4a5b6c7d8e9
Revises: d2e3f4a5b6c7
Create Date: 2026-04-07 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'f4a5b6c7d8e9'
down_revision = 'd2e3f4a5b6c7'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('npcs') as batch_op:
        batch_op.add_column(
            sa.Column('location', sa.String(), nullable=False, server_default='home')
        )


def downgrade():
    with op.batch_alter_table('npcs') as batch_op:
        batch_op.drop_column('location')
