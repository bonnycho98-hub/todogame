"""init

Revision ID: 6c6edb007ef7
Revises:
Create Date: 2026-04-05 16:36:29.288793

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '6c6edb007ef7'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'npcs',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('relation_type', sa.String(), nullable=False),
        sa.Column('sprite', sa.Text(), nullable=False),
        sa.Column('color', sa.String(7), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    op.create_table(
        'needs',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('npc_id', sa.Uuid(as_uuid=True), sa.ForeignKey('npcs.id', ondelete='CASCADE'), nullable=True),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    op.create_table(
        'quests',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('need_id', sa.Uuid(as_uuid=True), sa.ForeignKey('needs.id', ondelete='CASCADE'), nullable=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('quest_type', sa.Enum('daily', 'one_time', name='questtype'), nullable=False),
        sa.Column('routine', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('intimacy_reward', sa.Integer(), nullable=True),
        sa.Column('is_archived', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    op.create_table(
        'subtasks',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('quest_id', sa.Uuid(as_uuid=True), sa.ForeignKey('quests.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('order', sa.Integer(), nullable=True),
    )
    op.create_table(
        'daily_completions',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('subtask_id', sa.Uuid(as_uuid=True), sa.ForeignKey('subtasks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('completed_date', sa.Date(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
    )
    op.create_table(
        'one_time_completions',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('subtask_id', sa.Uuid(as_uuid=True), sa.ForeignKey('subtasks.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
    )
    op.create_table(
        'intimacy_logs',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('npc_id', sa.Uuid(as_uuid=True), sa.ForeignKey('npcs.id', ondelete='CASCADE'), nullable=True),
        sa.Column('delta', sa.Integer(), nullable=False),
        sa.Column('reason', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    op.create_table(
        'level_rewards',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('level', sa.Integer(), nullable=False, unique=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('is_claimed', sa.Boolean(), nullable=True),
        sa.Column('claimed_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('level_rewards')
    op.drop_table('intimacy_logs')
    op.drop_table('one_time_completions')
    op.drop_table('daily_completions')
    op.drop_table('subtasks')
    op.drop_table('quests')
    op.drop_table('needs')
    op.drop_table('npcs')
    op.execute('DROP TYPE IF EXISTS questtype')
