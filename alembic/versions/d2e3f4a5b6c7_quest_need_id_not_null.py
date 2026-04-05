"""quest need_id NOT NULL

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-04-05 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'd2e3f4a5b6c7'
down_revision = 'c1d2e3f4a5b6'
branch_labels = None
depends_on = None


def upgrade():
    # need_id가 NULL인 고아 퀘스트를 먼저 삭제한다.
    op.execute("DELETE FROM quests WHERE need_id IS NULL")
    # SQLite does not support ALTER COLUMN directly — recreate the table.
    with op.batch_alter_table('quests') as batch_op:
        batch_op.alter_column('need_id', nullable=False)


def downgrade():
    with op.batch_alter_table('quests') as batch_op:
        batch_op.alter_column('need_id', nullable=True)
