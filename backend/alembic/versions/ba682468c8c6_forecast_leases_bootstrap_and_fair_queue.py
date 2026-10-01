"""Forecast work leases, cold-history marker and bounded fair job deferral.

Revision ID: ba682468c8c6
Revises: 6d7d7c3c7c86
"""
from alembic import op
import sqlalchemy as sa
from app.db import UTCDateTime

revision='ba682468c8c6'
down_revision='6d7d7c3c7c86'
branch_labels=None
depends_on=None


def upgrade():
    with op.batch_alter_table('forecast_dirty_hours') as batch:
        batch.add_column(sa.Column('lease_id',sa.String(80),nullable=True))
        batch.add_column(sa.Column('lease_expires_at',UTCDateTime(),nullable=True))
    with op.batch_alter_table('forecast_projection_state') as batch:
        batch.add_column(sa.Column('history_initialized',sa.Boolean(),nullable=False,server_default=sa.false()))
    with op.batch_alter_table('forecast_runs') as batch:
        batch.add_column(sa.Column('not_before',UTCDateTime(),nullable=True))
    op.execute(sa.text('UPDATE forecast_runs SET not_before=requested_at WHERE not_before IS NULL'))
    with op.batch_alter_table('forecast_runs') as batch:
        batch.alter_column('not_before',existing_type=UTCDateTime(),nullable=False)
        batch.create_index('ix_forecast_runs_not_before',['not_before'])
    from app.invariants import install_database_invariants
    install_database_invariants(op.get_bind())


def downgrade():
    if op.get_bind().dialect.name=='postgresql':
        op.execute(sa.text('DROP TRIGGER IF EXISTS forecast_append_only ON forecast_hour_revisions'))
        op.execute(sa.text('DROP FUNCTION IF EXISTS carbentra_forecast_append_only()'))
    elif op.get_bind().dialect.name=='sqlite':
        op.execute(sa.text('DROP TRIGGER IF EXISTS forecast_no_update'))
        op.execute(sa.text('DROP TRIGGER IF EXISTS forecast_no_delete'))
    with op.batch_alter_table('forecast_runs') as batch:
        batch.drop_index('ix_forecast_runs_not_before')
        batch.drop_column('not_before')
    with op.batch_alter_table('forecast_projection_state') as batch:
        batch.drop_column('history_initialized')
    with op.batch_alter_table('forecast_dirty_hours') as batch:
        batch.drop_column('lease_expires_at')
        batch.drop_column('lease_id')
