"""Add columns to Post table.

Revision ID: 3d4b3aa9a212
Revises: 877590b1c80e
Create Date: 2023-07-04 16:10:26.025323

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3d4b3aa9a212'
down_revision = '877590b1c80e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'post',
        sa.Column('likes_count', sa.Integer(), nullable=True),
        schema='webtronics'
    )
    op.add_column(
        'post',
        sa.Column('dislikes_count', sa.Integer(), nullable=True),
        schema='webtronics'
    )


def downgrade() -> None:
    op.drop_column('post', 'dislikes_count', schema='webtronics')
    op.drop_column('post', 'likes_count', schema='webtronics')
