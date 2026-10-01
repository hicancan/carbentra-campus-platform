"""A small database-enforced safety floor for immutable audit history."""
from sqlalchemy import event, text, inspect
from .models import Audit, ForecastHourRevision, ChannelObservation, HardwareEvent, ChannelAcknowledgement


@event.listens_for(Audit, "before_update")
@event.listens_for(Audit, "before_delete")
def immutable_audit(mapper, connection, target):
    raise ValueError("Audit history is append-only")


@event.listens_for(ForecastHourRevision, "before_update")
@event.listens_for(ForecastHourRevision, "before_delete")
def immutable_forecast_revision(mapper, connection, target):
    raise ValueError("Closed forecast evidence revisions are append-only")


def immutable_channel_evidence(mapper, connection, target):
    raise ValueError("Channel and hardware evidence is append-only")


for _model in (ChannelObservation, HardwareEvent, ChannelAcknowledgement):
    event.listen(_model, "before_update", immutable_channel_evidence)
    event.listen(_model, "before_delete", immutable_channel_evidence)


def install_database_invariants(connection):
    dialect = connection.dialect.name
    if dialect == "postgresql":
        connection.execute(text("""CREATE OR REPLACE FUNCTION carbentra_audit_append_only() RETURNS trigger AS $$
        BEGIN RAISE EXCEPTION 'audit history is append-only'; END; $$ LANGUAGE plpgsql"""))
        connection.execute(text("DROP TRIGGER IF EXISTS audit_append_only ON audit_log"))
        connection.execute(text("CREATE TRIGGER audit_append_only BEFORE UPDATE OR DELETE ON audit_log FOR EACH ROW EXECUTE FUNCTION carbentra_audit_append_only()"))
    elif dialect == "sqlite":
        connection.execute(text("CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit_log BEGIN SELECT RAISE(ABORT, 'audit history is append-only'); END"))
        connection.execute(text("CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit_log BEGIN SELECT RAISE(ABORT, 'audit history is append-only'); END"))

    # Early migrations may not have introduced the derived evidence table yet.
    if inspect(connection).has_table("forecast_hour_revisions"):
        if dialect == "postgresql":
            connection.execute(text("""CREATE OR REPLACE FUNCTION carbentra_forecast_append_only() RETURNS trigger AS $$
            BEGIN RAISE EXCEPTION 'closed forecast revisions are append-only'; END; $$ LANGUAGE plpgsql"""))
            connection.execute(text("DROP TRIGGER IF EXISTS forecast_append_only ON forecast_hour_revisions"))
            connection.execute(text("CREATE TRIGGER forecast_append_only BEFORE UPDATE OR DELETE ON forecast_hour_revisions FOR EACH ROW EXECUTE FUNCTION carbentra_forecast_append_only()"))
        elif dialect == "sqlite":
            connection.execute(text("CREATE TRIGGER IF NOT EXISTS forecast_no_update BEFORE UPDATE ON forecast_hour_revisions BEGIN SELECT RAISE(ABORT, 'closed forecast revisions are append-only'); END"))
            connection.execute(text("CREATE TRIGGER IF NOT EXISTS forecast_no_delete BEFORE DELETE ON forecast_hour_revisions BEGIN SELECT RAISE(ABORT, 'closed forecast revisions are append-only'); END"))

    for table in ("channel_observations", "hardware_events", "channel_acknowledgements"):
        if not inspect(connection).has_table(table):
            continue
        if dialect == "postgresql":
            connection.execute(text("CREATE OR REPLACE FUNCTION carbentra_channel_append_only() RETURNS trigger AS $$ BEGIN RAISE EXCEPTION 'channel and hardware evidence is append-only'; END; $$ LANGUAGE plpgsql"))
            connection.execute(text(f"DROP TRIGGER IF EXISTS {table}_append_only ON {table}"))
            connection.execute(text(f"CREATE TRIGGER {table}_append_only BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION carbentra_channel_append_only()"))
        elif dialect == "sqlite":
            connection.execute(text(f"CREATE TRIGGER IF NOT EXISTS {table}_no_update BEFORE UPDATE ON {table} BEGIN SELECT RAISE(ABORT, 'channel and hardware evidence is append-only'); END"))
            connection.execute(text(f"CREATE TRIGGER IF NOT EXISTS {table}_no_delete BEFORE DELETE ON {table} BEGIN SELECT RAISE(ABORT, 'channel and hardware evidence is append-only'); END"))
