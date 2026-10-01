from collections import defaultdict
import math
from datetime import timedelta
from sqlalchemy import select, func
from .accounting import compute_energy, apply_accounting, selected_devices, energy_projection, prepare_carbon, carbon_queries
from .energy_sql import aggregate_bundle
from .db import utcnow, iso
from .models import Device, Telemetry, Building, Space, Alarm
from .common import record_dict
from .registry import device_status, freshness_limits


def overview(db, settings, campus_id=None, building_id=None):
    now = utcnow()
    scope = {"campus_id": campus_id, "building_id": building_id, "end": now}
    prepared = energy_projection(db, **scope)
    from .pricing import prepare_price,pricing_queries
    carbon_plan=prepare_carbon(db,prepared[3],prepared[0],prepared[1])
    price_plan=prepare_price(db,prepared[3],prepared[0],prepared[1])
    aggregates = aggregate_bundle(db, prepared[3], overview=True,extra_queries=carbon_queries(carbon_plan)+pricing_queries(price_plan))
    energy = compute_energy(db, _prepared=prepared, _totals=aggregates["totals"], **scope)
    grouped_energy, trend = aggregates["buildings"], aggregates["trend"]
    carbon = apply_accounting(db, "carbon", _prepared=prepared, _energy=energy, _plan=carbon_plan, _aggregate_rows=aggregates["extra"], **scope)
    cost = apply_accounting(db, "cost", _prepared=prepared, _energy=energy, _plan=price_plan, _aggregate_rows=aggregates["extra"], **scope)
    bq, sq, dq, aq = select(Building), select(Space), select(Device), select(Alarm).where(Alarm.status != "resolved")
    if campus_id:
        bq, sq, dq, aq = bq.where(Building.campus_id == campus_id), sq.where(Space.campus_id == campus_id), dq.where(Device.campus_id == campus_id), aq.where(Alarm.campus_id == campus_id)
    if building_id:
        bq, sq, dq, aq = bq.where(Building.id == building_id), sq.where(Space.building_id == building_id), dq.where(Device.building_id == building_id), aq.where(Alarm.building_id == building_id)
    buildings, devices, alarms = list(db.scalars(bq)), list(db.scalars(dq)), list(db.scalars(aq))
    limits = freshness_limits(db, settings)
    statuses = [device_status(d, settings, now, limits) for d in devices]
    samples = {s.device_id: s for s in db.scalars(select(Telemetry).where(Telemetry.id.in_([d.latest_telemetry_id for d in devices if d.latest_telemetry_id])))}
    selected = {d.id:d for d in selected_devices(db, campus_id, building_id, start=now, end=now)}
    power_by_building, energy_by_building = defaultdict(float), defaultdict(float)
    power_sources_by_building=defaultdict(set)
    fresh_samples = []
    for d in devices:
        sample = samples.get(d.id)
        if (d.id in selected and sample and sample.quality == "good" and sample.active_power_w is not None
                and math.isfinite(sample.active_power_w) and -5 <= (now-sample.observed_at).total_seconds() <= limits[0]
                and sample.binding_id in selected[d.id].eligible_binding_ids and sample.campus_id == d.campus_id
                and sample.building_id == d.building_id and sample.circuit_id == d.circuit_id and sample.source_mode == d.source_mode):
            fresh_samples.append(sample)
            power_by_building[d.building_id] += sample.active_power_w/1000
            power_sources_by_building[d.building_id].add(sample.source_mode)
    for key, values in grouped_energy.items():
        energy_by_building[key] = values["known_kwh"]
    def source_mode(modes):
        modes=set(modes)-{"UNKNOWN",None}
        return "MIXED" if "MIXED" in modes or len(modes)>1 else next(iter(modes)) if modes else "UNKNOWN"
    power_source=source_mode(sample.source_mode for sample in fresh_samples)
    overview_source=source_mode([energy["source_mode"],power_source])
    latest = max((s.observed_at for s in samples.values()), default=None)
    building_rows = []
    for building in buildings:
        building_rows.append({"id": building.id, "name": building.name, "active_kw": round(power_by_building[building.id], 4) if building.id in power_by_building else None,
            "known_kwh": round(energy_by_building[building.id], 4) if building.id in energy_by_building else None,
            "device_count": sum(d.building_id == building.id for d in devices), "alarm_count": sum(a.building_id == building.id for a in alarms),
            "quality": "good" if building.id in power_by_building else "unknown",
            "power_source_mode":source_mode(power_sources_by_building[building.id])})
    return {"scope": {"campus_id": campus_id, "building_id": building_id}, "source_mode": overview_source, "generated_at": iso(now),
        "freshness": {"status": "fresh" if latest and (now-latest).total_seconds() <= limits[0] else "stale" if latest else "unknown", "latest_sample_at": iso(latest), "stale_after_seconds": limits[0]},
        "counts": {"buildings": len(buildings), "spaces": db.scalar(select(func.count()).select_from(sq.subquery())), "devices": len(devices),
            "online_devices": statuses.count("online"), "stale_devices": statuses.count("stale"), "offline_devices": statuses.count("offline"), "unknown_devices": statuses.count("unknown"), "active_alarms": len(alarms)},
        "energy": energy, "power": {"active_kw": round(sum(s.active_power_w for s in fresh_samples)/1000, 4) if fresh_samples else None,
            "quality": "good" if len(fresh_samples) == len(selected) and selected else "partial" if fresh_samples else "unknown", "meter_count": len(fresh_samples), "source_mode":power_source},
        "carbon": {k: carbon[k] for k in ("kg_co2e", "factor_id", "quality", "reduction_claim")}, "cost": {k: cost[k] for k in ("amount", "currency", "tariff_id", "quality")},
        "trend": trend,
        "buildings": sorted(building_rows, key=lambda x: -(x["known_kwh"] or 0)), "alarms": [record_dict(a) for a in sorted(alarms, key=lambda a: a.created_at, reverse=True)[:10]],
        "provenance": {"spatial": "Pinned njupt-map/njupt-search reference identities", "telemetry": "Persisted interval ledger; source labels per device", "physical_control_enabled": settings.physical_dispatch_enabled, "measured_savings_claim": False}}
