"""add daily_quest_completions table

Revision ID: c1d2e3f4a5b6
Revises: b3f9a1c2d4e5
Create Date: 2026-04-05 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'c1d2e3f4a5b6'
down_revision = 'b3f9a1c2d4e5'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'daily_quest_completions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('quest_id', sa.Uuid(), nullable=False),
        sa.Column('completed_date', sa.Date(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['quest_id'], ['quests.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('daily_quest_completions')
