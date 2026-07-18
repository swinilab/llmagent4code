"""
Add recovery_log table.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0002_add_recovery_log_table'
down_revision = '0001_initial_migration'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'recovery_log',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('aggregate_type', sa.String(), nullable=False),
        sa.Column('aggregate_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('checkpoint_data', sa.JSON(), nullable=False),
        sa.Column('is_recovered', sa.Boolean(), default=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.func.now(), onupdate=sa.func.now())
    )


def downgrade():
    op.drop_table('recovery_log')