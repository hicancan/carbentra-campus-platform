"""Resource-level authorization across lists, direct IDs, exports and user changes."""
from datetime import timedelta
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app.config import Settings
from app.db import utcnow
from app.main import create_app
from app.models import Campus, Building, Alarm
from app.schemas import TelemetryIn
from app.telemetry import ingest_sample

P='/api/v1'
PASSWORD='qa-local-fixture-password-000000'

def value(response,status=200):
    assert response.status_code==status,response.text
    return response.json()['data']


def signin(client,username='admin',password='development-only'):
    body=value(client.post(P+'/auth/login',json={'username':username,'password':password}))
    return {'X-CSRF-Token':body['csrf_token']}


@pytest.fixture(scope='module')
def scoped(tmp_path_factory):
    app=create_app(Settings(env='test',database_url=f"sqlite:///{tmp_path_factory.mktemp('scope')/'scope.sqlite3'}",dev_auth=True,seed_demo=False,worker_enabled=False))
    with TestClient(app,raise_server_exceptions=False) as admin:
        headers=signin(admin)
        with app.state.session_factory() as db:
            for suffix in ('A','B'):
                db.add(Campus(id='QA-SCOPE-'+suffix,name='QA campus '+suffix,source='acceptance'))
            db.flush()
            for suffix in ('A','B'):
                db.add(Building(id='QA-BUILDING-'+suffix,campus_id='QA-SCOPE-'+suffix,name='QA building '+suffix,source='acceptance'))
            db.commit()
        records={}
        for suffix in ('A','B'):
            campus='QA-SCOPE-'+suffix;device='QA-SCOPE-DEVICE-'+suffix
            value(admin.post(P+'/devices',headers=headers,json={'id':device,'name':'QA scope device '+suffix,'campus_id':campus,'building_id':'QA-BUILDING-'+suffix,'source_mode':'SIMULATED','critical':False,'allow_control':True,'capabilities':['metering','shed','restore','hold']}),201)
            value(admin.patch(P+'/devices/'+device,headers=headers,json={'commissioned':True}))
            with app.state.session_factory() as db:
                now=utcnow()
                sample=TelemetryIn(device_id=device,boot_epoch='a'*32,sample_seq='1',observed_at=now,time_source='simulated',time_uncertainty_ms=0.0,active_power_w=1000.0,voltage_v=230.0,current_a=4.5,energy_import_wh=1000.0,energy_export_wh=0.0,desired_on=True,output_present=True,fault_latched=False,valid=True,calibrated=True,energy_status='known',source_mode='SIMULATED',source_version='qa-scope-v1')
                ingest_sample(db,sample)
                db.add(Alarm(id='QA-ALARM-'+suffix,device_id=device,campus_id=campus,building_id='QA-BUILDING-'+suffix,type='fixture',severity='warning',title='QA scoped alarm',description='Synthetic scope fixture',source_mode='SIMULATED'))
                db.commit()
            report=value(admin.post(P+'/reports',headers=headers,json={'name':'QA scope report '+suffix,'type':'operations','campus_id':campus}),201)
            strategy=value(admin.post(P+'/strategies',headers=headers,json={'name':'QA scope strategy '+suffix,'campus_id':campus,'target_reduction_pct':1.0}),201)
            command=value(admin.post(P+'/commands',headers=headers|{'Idempotency-Key':'qa-scope-'+uuid4().hex},json={'device_id':device,'action':'hold','reason':'QA scope command','expires_in_seconds':60}),201)
            records[suffix]={'campus':campus,'building':'QA-BUILDING-'+suffix,'device':device,'alarm':'QA-ALARM-'+suffix,'report':report['id'],'strategy':strategy['id'],'command':command['id']}
        yield app,admin,headers,records


def new_user(scoped,role='viewer',campus_ids=('QA-SCOPE-A',)):
    app,admin,headers,_=scoped
    username='qa-user-'+uuid4().hex[:10]
    row=value(admin.post(P+'/users',headers=headers,json={'username':username,'display_name':'Local scope QA','role':role,'campus_ids':list(campus_ids) if campus_ids is not None else None,'password':PASSWORD}),201)
    client=TestClient(app,raise_server_exceptions=False)
    auth=signin(client,username,PASSWORD)
    return row,client,auth


def test_resource_lists_and_direct_ids_are_scoped(scoped):
    _,client,_=new_user(scoped)
    records=scoped[3];b=records['B']
    try:
        assert [x['id'] for x in value(client.get(P+'/campuses'))]==['QA-SCOPE-A']
        assert [x['id'] for x in value(client.get(P+'/buildings'))]==['QA-BUILDING-A']
        assert [x['id'] for x in value(client.get(P+'/devices'))]==['QA-SCOPE-DEVICE-A']
        for route in ('buildings/'+b['building'],'devices/'+b['device'],'devices/'+b['device']+'/telemetry','alarms/'+b['alarm'],'commands/'+b['command'],'reports/'+b['report'],'reports/'+b['report']+'/export?format=csv'):
            response=client.get(P+'/'+route)
            assert response.status_code==404,(route,response.text)
        assert value(client.get(P+'/telemetry',params={'device_id':b['device']}))==[]
        assert client.get(P+'/energy/summary',params={'device_ids':b['device']}).status_code==404
        assert value(client.get(P+'/topology',params={'campus_id':b['campus']}))=={'circuits':[],'devices':[]}
        assert all(x['campus_id']=='QA-SCOPE-A' for x in value(client.get(P+'/commands')))
        assert all(x['campus_id']=='QA-SCOPE-A' for x in value(client.get(P+'/alarms')))
        assert all(x['campus_id']=='QA-SCOPE-A' for x in value(client.get(P+'/strategies')))
        assert all(x['campus_id']=='QA-SCOPE-A' for x in value(client.get(P+'/reports')))
        assert value(client.get(P+'/audit',params={'entity_id':b['device']}))==[]
    finally:client.close()


def test_cross_scope_registry_and_strategy_writes_are_denied(scoped):
    _,client,headers=new_user(scoped,role='operator')
    b=scoped[3]['B'];a=scoped[3]['A']
    try:
        attempts=[client.patch(P+'/devices/'+b['device'],headers=headers,json={'name':'FORBIDDEN'}),client.put(P+'/devices/'+a['device']+'/binding',headers=headers,json={'campus_id':b['campus'],'building_id':b['building'],'reason':'QA forbidden cross-scope move'}),client.post(P+'/devices',headers=headers,json={'id':'QA-FORBIDDEN-'+uuid4().hex[:8],'name':'Forbidden foreign asset','campus_id':b['campus'],'source_mode':'SIMULATED'})]
        assert all(r.status_code in {403,404} for r in attempts),[(r.status_code,r.text) for r in attempts]
    finally:client.close()
    _,client,headers=new_user(scoped,role='analyst')
    try:
        response=client.post(P+'/strategies/'+b['strategy']+'/evaluate',headers=headers,json={})
        assert response.status_code==404,response.text
    finally:client.close()


def test_empty_scope_is_empty_not_global(scoped):
    _,client,_=new_user(scoped,campus_ids=())
    try:
        for route in ('campuses','buildings','devices','telemetry','commands','alarms','strategies','reports'):
            assert value(client.get(P+'/'+route))==[],route
        overview=value(client.get(P+'/overview'))
        assert overview['counts']['devices']==0 and overview['energy']['known_kwh'] is None
    finally:client.close()


def test_scope_update_revokes_existing_session(scoped):
    user,client,_=new_user(scoped)
    app,admin,headers,_=scoped
    try:
        value(admin.patch(P+'/users/'+user['id'],headers=headers,json={'campus_ids':[]}))
        assert client.get(P+'/auth/me').status_code==401
        signin(client,user['username'],PASSWORD)
        assert value(client.get(P+'/devices'))==[]
    finally:client.close()


def test_scoped_administrator_cannot_grant_global_or_other_campus(scoped):
    _,client,headers=new_user(scoped,role='admin')
    try:
        for scope in (None,['QA-SCOPE-B']):
            response=client.post(P+'/users',headers=headers,json={'username':'qa-escalation-'+uuid4().hex[:8],'display_name':'Denied fixture','role':'admin','campus_ids':scope,'password':PASSWORD})
            assert response.status_code==403,response.text
        listed=value(client.get(P+'/users'))
        assert all(u['campus_ids'] is not None and set(u['campus_ids']).issubset({'QA-SCOPE-A'}) for u in listed)
    finally:client.close()


def test_prior_global_report_cannot_bypass_narrowed_scope_by_creator(scoped):
    user,client,headers=new_user(scoped,role='analyst',campus_ids=None)
    _,admin,admin_headers,_=scoped
    try:
        report=value(client.post(P+'/reports',headers=headers,json={'name':'QA formerly global report','type':'operations'}),201)
        assert report['content']['counts']['buildings']==2
        value(admin.patch(P+'/users/'+user['id'],headers=admin_headers,json={'campus_ids':['QA-SCOPE-A']}))
        assert client.get(P+'/reports/'+report['id']).status_code==401
        signin(client,user['username'],PASSWORD)
        for suffix in ('','/export?format=json','/export?format=csv'):
            response=client.get(P+'/reports/'+report['id']+suffix)
            assert response.status_code==404,'Prior broader snapshot leaks after resource scope reduction: '+response.text
    finally:client.close()


@pytest.mark.parametrize('operation',['settings','carbon_factor','tariff'])
def test_campus_scoped_admin_cannot_change_global_configuration(scoped,operation):
    _,client,headers=new_user(scoped,role='admin')
    now=utcnow()
    try:
        if operation=='settings':
            response=client.patch(P+'/settings',headers=headers,json={'stale_after_seconds':30})
        elif operation=='carbon_factor':
            response=client.post(P+'/carbon/factors',headers=headers,json={'id':'qa-global-factor-'+uuid4().hex[:8],'name':'QA denied global factor','region':'QA','year':now.year,'kg_co2e_per_kwh':0.5,'valid_from':(now-timedelta(days=1)).isoformat(),'valid_to':(now+timedelta(days=1)).isoformat(),'source_url':'https://example.invalid/qa-fixture','source_mode':'SIMULATED','version':1})
        else:
            response=client.post(P+'/tariffs',headers=headers,json={'id':'qa-global-tariff-'+uuid4().hex[:8],'name':'QA denied global tariff','currency':'CNY','rate_per_kwh':0.8,'valid_from':(now-timedelta(days=1)).isoformat(),'valid_to':(now+timedelta(days=1)).isoformat(),'source_url':'https://example.invalid/qa-fixture','source_mode':'SIMULATED','version':1})
        assert response.status_code==403,f'{operation} applies globally but was changed by a campus-scoped administrator: {response.text}'
    finally:client.close()
