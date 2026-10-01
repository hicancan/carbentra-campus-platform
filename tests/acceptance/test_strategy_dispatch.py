"""Shadow plan freeze, explicit approval/dispatch and all-or-nothing rechecks."""
from types import SimpleNamespace
from datetime import timedelta
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app.config import Settings
from app.db import utcnow
from app.main import create_app
from app.models import Campus,Building,Device,Strategy,Circuit
from app.schemas import TelemetryIn
from app.telemetry import ingest_sample

P='/api/v1'
def value(response,status=200):
    assert response.status_code==status,response.text
    return response.json()['data']

@pytest.fixture
def plan(tmp_path):
    application=create_app(Settings(env='test',database_url=f'sqlite:///{tmp_path}/strategy.sqlite3',dev_auth=True,seed_demo=False,worker_enabled=False))
    with TestClient(application,raise_server_exceptions=False) as client:
        auth=value(client.post(P+'/auth/login',json={'username':'admin','password':'development-only'}));headers={'X-CSRF-Token':auth['csrf_token']}
        with application.state.session_factory() as db:
            db.add(Campus(id='QA-PLAN-CAMPUS',name='QA plan campus',source='acceptance'));db.flush()
            db.add(Building(id='QA-PLAN-BUILDING',campus_id='QA-PLAN-CAMPUS',name='QA plan building',source='acceptance'));db.flush()
            db.add(Circuit(id='QA-PLAN-MAIN',campus_id='QA-PLAN-CAMPUS',building_id='QA-PLAN-BUILDING',name='QA plan main',kind='main'));db.flush()
            db.add(Circuit(id='QA-PLAN-BRANCH',campus_id='QA-PLAN-CAMPUS',building_id='QA-PLAN-BUILDING',name='QA unmetered intermediate',kind='branch',parent_id='QA-PLAN-MAIN'));db.flush()
            for i in range(1,4):db.add(Circuit(id=f'QA-PLAN-LOAD-{i}',campus_id='QA-PLAN-CAMPUS',building_id='QA-PLAN-BUILDING',name='QA plan load',kind='load',parent_id='QA-PLAN-BRANCH'))
            db.commit()
        for index in range(4):
            meter=index==0;ident=f'QA-PLAN-{index}'
            value(client.post(P+'/devices',headers=headers,json={'id':ident,'name':ident,'campus_id':'QA-PLAN-CAMPUS','building_id':'QA-PLAN-BUILDING','circuit_id':'QA-PLAN-MAIN' if meter else f'QA-PLAN-LOAD-{index}','kind':'meter' if meter else 'smart_plug','source_mode':'SIMULATED','critical':meter,'allow_control':not meter,'capabilities':['metering'] if meter else ['metering','shed','restore','hold']}),201)
            if not meter:value(client.patch(P+'/devices/'+ident,headers=headers,json={'commissioned':True}))
            with application.state.session_factory() as db:
                sample=TelemetryIn(device_id=ident,boot_epoch='a'*32,sample_seq='1',observed_at=utcnow(),time_source='simulated',time_uncertainty_ms=0.0,active_power_w=1000.0 if meter else 200.0,voltage_v=230.0,current_a=1.0,energy_import_wh=1000.0,energy_export_wh=0.0,desired_on=True,output_present=True,fault_latched=False,valid=True,calibrated=True,energy_status='known',source_mode='SIMULATED',source_version='qa-plan-v1')
                ingest_sample(db,sample);db.commit()
        strategy=value(client.post(P+'/strategies',headers=headers,json={'name':'QA frozen plan','campus_id':'QA-PLAN-CAMPUS','target_reduction_pct':30.0,'max_devices':3}),201)
        yield SimpleNamespace(application=application,client=client,headers=headers,strategy=strategy)


def evaluate(plan):return value(plan.client.post(P+'/strategies/'+plan.strategy['id']+'/evaluate',headers=plan.headers,json={}))
def approve(plan):return value(plan.client.post(P+'/strategies/'+plan.strategy['id']+'/approve',headers=plan.headers,json={'note':'QA explicit shadow approval'}))
def dispatch(plan,evaluation,key=None):return plan.client.post(P+'/strategies/'+plan.strategy['id']+'/dispatch',headers=plan.headers|{'Idempotency-Key':key or 'qa-plan-'+uuid4().hex},json={'evaluation_id':evaluation['id'],'reason':'QA explicit simulated dispatch'})
def commands(plan):return value(plan.client.get(P+'/commands'))


def test_evaluation_and_approval_do_not_dispatch_and_exact_plan_is_frozen(plan):
    first=evaluate(plan)
    assert first['dispatch_performed'] is False and len(first['candidate_device_ids'])==2
    assert commands(plan)==[]
    assert dispatch(plan,first).status_code==409
    approve(plan);assert commands(plan)==[]
    second=evaluate(plan)
    assert second['id']!=first['id']
    assert dispatch(plan,first).status_code==409
    assert dispatch(plan,second).status_code==409
    approve(plan)
    key='qa-plan-'+uuid4().hex
    sent=value(dispatch(plan,second,key),201)
    again=value(dispatch(plan,second,key),201)
    assert [x['id'] for x in sent['commands']]==[x['id'] for x in again['commands']]
    assert len(commands(plan))==2 and sent['physical_dispatch'] is False


def test_dispatch_rechecks_every_candidate_and_rolls_back_entire_batch(plan):
    frozen=evaluate(plan);approve(plan)
    victim=frozen['candidate_device_ids'][1]
    value(plan.client.patch(P+'/devices/'+victim,headers=plan.headers,json={'allow_control':False,'critical':True}))
    response=dispatch(plan,frozen)
    assert response.status_code==409,response.text
    assert commands(plan)==[],'Earlier command escaped despite later candidate safety failure'


def test_expired_evaluation_requires_fresh_approval(plan):
    frozen=evaluate(plan);approve(plan)
    with plan.application.state.session_factory() as db:
        row=db.get(Strategy,plan.strategy['id'])
        content=dict(row.latest_evaluation)
        content['created_at']=(utcnow()-timedelta(minutes=6)).isoformat()
        row.latest_evaluation=content;db.commit()
    response=dispatch(plan,frozen)
    assert response.status_code==409 and response.json()['error']['code']=='evaluation_expired'
    assert commands(plan)==[]


def test_reparenting_unmetered_ancestor_cannot_rewrite_descendant_history(plan):
    value(plan.client.post(P+'/circuits',headers=plan.headers,json={'id':'QA-PLAN-OTHER','campus_id':'QA-PLAN-CAMPUS','building_id':'QA-PLAN-BUILDING','name':'QA another boundary','kind':'main','source_mode':'SIMULATED'}),201)
    response=plan.client.patch(P+'/circuits/QA-PLAN-BRANCH',headers=plan.headers,json={'parent_id':'QA-PLAN-OTHER'})
    assert response.status_code==409,'Ancestor reparenting rewrites existing descendant measurement history: '+response.text


def test_virtual_transport_activation_rejects_non_wire_device_identity(plan):
    value(plan.client.post(P+'/devices',headers=plan.headers,json={'id':'QA:NONWIRE:DEVICE','name':'QA namespaced logical device','campus_id':'QA-PLAN-CAMPUS','source_mode':'SIMULATED','critical':False,'allow_control':False}),201)
    response=plan.client.patch(P+'/devices/QA:NONWIRE:DEVICE',headers=plan.headers,json={'dispatch_mode':'VIRTUAL','commissioned':True})
    assert response.status_code in {409,422},'Virtual transport accepted a device ID rejected by canonical MQTT wire schema: '+response.text
