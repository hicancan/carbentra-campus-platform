"""Server-side campus authorization applied to every ORM read, including direct-ID gets.
No UI filter is an authorization boundary. Ingestion uses its separate explicit device ACL.
"""
from sqlalchemy import event, or_
from sqlalchemy.orm import Session, with_loader_criteria
from .models import Campus, Building, Floor, Space, Circuit, Device, Binding, Telemetry, Command, Alarm, Strategy, Evaluation, Report, Audit, Event, AdapterObservation, SimulatedOutput, ScheduleEvent, CommissioningRecord, ForecastHourRevision, ForecastProjectionState, DeviceChannel, ChannelObservation, HardwareEvent, RoomMode, RoomPolicy, RoomEvaluation, RoomAnomaly, ChannelAcknowledgement, ChannelHold, SimulatedChannelOutput, RoomAnomalyRule


@event.listens_for(Session, "do_orm_execute")
def enforce_scope(execute_state):
    scope = execute_state.session.info.get("campus_ids")
    if scope is None or not execute_state.is_select:
        return
    statement = execute_state.statement
    for model in (Building, Space, Circuit, Device, Binding, Telemetry, Command, Alarm, Strategy, AdapterObservation, SimulatedOutput, ScheduleEvent, CommissioningRecord, ForecastHourRevision, ForecastProjectionState, DeviceChannel, ChannelObservation, HardwareEvent, RoomMode, RoomPolicy, RoomEvaluation, RoomAnomaly, ChannelAcknowledgement, ChannelHold, SimulatedChannelOutput, RoomAnomalyRule):
        if model in (Device, DeviceChannel) and execute_state.execution_options.get("authorized_historical_identity"):
            continue
        statement = statement.options(with_loader_criteria(model, model.campus_id.in_(scope), include_aliases=True))
    statement = statement.options(with_loader_criteria(Campus, Campus.id.in_(scope), include_aliases=True))
    statement = statement.options(with_loader_criteria(Floor, Floor.building_id.in_(execute_state.session.query(Building.id).filter(Building.campus_id.in_(scope)).statement), include_aliases=True))
    statement = statement.options(with_loader_criteria(Evaluation, Evaluation.strategy_id.in_(execute_state.session.query(Strategy.id).filter(Strategy.campus_id.in_(scope)).statement), include_aliases=True))
    actor = execute_state.session.info.get("actor")
    statement = statement.options(with_loader_criteria(Report, or_(Report.campus_id.in_(scope), Report.created_by == actor), include_aliases=True))
    statement = statement.options(with_loader_criteria(Audit, or_(Audit.campus_id.in_(scope), (Audit.campus_id.is_(None)) & (Audit.actor == actor)), include_aliases=True))
    statement = statement.options(with_loader_criteria(Event, Event.campus_id.in_(scope), include_aliases=True))
    execute_state.statement = statement


def report_scope_predicate(db, user):
    """Bound report pagination by immutable snapshot scope without loading contents."""
    from sqlalchemy import select, func, exists, and_, case, cast, literal, JSON
    if user.campus_ids is None:
        return literal(True)
    scope=user.campus_ids
    data=Report.parameters["authorized_campus_ids"]
    if db.bind.dialect.name=="postgresql":
        is_array=func.coalesce(func.json_typeof(data)=="array",False)
        safe=case((is_array,data),else_=cast(literal("[]"),JSON))
        members=func.json_array_elements_text(safe).table_valued("value").alias("report_scope_members")
    else:
        is_array=func.coalesce(func.json_type(Report.parameters,"$.authorized_campus_ids")=="array",False)
        members=func.json_each(Report.parameters,"$.authorized_campus_ids").table_valued("value").alias("report_scope_members")
    outside=exists(select(literal(1)).select_from(members).where(members.c.value.not_in(scope)).correlate(Report))
    explicit=and_(is_array,~outside)
    legacy_single=and_(~is_array,Report.campus_id.in_(scope))
    return or_(explicit,legacy_single)
