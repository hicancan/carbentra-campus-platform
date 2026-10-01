"""Interval accounting: Wh deltas, immutable placement, topology antichains, explicit gaps."""
from collections import defaultdict
from types import SimpleNamespace
from datetime import timedelta
from sqlalchemy import select, func, and_, case, literal
from .common import DomainError, record_dict
from .db import utcnow, iso
from .models import Device, Telemetry, Circuit, Building, CarbonFactor, Tariff, Binding


def period(start=None, end=None):
    end = end or utcnow()
    start = start or end - timedelta(hours=24)
    if start.tzinfo is None or end.tzinfo is None:
        raise DomainError("invalid_period", "Timestamps must include a timezone", 422)
    if end <= start or (end - start).total_seconds() > 366 * 86400:
        raise DomainError("invalid_period", "Use a positive interval no longer than 366 days", 422)
    return start, end


def scoped_devices(db, campus_id=None, building_id=None):
    query = select(Device)
    if campus_id:
        query = query.where(Device.campus_id == campus_id)
    if building_id:
        query = query.where(Device.building_id == building_id)
    return list(db.scalars(query).all())


def ensure_antichain(devices, circuits):
    by_id = {c.id: c for c in circuits}
    meters = {d.circuit_id: d.id for d in devices if d.kind == "meter" and d.circuit_id}
    for d in devices:
        if d.circuit_id in meters and meters[d.circuit_id] != d.id:
            raise DomainError("double_counting", "Cannot combine a meter and a load within its measurement boundary", 409)
        c = by_id.get(d.circuit_id)
        visited = set()
        while c and c.parent_id:
            if c.id in visited:
                raise DomainError("topology_cycle", "Electrical hierarchy contains a cycle", 409)
            visited.add(c.id)
            if c.parent_id in meters:
                raise DomainError("double_counting", "Cannot combine a parent meter with its descendant meters or loads", 409)
            c = by_id.get(c.parent_id)


def selected_devices(db, campus_id=None, building_id=None, device_ids=None, start=None, end=None):
    circuits = list(db.scalars(select(Circuit)).all())
    # Measurement placement is selected for the accounting interval, never from today's
    # device location. Each binding is immutable history; a move cannot rewrite totals.
    bindings_query = select(Binding)
    if start:
        bindings_query = bindings_query.where((Binding.valid_to.is_(None)) | (Binding.valid_to > start))
    if end:
        bindings_query = bindings_query.where(Binding.valid_from <= end)
    if campus_id:
        bindings_query = bindings_query.where(Binding.campus_id == campus_id)
    if building_id:
        bindings_query = bindings_query.where(Binding.building_id == building_id)
    bindings = list(db.scalars(bindings_query))
    by_device = defaultdict(list)
    for binding in bindings:
        by_device[binding.device_id].append(binding)
    if device_ids is not None:
        if not device_ids or len(device_ids) > 2000:
            raise DomainError("invalid_devices", "Select between 1 and 2000 distinct devices", 422)
        ids = set(device_ids)
        current_ids = set(db.scalars(select(Device.id).where(Device.id.in_(ids))))
        authorized_ids = current_ids | (ids & set(by_device))
        raw_devices = list(db.scalars(select(Device).where(Device.id.in_(authorized_ids)).execution_options(authorized_historical_identity=True)))
        if len(raw_devices) != len(ids):
            raise DomainError("unknown_device", "One or more requested devices do not exist", 404)
    else:
        current_ids = {d.id for d in scoped_devices(db, campus_id, building_id)}
        raw_devices = list(db.scalars(select(Device).where(Device.id.in_(current_ids | set(by_device))).execution_options(authorized_historical_identity=True)))
    devices = []
    for device in raw_devices:
        placements = by_device.get(device.id, [])
        circuit_ids = {b.circuit_id for b in placements} or {device.circuit_id}
        for circuit_id in circuit_ids:
            matched = [b for b in placements if b.circuit_id == circuit_id]
            devices.append(SimpleNamespace(id=device.id, circuit_id=circuit_id, kind=device.kind, capabilities=device.capabilities, source_mode=device.source_mode,
                eligible_binding_ids={b.id for b in matched}, eligible_circuit_ids={circuit_id}, eligible_building_ids={b.building_id for b in matched} or {device.building_id}))
    if device_ids is None:
        circuit_map = {c.id: c for c in circuits}
        meter_circuits = {d.circuit_id for d in devices if d.kind == "meter" and d.circuit_id}
        selected = []
        for d in devices:
            c = circuit_map.get(d.circuit_id)
            has_parent_meter = d.kind != "meter" and d.circuit_id in meter_circuits
            seen = set()
            while c and c.parent_id and not has_parent_meter:
                if c.id in seen:
                    raise DomainError("topology_cycle", "Electrical hierarchy contains a cycle", 409)
                seen.add(c.id)
                has_parent_meter = c.parent_id in meter_circuits
                c = circuit_map.get(c.parent_id)
            if not has_parent_meter and "metering" in d.capabilities:
                selected.append(d)
        devices = selected
    ensure_antichain(devices, circuits)
    merged = {}
    for device in devices:
        if device.id not in merged:
            merged[device.id] = device
        else:
            target = merged[device.id]
            target.eligible_binding_ids |= device.eligible_binding_ids
            target.eligible_circuit_ids |= device.eligible_circuit_ids
            target.eligible_building_ids |= device.eligible_building_ids
    return list(merged.values())


def energy_projection(db, campus_id=None, building_id=None, start=None, end=None, device_ids=None):
    from .energy_sql import project_intervals
    start, end = period(start, end)
    devices = selected_devices(db, campus_id, building_id, device_ids, start, end)
    projection, count = project_intervals(db, devices, start, end, campus_id, building_id)
    return start, end, devices, projection, count


def compute_energy(db, campus_id=None, building_id=None, start=None, end=None, device_ids=None, include_intervals=False, _prepared=None, _totals=None):
    from .energy_sql import summarize, interval_rows
    start, end, devices, projection, sample_count = _prepared or energy_projection(db, campus_id, building_id, start, end, device_ids)
    totals = _totals if _totals is not None else summarize(db, projection)
    seconds = (end-start).total_seconds()
    coverage = min(1.0, totals["seconds"]/(seconds*len(devices))) if devices else None
    modes = totals["modes"]
    mode = next(iter(modes)) if len(modes)==1 else "MIXED" if modes else "UNKNOWN"
    reasons = totals["reasons"]
    result = {"known_kwh":round(totals["known"],6) if totals["count"] else None, "export_kwh":round(totals["exported"],6) if totals["count"] else None,
        "coverage_ratio":round(coverage,6) if coverage is not None else None, "quality":"unknown" if not totals["count"] else "good" if coverage >= .95 else "partial",
        "period_start":iso(start), "period_end":iso(end), "device_count":len(devices), "interval_count":totals["count"], "excluded_intervals":sum(reasons.values()),
        "source_mode":mode, "warnings":[f"{k}:{v}" for k,v in sorted(reasons.items())]+(["SIMULATED: not measured campus consumption"] if "SIMULATED" in modes else [])+(["No eligible intervals"] if not totals["count"] else []),
        "method":"same_boot_monotonic_Wh_delta; interval-specific parent_meter_antichain; SQL aggregate; no gap imputation", "selected_device_ids":[d.id for d in devices],
        "queried_sample_count":sample_count}
    if include_intervals:
        if totals["count"] > 100000:
            raise DomainError("accounting_detail_too_large", "Raw interval detail exceeds the bounded export limit; use the aggregate summary or a narrower scope", 422, {"partial_result_returned":False})
        result["_intervals"] = interval_rows(db, projection)
    return result


def breakdown(db, group_by="building", **scope):
    from .energy_sql import group_totals
    start,end,selected,projection,_ = energy_projection(db,**scope)
    groups = group_totals(db,projection,group_by)
    expected = defaultdict(set)
    for device in selected:
        keys={device.id} if group_by=="device" else device.eligible_building_ids if group_by=="building" else device.eligible_circuit_ids
        for key in keys:
            expected[key].add(device.id)
    models={"building":Building,"device":Device,"circuit":Circuit}
    names={x.id:x.name for x in db.scalars(select(models[group_by])).all()}
    p=projection.c
    key_column=getattr(p,f"{group_by}_id")
    modes=defaultdict(set)
    for key,mode in db.execute(select(key_column,p.source_mode).where(p.reason.is_(None)).distinct()):
        modes[key].add(mode)
    duration=(end-start).total_seconds()
    result=[]
    for key,devices in expected.items():
        values=groups.get(key)
        coverage=min(1,(values["seconds"] if values else 0)/max(1,duration*len(devices)))
        result.append({"id":key,"name":names.get(key,"未绑定"),"known_kwh":round(values["known_kwh"],6) if values else None,"coverage_ratio":round(coverage,6),
            "quality":"good" if coverage>=.95 else "partial" if values else "unknown","source_mode":next(iter(modes[key])) if len(modes[key])==1 else "MIXED" if modes[key] else "UNKNOWN","device_count":len(devices)})
    return sorted(result,key=lambda x:x["known_kwh"] or 0,reverse=True)


def prepare_carbon(db,projection,start,end):
    p,f=projection.c,CarbonFactor.__table__.c
    condition=and_(f.valid_from<=p.start,f.valid_to>=p.end,f.source_mode==p.source_mode)
    matched=select(p.to_sample_id,p.known_kwh,func.count(f.id).label("matches"),func.max(f.kg_co2e_per_kwh).label("rate"))        .select_from(projection.outerjoin(CarbonFactor.__table__,condition)).where(p.reason.is_(None)).group_by(p.to_sample_id,p.known_kwh).cte("factor_matches")
    m=matched.c
    totals=select(func.sum(case((m.matches==1,m.known_kwh*m.rate),else_=0.0)).label("amount"),
        func.sum(case((m.matches!=1,1),else_=0)).label("unresolved")).select_from(matched)
    # Prove reference uniqueness once, rather than sorting every raw interval to
    # count matches. Corrupt/imported overlapping versions retain the exact general
    # ambiguity path; the optimization never assumes API validation was sufficient.
    records=list(db.scalars(select(CarbonFactor).where(CarbonFactor.valid_from<end,CarbonFactor.valid_to>start)))
    previous={};unique=True
    for record in sorted(records,key=lambda item:item.valid_from):
        if record.source_mode in previous and record.valid_from<previous[record.source_mode]:
            unique=False;break
        previous[record.source_mode]=record.valid_to
    if unique:
        totals=select(func.sum(case((f.id.is_not(None),p.known_kwh*f.kg_co2e_per_kwh),else_=0.0)).label("amount"),
            func.sum(case((f.id.is_(None),1),else_=0)).label("unresolved"))            .select_from(projection.outerjoin(CarbonFactor.__table__,condition)).where(p.reason.is_(None))
    used=select(f.id).select_from(projection.join(CarbonFactor.__table__,condition)).where(p.reason.is_(None)).distinct()
    return {"totals":totals,"used":used,"records":records}


def carbon_queries(plan):
    from .energy_sql import aggregate_fields
    totals=plan["totals"].cte("overview_carbon_totals");used=plan["used"].cte("overview_carbon_ids")
    return [select(*aggregate_fields(tag=literal("carbon"),amount=totals.c.amount,unresolved=totals.c.unresolved)),
        select(*aggregate_fields(tag=literal("carbon_factor"),id=used.c.id))]


def apply_accounting(db,kind,allocation_mode="strict",_prepared=None,_energy=None,_plan=None,_aggregate_rows=None,**scope):
    from copy import deepcopy
    prepared=_prepared or energy_projection(db,**scope)
    energy=deepcopy(_energy) if _energy is not None else compute_energy(db,_prepared=prepared,**scope)
    start,end,devices,projection,_=prepared
    if kind=="cost":
        from .pricing import price_energy
        return price_energy(db,energy,projection,start,end,allocation_mode,plan=_plan,aggregate_rows=_aggregate_rows)
    if kind!="carbon":
        raise DomainError("invalid_accounting_kind","Use carbon or cost accounting",422)
    plan=_plan or prepare_carbon(db,projection,start,end)
    if _aggregate_rows is None:
        row=db.execute(plan["totals"]).mappings().one();used_ids=set(db.scalars(plan["used"]))
    else:
        row=next(row for row in _aggregate_rows if row["tag"]=="carbon")
        used_ids={row["id"] for row in _aggregate_rows if row["tag"]=="carbon_factor"}
    total,uncovered=row["amount"],int(row["unresolved"] or 0)
    used={record.id:record for record in plan["records"] if record.id in used_ids}
    eligible=bool(energy["interval_count"]) and not uncovered
    if uncovered:
        energy["quality"]="unavailable";energy["warnings"].append(f"{uncovered} intervals have missing or ambiguous carbon configuration")
    single=next(iter(used.values())) if len(used)==1 else None
    energy.update(kg_co2e=round(float(total),6) if eligible else None,factor_id=single.id if single else None,factor=record_dict(single) if single else None,
        factors_used=list(used),method="location_based",reduction_claim=False)
    return energy


def balance(db, **scope):
    devices = scoped_devices(db, scope.get("campus_id"), scope.get("building_id"))
    circuits = {c.id: c for c in db.scalars(select(Circuit)).all()}
    main = [d for d in devices if d.kind == "meter" and d.circuit_id and not circuits[d.circuit_id].parent_id]
    children = [d for d in devices if d.circuit_id and circuits[d.circuit_id].parent_id in {m.circuit_id for m in main}]
    if not main or not children:
        return {"parent_kwh": None, "children_kwh": None, "residual_kwh": None, "quality": "unavailable", "warnings": ["Comparable parent/child meter boundaries are absent"]}
    parent = compute_energy(db, device_ids=[d.id for d in main], **scope)
    child = compute_energy(db, device_ids=[d.id for d in children], **scope)
    a, b = parent["known_kwh"], child["known_kwh"]
    return {"parent_kwh": a, "children_kwh": b, "residual_kwh": round(a-b, 6) if a is not None and b is not None else None,
        "quality": "partial" if a is not None and b is not None else "unknown", "warnings": ["Residual includes uninstrumented loads and boundary/coverage mismatch; not a verified electrical loss", "Parent and child totals are compared, never summed"]}
