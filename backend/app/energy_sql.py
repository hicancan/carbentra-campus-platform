"""Canonical interval projection in the database; raw telemetry remains authoritative.
The query returns aggregates rather than hydrating unbounded raw ORM objects. Each
interval preserves device/boot/binding/source identity and explicit exclusion reasons.
"""
from datetime import timezone
from sqlalchemy import select, func, case, and_, or_, literal, Float, Integer, BigInteger, String, cast, type_coerce, union_all
from .models import Telemetry
from .common import DomainError

MAX_SQL_SAMPLES = 5_000_000


def seconds_between(db, end, start):
    if db.bind.dialect.name == "postgresql":
        return cast(func.extract("epoch", end-start), Float)
    # SQLite julianday has ~40µs cancellation error, enough to turn exact full
    # coverage into 0.999999. Subtract whole Unix seconds and stored microseconds
    # separately; ORM UTCDateTime writes the canonical 26-character timestamp.
    whole = cast(func.strftime("%s",func.substr(end,1,19)),Integer)-cast(func.strftime("%s",func.substr(start,1,19)),Integer)
    fraction = (cast(func.substr(end,21,6),Float)-cast(func.substr(start,21,6),Float))/1_000_000.0
    return whole+fraction


def project_intervals(db, devices, start, end, campus_id=None, building_id=None):
    from datetime import timedelta
    ids = [d.id for d in devices]
    binding_ids = {bid for d in devices for bid in d.eligible_binding_ids}
    if len(binding_ids) > 20000:
        raise DomainError("accounting_scope_too_large", "Too many historical placement boundaries; narrow the period or campus", 422, {"partial_result_returned": False})
    t = Telemetry.__table__
    filters = [t.c.device_id.in_(ids), t.c.observed_at >= start-timedelta(hours=1), t.c.observed_at <= end]
    if campus_id:
        filters.append(t.c.campus_id == campus_id)
    if building_id:
        filters.append(t.c.building_id == building_id)
    allowed = db.info.get("campus_ids")
    if allowed is not None:
        filters.append(t.c.campus_id.in_(allowed))
    count = db.scalar(select(func.count()).select_from(t).where(*filters)) if ids else 0
    if count > MAX_SQL_SAMPLES:
        raise DomainError("accounting_scope_too_large", "Requested interval workload exceeds the bounded SQL accounting limit; narrow the period or building scope", 422,
            {"sample_count": count, "maximum_samples": MAX_SQL_SAMPLES, "partial_result_returned": False})
    window = {"partition_by": t.c.device_id, "order_by": (t.c.observed_at, t.c.id)}
    uncertain = cast(t.c.raw_payload["energy_uncertain_intervals"].as_string(), BigInteger)
    columns = [t.c.id, t.c.device_id, t.c.building_id, t.c.circuit_id, t.c.binding_id, t.c.boot_epoch, t.c.sample_seq, t.c.observed_at,
        t.c.energy_import_wh, t.c.energy_export_wh, t.c.quality, t.c.source_mode, uncertain.label("uncertain")]
    for name, value in [("prior_id",t.c.id),("prior_binding",t.c.binding_id),("prior_circuit",t.c.circuit_id),("prior_boot",t.c.boot_epoch),
        ("prior_seq",t.c.sample_seq),("prior_at",t.c.observed_at),("prior_import",t.c.energy_import_wh),("prior_export",t.c.energy_export_wh),
        ("prior_quality",t.c.quality),("prior_uncertain",uncertain),("prior_source",t.c.source_mode)]:
        columns.append(type_coerce(func.lag(value).over(**window), value.type).label(name))
    pairs = select(*columns).where(*filters).cte("energy_pairs")
    p = pairs.c
    dt = seconds_between(db,p.observed_at,p.prior_at)
    seq_newer = or_(func.length(p.sample_seq)>func.length(p.prior_seq), and_(func.length(p.sample_seq)==func.length(p.prior_seq), p.sample_seq>p.prior_seq))
    # Canonical decimal sequence strings are compared exactly without floating point
    # or signed-int64 casts, including the upper half of uint64.
    reason = case(
        (p.prior_id.is_(None), literal("first_sample")),
        (or_(p.binding_id.not_in(binding_ids),p.prior_binding.not_in(binding_ids),p.binding_id.is_(None),p.prior_binding.is_(None)),literal("measurement_boundary_excluded")),
        (p.prior_at < start,literal("partial_boundary")),
        (p.boot_epoch != p.prior_boot,literal("boot_boundary")),
        (or_(p.binding_id.is_distinct_from(p.prior_binding),p.circuit_id.is_distinct_from(p.prior_circuit)),literal("binding_boundary")),
        (or_(dt<=0,~seq_newer),literal("sequence_or_time_regression")),
        (dt > case((p.source_mode=="SIMULATED",1800.001),else_=30.001),literal("coverage_gap")),
        (or_(p.quality!="good",p.prior_quality!="good",p.source_mode!=p.prior_source),literal("quality_excluded")),
        (or_(p.energy_import_wh.is_(None),p.prior_import.is_(None),p.energy_export_wh.is_(None),p.prior_export.is_(None)),literal("missing_counter")),
        (or_(p.energy_import_wh<p.prior_import,p.energy_export_wh<p.prior_export),literal("counter_regression")),
        (func.coalesce(p.uncertain,0)!=func.coalesce(p.prior_uncertain,0),literal("uncertain_energy_interval")),
        else_=literal(None))
    projection = select(p.device_id,p.building_id,p.circuit_id,p.source_mode,p.prior_at.label("start"),p.observed_at.label("end"),dt.label("seconds"),
        ((p.energy_import_wh-p.prior_import)/1000.0).label("known_kwh"),((p.energy_export_wh-p.prior_export)/1000.0).label("export_kwh"),
        p.prior_id.label("from_sample_id"),p.id.label("to_sample_id"),reason.label("reason")).cte("energy_intervals")
    return projection, count


AGGREGATE_SHAPE={'tag':String(),'id':String(),'source_mode':String(),'reason':String(),'timestamp':String(),
    'known':Float(),'exported':Float(),'seconds':Float(),'count':BigInteger(),'active_kw':Float(),'devices':BigInteger(),
    'amount':Float(),'unresolved':BigInteger(),'boundary':BigInteger(),'estimated':BigInteger(),'priced_seconds':Float(),'total_seconds':Float()}


def aggregate_fields(**values):
    return [values.get(name,cast(literal(None),kind)).label(name) for name,kind in AGGREGATE_SHAPE.items()]


def aggregate_bundle(db,projection,overview=False,extra_queries=()):
    """One tagged statement reuses one materialized interval CTE for all views."""
    p=projection.c
    fields=aggregate_fields
    statements=[select(*fields(tag=literal('summary'),source_mode=p.source_mode,reason=p.reason,
        known=func.sum(p.known_kwh),exported=func.sum(p.export_kwh),seconds=func.sum(p.seconds),count=func.count()))
        .select_from(projection).group_by(p.source_mode,p.reason)]
    if overview:
        statements.append(select(*fields(tag=literal('building'),id=p.building_id,known=func.sum(p.known_kwh),
            seconds=func.sum(p.seconds),count=func.count())).where(p.reason.is_(None)).group_by(p.building_id))
        bucket=func.date_trunc('hour',func.timezone('UTC',p.end)) if db.bind.dialect.name=='postgresql' else func.strftime('%Y-%m-%dT%H:00:00Z',p.end)
        per_device=select(bucket.label('at'),p.device_id,func.sum(p.known_kwh).label('energy'),func.sum(p.seconds).label('seconds'),func.count().label('count'))            .where(p.reason.is_(None)).group_by(bucket,p.device_id).cte('overview_device_hours')
        h=per_device.c
        stamp=func.to_char(h.at,'YYYY-MM-DD"T"HH24:MI:SS"Z"') if db.bind.dialect.name=='postgresql' else h.at
        statements.append(select(*fields(tag=literal('hour'),timestamp=stamp,known=func.sum(h.energy),seconds=func.sum(h.seconds),
            count=func.sum(h.count),active_kw=func.sum(h.energy*3600.0/h.seconds),devices=func.count())).group_by(h.at))
    totals={'count':0,'known':None,'exported':None,'seconds':0.0,'reasons':{},'modes':set()}
    buildings,trend,extra={},[],[]
    statements.extend(extra_queries)
    for row in db.execute(union_all(*statements)):
        if row.tag=='summary':
            if row.reason is None:
                totals['count']+=int(row.count);totals['known']=(totals['known'] or 0.0)+float(row.known or 0.0)
                totals['exported']=(totals['exported'] or 0.0)+float(row.exported or 0.0);totals['seconds']+=float(row.seconds or 0.0)
                totals['modes'].add(row.source_mode)
            elif row.reason!='first_sample':
                totals['reasons'][row.reason]=totals['reasons'].get(row.reason,0)+int(row.count)
        elif row.tag=='building':
            buildings[row.id]={'id':row.id,'known_kwh':float(row.known),'seconds':float(row.seconds),'interval_count':int(row.count)}
        elif row.tag=='hour':
            trend.append({'timestamp':row.timestamp,'known_kwh':round(float(row.known),6),'active_kw':round(float(row.active_kw),6),
                'seconds':float(row.seconds),'interval_count':int(row.count),'observed_device_count':int(row.devices),
                'method':'interval-ending-hour; observed-interval mean power; no gap fill'})
        else:
            extra.append(dict(row._mapping))
    return {'totals':totals,'buildings':buildings,'trend':sorted(trend,key=lambda item:item['timestamp']),'extra':extra}


def summarize(db,projection):
    return aggregate_bundle(db,projection)['totals']


def interval_rows(db, projection):
    p=projection.c
    return [dict(row) for row in db.execute(select(projection).where(p.reason.is_(None))).mappings()]


def group_totals(db, projection, group_by):
    p=projection.c
    key=getattr(p,f"{group_by}_id")
    return {row.id:{"id":row.id,"known_kwh":float(row.known_kwh),"seconds":float(row.seconds),"interval_count":int(row.interval_count)} for row in db.execute(select(key.label("id"),func.sum(p.known_kwh).label("known_kwh"),func.sum(p.seconds).label("seconds"),func.count().label("interval_count")).where(p.reason.is_(None)).group_by(key))}


def hourly_totals(db, projection):
    p=projection.c
    # Attribute each measured delta to its interval-ending UTC hour. Power is the
    # sum of each observed meter's mean over its covered intervals, never a filled
    # value for a missing meter or an invented sub-hour counter allocation.
    hour=func.date_trunc("hour",func.timezone("UTC",p.end)) if db.bind.dialect.name=="postgresql" else func.strftime("%Y-%m-%dT%H:00:00Z",p.end)
    per_device=select(hour.label("timestamp"),p.device_id,func.sum(p.known_kwh).label("energy"),func.sum(p.seconds).label("seconds"),func.count().label("count")).where(p.reason.is_(None)).group_by(hour,p.device_id).cte("device_hour_energy")
    h=per_device.c
    rows=[]
    query=select(h.timestamp,func.sum(h.energy).label("known_kwh"),func.sum(h.seconds).label("seconds"),func.sum(h.count).label("interval_count"),
        func.sum(h.energy*3600.0/h.seconds).label("active_kw"),func.count().label("observed_device_count")).group_by(h.timestamp).order_by(h.timestamp)
    for row in db.execute(query):
        timestamp=row.timestamp
        if hasattr(timestamp,"isoformat"):
            from .db import iso
            timestamp=iso(timestamp)
        rows.append({"timestamp":timestamp,"known_kwh":round(float(row.known_kwh),6),"active_kw":round(float(row.active_kw),6),"seconds":float(row.seconds),
            "interval_count":int(row.interval_count),"observed_device_count":int(row.observed_device_count),"method":"interval-ending-hour; observed-interval mean power; no gap fill"})
    return rows
