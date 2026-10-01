"""Timezone-aware daily tariffs, with explicit uncertainty at counter/rate boundaries.
Flat rates are the constant case of the same daily price function. No model claims a
subinterval measurement when only a spanning cumulative-counter delta is available.
"""
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from sqlalchemy import select, func, case, and_, column, values, String, Float, literal
from .db import UTCDateTime, iso
from .models import Tariff
from .schemas import RateBand
from .common import DomainError, record_dict
from .energy_sql import seconds_between

MAX_PRICE_WINDOWS = 3000


def daily_pieces(tariff):
    try:
        bands = sorted([RateBand.model_validate(x) for x in tariff.bands or []],key=lambda b:b.start_minute)
    except ValueError:
        raise DomainError("tariff_invalid", "Persisted tariff bands fail the pricing contract", 422)
    if any(a.end_minute>b.start_minute for a,b in zip(bands,bands[1:])):
        raise DomainError("tariff_invalid", "Persisted tariff bands overlap", 422)
    pieces, cursor = [],0
    for band in bands:
        if cursor<band.start_minute:
            pieces.append((cursor,band.start_minute,tariff.rate_per_kwh))
        pieces.append((band.start_minute,band.end_minute,band.rate_per_kwh))
        cursor=band.end_minute
    if cursor<1440:
        pieces.append((cursor,1440,tariff.rate_per_kwh))
    merged=[]
    for start,end,rate in pieces:
        if merged and merged[-1][2]==rate:
            merged[-1]=(merged[-1][0],end,rate)
        else:
            merged.append((start,end,rate))
    return merged


def utc_price_windows(tariff, start, end):
    """Return disjoint UTC windows. Ambiguous/nonexistent price-switch wall times
    are rejected explicitly; no undocumented DST-fold or gap policy is invented.
    """
    start,end=max(start,tariff.valid_from),min(end,tariff.valid_to)
    if end<=start:
        return []
    pieces=daily_pieces(tariff)
    if len(pieces)==1:
        return [(start,end,pieces[0][2])]
    try:
        zone=ZoneInfo(tariff.timezone)
    except (ZoneInfoNotFoundError,ValueError):
        raise DomainError("tariff_timezone_unknown", "Tariff timezone is unavailable", 422)
    switches=[segment[0] for i,segment in enumerate(pieces) if segment[2]!=pieces[i-1][2]]
    local_start,local_end=start.astimezone(zone),end.astimezone(zone)
    first,last=min(local_start.date(),local_end.date()),max(local_start.date(),local_end.date())
    if (last-first).days>368:
        raise DomainError("tariff_scope_too_large", "Price-window scope exceeds one year", 422)
    boundaries={start,end}
    date=first-timedelta(days=1)
    while date<=last+timedelta(days=1):
        for minute in switches:
            wall=datetime.combine(date,time.min)+timedelta(minutes=minute)
            candidates=set()
            for fold in (0,1):
                candidate=wall.replace(tzinfo=zone,fold=fold).astimezone(timezone.utc)
                if candidate.astimezone(zone).replace(tzinfo=None)==wall:
                    candidates.add(candidate)
            if len(candidates)!=1:
                if first<=date<=last:
                    raise DomainError("tariff_wall_time_unresolved", "Tariff contains an ambiguous or nonexistent local price-switch time; an explicit transition policy is required", 422,
                        {"tariff_id":tariff.id,"timezone":tariff.timezone,"local_time":wall.isoformat(),"kind":"ambiguous" if candidates else "nonexistent"})
                continue
            candidate=next(iter(candidates))
            if start<candidate<end:
                boundaries.add(candidate)
        date+=timedelta(days=1)
    result=[]
    ordered=sorted(boundaries)
    for left,right in zip(ordered,ordered[1:]):
        middle=(left+(right-left)/2).astimezone(zone)
        minute=middle.hour*60+middle.minute+middle.second/60+middle.microsecond/60_000_000
        rate=next(rate for low,high,rate in pieces if low<=minute<high)
        if result and result[-1][2]==rate:
            result[-1]=(result[-1][0],right,rate)
        else:
            result.append((left,right,rate))
    return result


def unavailable(energy, mode, message, error=None):
    energy.update(amount=None,currency=None,tariff_id=None,tariff=None,tariffs_used=[],quality="unavailable",pricing_mode=mode,
        boundary_estimated_intervals=0,boundary_unresolved_intervals=None,pricing_coverage_ratio=None,charge_type="configured_energy_charge_estimate",
        settlement_bill=False,excluded_components=["separate_demand_charges","separate_fixed_charges"])
    energy["warnings"].append(message)
    if error:
        energy["pricing_error"]={"code":error.code,"message":error.message,"details":error.details}
    return energy


def prepare_price(db,projection,start,end,allocation_mode="strict"):
    if allocation_mode not in {"strict","proportional_estimate"}:
        raise DomainError("invalid_pricing_mode", "Use strict or proportional_estimate pricing mode", 422)
    tariffs=list(db.scalars(select(Tariff).where(Tariff.valid_from<end,Tariff.valid_to>start)))
    window_rows=[]
    try:
        for tariff in tariffs:
            for left,right,rate in utc_price_windows(tariff,start,end):
                window_rows.append((tariff.id,tariff.source_mode,tariff.currency,left,right,rate))
                if len(window_rows)>MAX_PRICE_WINDOWS:
                    return {"unavailable":"Too many derived UTC price windows; narrow the period. No partial charge is returned","error":None}
    except DomainError as exc:
        return {"unavailable":exc.message,"error":exc}
    if not window_rows:
        return {"unavailable":"No applicable tariff windows are configured","error":None}
    windows=values(column("tariff_id",String),column("source_mode",String),column("currency",String),column("starts",UTCDateTime),column("ends",UTCDateTime),column("rate",Float)).data(window_rows).cte("tariff_utc_windows")
    p,w=projection.c,windows.c
    join=and_(p.source_mode==w.source_mode,p.start<w.ends,p.end>w.starts)
    greatest=func.greatest if db.bind.dialect.name=="postgresql" else func.max
    least=func.least if db.bind.dialect.name=="postgresql" else func.min
    overlap=case((w.tariff_id.is_not(None),seconds_between(db,least(p.end,w.ends),greatest(p.start,w.starts))),else_=0.0)
    mapped=select(p.to_sample_id,p.known_kwh,p.seconds,func.count(w.tariff_id).label("segments"),func.count(func.distinct(w.rate)).label("rates"),
        func.count(func.distinct(w.currency)).label("currencies"),func.sum(overlap).label("covered"),func.min(w.rate).label("single_rate"),
        func.sum(case((w.tariff_id.is_not(None),p.known_kwh*overlap/p.seconds*w.rate),else_=0.0)).label("allocated_charge"))
    mapped=mapped.select_from(projection.outerjoin(windows,join)).where(p.reason.is_(None)).group_by(p.to_sample_id,p.known_kwh,p.seconds).cte("priced_energy_intervals")
    m=mapped.c
    complete=and_(m.segments>0,func.abs(m.covered-m.seconds)<0.000001,m.currencies==1)
    resolved=and_(complete,True if allocation_mode=="proportional_estimate" else m.rates==1)
    charge=case((m.rates==1,m.known_kwh*m.single_rate),else_=m.allocated_charge)
    totals=select(func.sum(case((resolved,charge),else_=0.0)).label("amount"),
        func.sum(case((~resolved,1),else_=0)).label("unresolved"),
        func.sum(case((and_(complete,m.rates>1),1),else_=0)).label("boundary"),
        func.sum(case((and_(resolved,m.rates>1),1),else_=0)).label("estimated"),
        func.sum(case((resolved,m.seconds),else_=0.0)).label("priced_seconds"),func.sum(m.seconds).label("total_seconds")).select_from(mapped)
    # A single complete constant window per source is the natural flat-rate
    # case. Its join is cardinality-preserving, so no per-interval DISTINCT/sort is
    # necessary. Partial dates, overlapping versions and real rate switches use
    # the same general interval-boundary uncertainty calculation above.
    by_source={}
    for row in window_rows:
        by_source.setdefault(row[1],[]).append(row)
    constant=all(len(rows)==1 and rows[0][3]<=start and rows[0][4]>=end for rows in by_source.values())
    if constant:
        present=w.tariff_id.is_not(None)
        totals=select(func.sum(case((present,p.known_kwh*w.rate),else_=0.0)).label("amount"),
            func.sum(case((~present,1),else_=0)).label("unresolved"),literal(0).label("boundary"),literal(0).label("estimated"),
            func.sum(case((present,p.seconds),else_=0.0)).label("priced_seconds"),func.sum(p.seconds).label("total_seconds"))            .select_from(projection.outerjoin(windows,join)).where(p.reason.is_(None))
    used=select(w.tariff_id.label("id")).select_from(projection.join(windows,join)).where(p.reason.is_(None)).distinct()
    return {"totals":totals,"used":used,"tariffs":tariffs,"window_count":len(window_rows)}


def pricing_queries(plan):
    """Tagged branches share the request's canonical raw interval CTE."""
    if "unavailable" in plan:
        return []
    from .energy_sql import aggregate_fields
    totals=plan["totals"].cte("overview_price_totals")
    used=plan["used"].cte("overview_price_ids")
    return [select(*aggregate_fields(tag=literal("cost"),**{name:totals.c[name] for name in ("amount","unresolved","boundary","estimated","priced_seconds","total_seconds")})),
        select(*aggregate_fields(tag=literal("cost_tariff"),id=used.c.id))]


def price_energy(db,energy,projection,start,end,allocation_mode="strict",plan=None,aggregate_rows=None):
    plan=plan or prepare_price(db,projection,start,end,allocation_mode)
    if "unavailable" in plan:
        return unavailable(energy,allocation_mode,plan["unavailable"],plan["error"])
    if aggregate_rows is None:
        row=db.execute(plan["totals"]).mappings().one()
        used_ids=set(db.scalars(plan["used"]))
    else:
        row=next(row for row in aggregate_rows if row["tag"]=="cost")
        used_ids={row["id"] for row in aggregate_rows if row["tag"]=="cost_tariff"}
    amount,unresolved,boundary,estimated,priced_seconds,total_seconds=(row[name] for name in ("amount","unresolved","boundary","estimated","priced_seconds","total_seconds"))
    tariffs=plan["tariffs"]
    used={t.id:t for t in tariffs if t.id in used_ids}
    currencies={t.currency for t in used.values()}
    unresolved,boundary,estimated=unresolved or 0,boundary or 0,estimated or 0
    eligible=bool(energy["interval_count"]) and not unresolved and len(currencies)==1
    if unresolved:
        energy["quality"]="unavailable"
        energy["warnings"].append(f"{unresolved} intervals have incomplete/overlapping price coverage or unresolved rate boundaries")
    if len(currencies)>1:
        energy["quality"]="unavailable"
        energy["warnings"].append("Mixed currencies cannot be summed without an explicit conversion model")
    if estimated:
        if eligible:
            energy["quality"]="estimated"
        energy["warnings"].append(f"{estimated} counter intervals were allocated proportionally by elapsed UTC time; subinterval energy was not measured")
    single=next(iter(used.values())) if len(used)==1 else None
    energy.update(amount=round(amount,4) if eligible else None,currency=next(iter(currencies)) if len(currencies)==1 else None,
        tariff_id=single.id if single else None,tariff=record_dict(single) if single else None,tariffs_used=list(used),pricing_mode=allocation_mode,
        boundary_estimated_intervals=estimated,boundary_unresolved_intervals=boundary if allocation_mode=="strict" else 0,
        pricing_coverage_ratio=round((priced_seconds or 0)/total_seconds,6) if total_seconds else None,
        charge_type="configured_energy_charge_estimate",settlement_bill=False,excluded_components=["separate_demand_charges","separate_fixed_charges"],
        allocation_method="elapsed-UTC-time proportions with conserved counter delta" if estimated else "constant rate over each eligible counter interval",
        derived_price_windows=plan["window_count"])
    return energy
