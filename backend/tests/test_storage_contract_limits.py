import pytest
from pydantic import ValidationError
from app.schemas import TariffIn,TelemetryIn


def test_accounting_identity_and_version_fit_postgresql_storage():
    body={'id':'example','name':'Synthetic','rate_per_kwh':.5,'valid_from':'2026-01-01T00:00:00Z','valid_to':'2027-01-01T00:00:00Z',
        'source_url':'https://example.invalid/fixture','source_mode':'SIMULATED','version':1}
    with pytest.raises(ValidationError):TariffIn(**(body|{'id':'x'*101}))
    with pytest.raises(ValidationError):TariffIn(**(body|{'version':2**31}))


def test_uncertain_interval_counter_cannot_overflow_the_sql_projection():
    body={'device_id':'fixture','boot_epoch':'a'*32,'sample_seq':'1','observed_at':'2026-01-01T00:00:00Z','time_source':'simulated',
        'valid':False,'calibrated':False,'source_mode':'SIMULATED','source_version':'test','energy_uncertain_intervals':2**32}
    with pytest.raises(ValidationError):TelemetryIn(**body)


@pytest.mark.parametrize('identifier',['.','..',' . ',' .. '])
def test_shared_resource_ids_reserve_normalized_url_dot_segments(identifier):
    from app.schemas import BindingIn,TariffIn
    with pytest.raises(ValidationError):
        BindingIn(campus_id=identifier,reason='Addressability regression')
    body={'id':identifier,'name':'Synthetic','rate_per_kwh':.5,'valid_from':'2026-01-01T00:00:00Z','valid_to':'2027-01-01T00:00:00Z',
        'source_url':'https://example.invalid/fixture','source_mode':'SIMULATED','version':1}
    with pytest.raises(ValidationError):
        TariffIn(**body)


@pytest.mark.parametrize('identifier',['.a','a.','a..','...','v1.2','campus:building-1'])
def test_shared_resource_ids_keep_safe_dotted_and_namespaced_values(identifier):
    from app.schemas import BindingIn
    assert BindingIn(campus_id=identifier,reason='Exact identity').campus_id==identifier


def test_openapi_resource_id_constraint_matches_the_reserved_values():
    from app.schemas import DeviceIn,CircuitIn,TariffIn
    for model in (DeviceIn,CircuitIn,TariffIn):
        assert model.model_json_schema()['properties']['id']['not']=={'enum':['.','..']}
