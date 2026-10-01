from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import pytest
import os
from uuid import uuid4
from sqlalchemy import text
from pydantic import ValidationError
from app.db import Base, make_engine, make_session_factory
from app.models import Campus, Device, Tariff
from app.registry import add_binding
from app.schemas import TelemetryIn, TariffIn
from app.telemetry import ingest_sample
from app.accounting import apply_accounting
from app.pricing import utc_price_windows
from app.common import DomainError

UTC=timezone.utc


@pytest.fixture
def pricing_db():
    url=os.environ.get("PRICING_TEST_DATABASE_URL","sqlite:///:memory:")
    engine=make_engine(url)
    schema=None
    if engine.dialect.name=="postgresql":
        schema="price_test_"+uuid4().hex
        with engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine=engine.execution_options(schema_translate_map={None:schema})
    Base.metadata.create_all(engine)
    with make_session_factory(engine)() as db:
        db.add(Campus(id="price-campus",name="Synthetic price fixture",source="test"));db.flush()
        device=Device(id="PRICE-METER",name="Synthetic counter",campus_id="price-campus",kind="meter",source_mode="SIMULATED",capabilities=["metering"])
        db.add(device);db.flush();add_binding(db,device,"test","Synthetic measurement boundary",datetime(2020,1,1,tzinfo=UTC));db.commit()
        yield db,device
    if schema:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    engine.dispose()


def tariff(db,ident="test-tariff",rate=1.0,bands=None,zone="Asia/Shanghai",currency="CNY",start=None,end=None):
    row=Tariff(id=ident,name="Synthetic time-of-use tariff, not institutional prices",currency=currency,rate_per_kwh=rate,timezone=zone,bands=bands or [],
        valid_from=start or datetime(2020,1,1,tzinfo=UTC),valid_to=end or datetime(2030,1,1,tzinfo=UTC),source_url="https://example.invalid/synthetic-tariff",source_mode="SIMULATED",version=1)
    db.add(row);db.commit();return row


def interval(db,device,start,end,kwh=1.0):
    for seq,at,wh in [(1,start,1000.0),(2,end,1000.0+kwh*1000)]:
        sample=TelemetryIn(device_id=device.id,boot_epoch="c"*32,sample_seq=str(seq),observed_at=at,time_source="simulated",time_uncertainty_ms=0.0,
            active_power_w=1000.0,voltage_v=230.0,current_a=4.5,energy_import_wh=wh,energy_export_wh=0.0,valid=True,calibrated=True,energy_status="known",source_mode="SIMULATED",source_version="synthetic-tou-test")
        ingest_sample(db,sample,received_at=at)
    db.commit()


def local(hour,minute,date=1):
    return datetime(2026,10,date,hour,minute,tzinfo=ZoneInfo("Asia/Shanghai")).astimezone(UTC)


def test_flat_price_is_constant_daily_function(pricing_db):
    db,device=pricing_db;tariff(db,rate=.82)
    start,end=local(7,50),local(8,10);interval(db,device,start,end,kwh=2)
    result=apply_accounting(db,"cost",start=start,end=end)
    assert result["amount"]==1.64 and result["pricing_mode"]=="strict"
    assert result["boundary_estimated_intervals"]==0 and result["settlement_bill"] is False
    assert result["charge_type"]=="configured_energy_charge_estimate"


def test_rate_boundary_is_unresolved_by_default_and_explicit_estimate_conserves_energy(pricing_db):
    db,device=pricing_db;tariff(db,bands=[{"start_minute":480,"end_minute":1320,"rate_per_kwh":2.0}])
    start,end=local(7,50),local(8,10);interval(db,device,start,end)
    strict=apply_accounting(db,"cost",start=start,end=end)
    assert strict["amount"] is None and strict["quality"]=="unavailable" and strict["boundary_unresolved_intervals"]==1
    estimated=apply_accounting(db,"cost",start=start,end=end,allocation_mode="proportional_estimate")
    assert estimated["known_kwh"]==strict["known_kwh"]==1.0
    assert estimated["amount"]==1.5 and estimated["quality"]=="estimated" and estimated["boundary_estimated_intervals"]==1
    assert estimated["pricing_coverage_ratio"]==1


def test_local_midnight_is_split_without_changing_kwh(pricing_db):
    db,device=pricing_db;tariff(db,bands=[{"start_minute":0,"end_minute":60,"rate_per_kwh":2.0}])
    start,end=local(23,50),local(0,10,date=2);interval(db,device,start,end)
    result=apply_accounting(db,"cost",start=start,end=end,allocation_mode="proportional_estimate")
    assert result["amount"]==1.5 and result["known_kwh"]==1.0 and result["boundary_estimated_intervals"]==1


@pytest.mark.parametrize("case",["missing","overlapping","mixed_currency"])
def test_missing_overlap_and_currency_never_become_a_settlement_total(pricing_db,case):
    db,device=pricing_db;start,end=local(7,50),local(8,10);middle=local(8,0)
    if case=="missing":
        tariff(db,end=middle-timedelta(minutes=5));tariff(db,"next",start=middle+timedelta(minutes=5))
    elif case=="overlapping":
        tariff(db);tariff(db,"overlapping")
    else:
        tariff(db,end=middle);tariff(db,"next",start=middle,currency="USD")
    interval(db,device,start,end)
    result=apply_accounting(db,"cost",start=start,end=end,allocation_mode="proportional_estimate")
    assert result["amount"] is None and result["quality"]=="unavailable" and result["settlement_bill"] is False


def test_iana_daylight_saving_with_unambiguous_switches_is_disjoint_and_complete(pricing_db):
    db,_=pricing_db
    row=tariff(db,zone="America/New_York",bands=[{"start_minute":480,"end_minute":1320,"rate_per_kwh":2.0}])
    start=datetime(2026,3,8,0,tzinfo=ZoneInfo(row.timezone)).astimezone(UTC)
    end=datetime(2026,3,9,0,tzinfo=ZoneInfo(row.timezone)).astimezone(UTC)
    windows=utc_price_windows(row,start,end)
    assert sum((b-a).total_seconds() for a,b,_ in windows)==23*3600
    assert all(a[1]==b[0] for a,b in zip(windows,windows[1:]))
    assert windows[0][0]==start and windows[-1][1]==end


@pytest.mark.parametrize("date,minute,kind",[(datetime(2026,3,8,tzinfo=UTC),150,"nonexistent"),(datetime(2026,11,1,tzinfo=UTC),90,"ambiguous")])
def test_ambiguous_or_nonexistent_price_switch_is_explicitly_rejected(pricing_db,date,minute,kind):
    db,_=pricing_db
    row=tariff(db,zone="America/New_York",bands=[{"start_minute":minute,"end_minute":240,"rate_per_kwh":2.0}])
    with pytest.raises(DomainError) as error:
        utc_price_windows(row,date,date+timedelta(days=1))
    assert error.value.code=="tariff_wall_time_unresolved" and error.value.details["kind"]==kind


def test_overlapping_local_bands_and_unknown_timezone_are_rejected():
    body={"id":"synthetic-tariff","name":"Synthetic","rate_per_kwh":1.0,"valid_from":"2026-01-01T00:00:00Z","valid_to":"2027-01-01T00:00:00Z","source_url":"https://example.invalid/test","source_mode":"SIMULATED","version":1}
    with pytest.raises(ValidationError):
        TariffIn(**body,bands=[{"start_minute":0,"end_minute":120,"rate_per_kwh":.2},{"start_minute":60,"end_minute":180,"rate_per_kwh":.3}])
    with pytest.raises(ValidationError):
        TariffIn(**body,timezone="Not/A_Real_Zone")


@pytest.mark.parametrize('overlapping_factors',[False,True])
def test_overview_shares_one_interval_query_and_preserves_factor_ambiguity(pricing_db,monkeypatch,overlapping_factors):
    import json
    from sqlalchemy import event
    from app.models import CarbonFactor
    from app.config import Settings
    from app import analytics
    db,device=pricing_db
    start,end=local(7,50),local(8,10)
    interval(db,device,start,end);tariff(db,rate=.82)
    for index in range(2 if overlapping_factors else 1):
        db.add(CarbonFactor(id=f'factor-{index}',name='Synthetic factor',region='Test',year=2026,kg_co2e_per_kwh=.5,
            valid_from=datetime(2020,1,1,tzinfo=UTC),valid_to=datetime(2030,1,1,tzinfo=UTC),
            source_url='https://example.invalid/synthetic',source_mode='SIMULATED',version=index+1))
    db.commit()
    monkeypatch.setattr(analytics,'utcnow',lambda:end)
    statements=[]
    def capture(connection,cursor,statement,parameters,context,executemany):
        if 'energy_pairs AS' in statement:
            statements.append(statement)
    event.listen(db.bind,'before_cursor_execute',capture)
    try:
        result=analytics.overview(db,Settings(env='test'))
    finally:
        event.remove(db.bind,'before_cursor_execute',capture)
    json.dumps(result,allow_nan=False)
    assert len(statements)==1
    assert result['energy']['known_kwh']==1.0 and result['cost']['amount']==.82
    assert result['carbon']['kg_co2e']==(None if overlapping_factors else .5)
    assert result['carbon']['quality']==('unavailable' if overlapping_factors else 'partial')


def test_standalone_hourly_buckets_use_utc_even_if_database_session_does_not(pricing_db):
    from app.accounting import energy_projection
    from app.energy_sql import hourly_totals
    db,device=pricing_db
    start,end=local(7,50),local(8,10)
    interval(db,device,start,end)
    if db.bind.dialect.name=='postgresql':
        db.execute(text("SET LOCAL TIME ZONE 'Asia/Kathmandu'"))
    prepared=energy_projection(db,start=start,end=end)
    rows=hourly_totals(db,prepared[3])
    assert len(rows)==1 and rows[0]['timestamp']=='2026-10-01T00:00:00Z'
    assert rows[0]['known_kwh']==1.0
