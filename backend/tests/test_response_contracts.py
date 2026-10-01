"""Public DTO/schema parity using actual HTTP and persisted synthetic observations."""
import json
from datetime import timedelta
import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError
from app.db import utcnow
from app.models import Device, Telemetry
from app.responses import Envelope, CommandResponse, TelemetryResponse, DeviceResponse, ForecastResponse
from app.control import advance_commands


def assert_openapi_response(application, path, method, status, payload):
    schema=application.openapi()
    response=schema['paths'][path][method]['responses'][str(status)]['content']['application/json']['schema']
    Draft202012Validator({**response,'components':schema['components']}).validate(payload)


@pytest.mark.parametrize('path,template',[
    ('/auth/me','/auth/me'),('/devices','/devices'),('/devices/SIM-A','/devices/{device_id}'),
    ('/telemetry','/telemetry'),('/devices/SIM-A/telemetry','/devices/{device_id}/telemetry'),
    ('/energy/summary','/energy/summary'),('/energy/breakdown','/energy/breakdown'),('/energy/balance','/energy/balance'),
    ('/carbon/summary','/carbon/summary'),('/cost/summary','/cost/summary'),('/forecasts','/forecasts'),
    ('/devices/SIM-A/control-eligibility','/devices/{device_id}/control-eligibility')])
def test_real_endpoint_responses_match_published_contract(app,admin,path,template):
    application,_=app;client,_=admin
    response=client.get('/api/v1'+path)
    assert response.status_code==200,response.text
    assert_openapi_response(application,'/api/v1'+template,'get',200,response.json())
    json.dumps(response.json(),allow_nan=False)


def test_exact_uint64_and_persisted_command_lifecycle_match_response_contract(app,admin):
    application,_=app;client,headers=admin
    with application.state.session_factory() as db:
        device=db.get(Device,'SIM-A');device.next_command_sequence=2**64-1
        sample=db.get(Telemetry,device.latest_telemetry_id);sample.sample_seq=str(2**64-2)
        db.commit()
    response=client.post('/api/v1/commands',headers={**headers,'Idempotency-Key':'response-contract-max-sequence'},json={'device_id':'SIM-A','action':'hold','reason':'Synthetic contract evidence'})
    assert response.status_code==201,response.text
    body=response.json();ident=body['data']['id']
    assert body['data']['sequence']=='18446744073709551615'
    assert_openapi_response(application,'/api/v1/commands','post',201,body)
    for step in (1,2,3):
        with application.state.session_factory() as db:
            advance_commands(db,utcnow()+timedelta(seconds=step),application.state.settings);db.commit()
    detail=client.get('/api/v1/commands/'+ident)
    assert detail.status_code==200,detail.text
    assert detail.json()['data']['status']=='verified'
    assert_openapi_response(application,'/api/v1/commands/{command_id}','get',200,detail.json())
    records=client.get('/api/v1/telemetry').json()
    assert_openapi_response(application,'/api/v1/telemetry','get',200,records)
    assert all(isinstance(row['sample_seq'],str) for row in records['data'])
    assert not {'payload_hash','raw_payload'} & records['data'][0].keys()


@pytest.mark.parametrize('value',[1,True,'01','-1','1.0','18446744073709551616'])
def test_uint64_response_contract_rejects_lossy_or_noncanonical_counters(app,admin,value):
    client,_=admin
    sample=client.get('/api/v1/devices/SIM-A').json()['data']['latest']
    with pytest.raises(ValidationError):
        TelemetryResponse.model_validate({**sample,'sample_seq':value})


def test_public_schema_does_not_contain_internal_storage_fields(app):
    application,_=app
    schemas=application.openapi()['components']['schemas']
    prohibited={'password_hash','token_hash','payload_hash','raw_payload','next_command_sequence','latest_telemetry_id','last_control_at'}
    for name in ('UserResponse','DeviceResponse','TelemetryResponse','CommandResponse'):
        assert not prohibited & schemas[name]['properties'].keys()
        assert schemas[name]['additionalProperties'] is False
    assert schemas['CommandResponse']['properties']['sequence']['type']=='string'
    assert schemas['TelemetryResponse']['properties']['sample_seq']['type']=='string'


def test_accidental_internal_field_is_fail_closed_without_log_or_http_leak(app,admin,monkeypatch,caplog):
    from app import routes
    application,_=app;client,_=admin
    original=routes.device_dict
    def polluted(*args,**kwargs):
        return {**original(*args,**kwargs),'password_hash':'SYNTHETIC_SECRET_MUST_NOT_LEAK'}
    monkeypatch.setattr(routes,'device_dict',polluted)
    response=client.get('/api/v1/devices/SIM-A')
    assert response.status_code==500
    assert response.json()['error']['code']=='response_contract_violation'
    assert 'SYNTHETIC_SECRET_MUST_NOT_LEAK' not in response.text+caplog.text
