from datetime import timedelta
from copy import deepcopy
import pytest
from sqlalchemy import select, func
from app.db import utcnow
from app.models import (Space, Device, Binding, DeviceChannel, ChannelObservation, RoomMode, RoomPolicy,
    RoomAnomaly, HardwareEvent, ChannelAcknowledgement, Telemetry, User, Command)
from app.registry import create_device, add_binding
from app.classroom_schemas import ChannelIn, ChannelSample, ChannelValue, ModeIn, PolicyIn
from app.classrooms import register_channel, ingest_channel, snapshots, timeline, set_mode, distribution
from app.room_control import create_policy, evaluate_policy, dispatch_evaluation, evaluation_dict
from app.room_anomalies import evaluate_room, conditional_baseline
from app.schemas import TelemetryIn
from app.telemetry import ingest_sample
from app.common import DomainError

P = '/api/v1'

@pytest.fixture
def room_app(app):
    application, client = app
    now = utcnow()+timedelta(seconds=1)
    with application.state.session_factory() as db:
        for name in ('A', 'B'):
            db.add(Space(id=f'room-{name}', name=f'Room {name}', campus_id=name, building_id=f'building-{name}',
                kind='classroom_reference', source='test', confidence='synthetic'))
        db.flush()
        plug = db.get(Device, 'SIM-A');plug.space_id='room-A'
        add_binding(db, plug, 'test', 'Bind classroom fixture', now-timedelta(days=30))
        device = create_device(db, dict(id='SIM-SENSE', name='Presence fixture', campus_id='A', building_id='building-A', space_id='room-A',
            kind='presence', source_mode='SIMULATED', critical=False, allow_control=False, capabilities=['presence']), 'test')
        binding=db.scalar(select(Binding).where(Binding.device_id == device.id));binding.valid_from=now-timedelta(days=30)
        for body in (ChannelIn(id='channel-plug', device_id='SIM-A', channel_key='relay.1', name='Plug', kind='socket',
            capabilities=['relay.commanded','relay.feedback','power.active'], unit='W', freshness_seconds=120, controllable=True),
            ChannelIn(id='channel-presence', device_id='SIM-SENSE', channel_key='sensor.radar', name='Radar', kind='presence', capabilities=['presence.radar'], freshness_seconds=120)):
            register_channel(db, body, 'test')
        db.commit()
    application.state.settings.adapter_allowed_device_ids += ['SIM-SENSE']
    return application, client, now


def sample(db, channel, at, seq, value, valid=True, received_at=None, boot='test-epoch'):
    return ingest_channel(db, ChannelSample(channel_id=channel, boot_epoch=boot, sample_seq=str(seq), observed_at=at,
        time_source='simulated', time_uncertainty_ms=0., source_mode='SIMULATED', source_version='unit', valid=valid,
        value=ChannelValue(**value)), received_at=received_at or at)[0]


def evidence(db, at, seq, occupied=False, power=100.):
    sample(db,'channel-presence',at,seq,{'occupancy':'occupied' if occupied else 'vacant'})
    sample(db,'channel-plug',at,seq,{'output_present':power>0,'desired_on':power>0,'active_power_w':power,'fault_latched':False})


def test_half_open_freshness_unknown_not_vacant(room_app):
    app,_,now=room_app
    with app.state.session_factory() as db:
        room=db.get(Space,'room-A'); evidence(db,now,1)
        assert snapshots(db,[room],now-timedelta(seconds=1))[0]['occupancy']=='unknown'
        assert snapshots(db,[room],now)[0]['occupancy']=='vacant'
        assert snapshots(db,[room],now+timedelta(seconds=119))[0]['occupancy']=='vacant'
        end=snapshots(db,[room],now+timedelta(seconds=120))[0]
        assert end['occupancy']=='unknown' and end['sockets']=='unknown' and end['observed_power_w'] is None
        out=timeline(db,room,now-timedelta(seconds=60),now+timedelta(seconds=180))
        assert out['durations']['occupancy']=={'occupied':0.,'vacant':120.,'unknown':120.}
        assert sum(x['duration_seconds'] for x in out['intervals'])==240.


def test_invalid_observation_cuts_prior_interval(room_app):
    app,_,now=room_app
    with app.state.session_factory() as db:
        evidence(db,now,1)
        sample(db,'channel-presence',now+timedelta(seconds=30),2,{'occupancy':'vacant'},valid=False)
        out=timeline(db,db.get(Space,'room-A'),now,now+timedelta(seconds=120))
        assert out['durations']['occupancy']['vacant']==30.
        assert out['durations']['occupancy']['unknown']==90.


def test_late_received_event_uses_observed_time(room_app):
    app,_,now=room_app
    with app.state.session_factory() as db:
        sample(db,'channel-presence',now-timedelta(hours=1),1,{'occupancy':'occupied'},received_at=now)
        room=db.get(Space,'room-A')
        assert snapshots(db,[room],now)[0]['occupancy']=='unknown'
        assert snapshots(db,[room],now-timedelta(hours=1)+timedelta(seconds=20))[0]['occupancy']=='occupied'


def test_historical_binding_and_cross_scope_after_move(room_app):
    app,_,now=room_app
    with app.state.session_factory() as db:
        evidence(db,now,1)
        device=db.get(Device,'SIM-SENSE');device.campus_id='B';device.building_id='building-B';device.space_id='room-B'
        add_binding(db,device,'test','Move historical sensor',now+timedelta(seconds=30));db.commit()
    with app.state.session_factory() as db:
        db.info['campus_ids']=['A'];db.info['actor']='test'
        room=db.get(Space,'room-A')
        before=snapshots(db,[room],now+timedelta(seconds=20))[0]
        assert before['occupancy']=='vacant'
        after=snapshots(db,[room],now+timedelta(seconds=40))[0]
        assert after['occupancy']=='unknown'
        assert all(c['device_id']!='SIM-SENSE' for c in after['channels'])
        assert db.get(Space,'room-B') is None


def test_duplicate_samples_conflict_and_are_not_double_counted(room_app):
    app,_,now=room_app
    with app.state.session_factory() as db:
        evidence(db,now,1);evidence(db,now,1)
        assert db.scalar(select(func.count()).select_from(ChannelObservation))==2
        with pytest.raises(DomainError,match='different content'):
            sample(db,'channel-presence',now,1,{'occupancy':'occupied'})


def test_pir_silence_is_not_vacancy_and_any_presence_wins(room_app):
    app,_,now=room_app
    with app.state.session_factory() as db:
        register_channel(db,ChannelIn(id='channel-pir',device_id='SIM-SENSE',channel_key='sensor.pir',name='PIR',kind='presence',capabilities=['presence.pir']),'test')
        with pytest.raises(DomainError,match='PIR silence'):
            sample(db,'channel-pir',now,1,{'occupancy':'vacant'})
        evidence(db,now,1)
        sample(db,'channel-pir',now,2,{'occupancy':'unknown'})
        assert snapshots(db,[db.get(Space,'room-A')],now)[0]['occupancy']=='vacant'
        sample(db,'channel-pir',now+timedelta(seconds=1),3,{'occupancy':'occupied'})
        assert snapshots(db,[db.get(Space,'room-A')],now+timedelta(seconds=1))[0]['occupancy']=='occupied'


def test_all_required_radar_points_must_be_fresh(room_app):
    app,_,now=room_app
    with app.state.session_factory() as db:
        register_channel(db,ChannelIn(id='channel-radar2',device_id='SIM-SENSE',channel_key='sensor.radar2',name='Second radar',kind='presence',capabilities=['presence.radar']),'test')
        evidence(db,now,1)
        assert snapshots(db,[db.get(Space,'room-A')],now)[0]['occupancy']=='unknown'
        sample(db,'channel-radar2',now,1,{'occupancy':'vacant'})
        assert snapshots(db,[db.get(Space,'room-A')],now)[0]['occupancy']=='vacant'


def test_distribution_counts_every_room_and_duration(room_app):
    app,_,now=room_app
    with app.state.session_factory() as db:
        evidence(db,now,1);rooms=list(db.scalars(select(Space)))
        result=distribution(db,rooms,at=now,start=now,end=now+timedelta(seconds=180))
        assert result['total_rooms']==2
        assert sum(g['room_count'] for g in result['groups'])==2
        assert sum(sum(g['durations']['occupancy'].values()) for g in result['groups'])==360.
        assert sum(g['occupancy']['unknown'] for g in result['groups'])==1


def test_manual_hold_expires_back_to_automatic(room_app):
    app,_,now=room_app
    with app.state.session_factory() as db:
        room=db.get(Space,'room-A')
        set_mode(db,room,ModeIn(mode='automatic',reason='Enable bounded policy'),'test',now)
        set_mode(db,room,ModeIn(mode='manual',duration_seconds=60,reason='Operator override'),'test',now+timedelta(seconds=1))
        assert snapshots(db,[room],now+timedelta(seconds=20))[0]['mode']=='manual'
        assert snapshots(db,[room],now+timedelta(seconds=61))[0]['mode']=='automatic'


def _policy_fixture(db, now, mode='SIMULATED'):
    room=db.get(Space,'room-A')
    for i in range(6):evidence(db,now-timedelta(seconds=300-i*60),i+1)
    set_mode(db,room,ModeIn(mode='automatic',reason='Simulation policy authorization'),'dev-admin',now-timedelta(seconds=600))
    device=db.get(Device,'SIM-A')
    sample_in=TelemetryIn(device_id=device.id,boot_epoch='a'*32,sample_seq='2',observed_at=now,time_source='simulated',time_uncertainty_ms=0.,
        active_power_w=100.,voltage_v=230.,current_a=.5,energy_import_wh=10.,energy_export_wh=0.,desired_on=True,output_present=True,fault_latched=False,
        valid=True,calibrated=True,energy_status='known',source_mode='SIMULATED',source_version='unit')
    ingest_sample(db,sample_in,received_at=now)
    policy=create_policy(db,room,PolicyIn(name='Vacancy shedding',mode=mode,starts_at=now-timedelta(hours=1),ends_at=now+timedelta(hours=1),
        channel_ids=['channel-plug'],vacant_for_seconds=300,minimum_power_w=5.,reason='Explicit fixture authorization'),'dev-admin')
    return policy


def test_policy_shadow_does_not_fake_command_or_savings(room_app):
    app,_,now=room_app
    with app.state.session_factory() as db:
        policy=_policy_fixture(db,now,'SHADOW')
        row=evaluate_policy(db,policy,'dev-admin',now)
        assert row.content['eligible_count']==1
        assert row.content['savings_claim'] is False
        assert evaluation_dict(db,row)['execution_status']=='shadow'
        with pytest.raises(DomainError,match='SHADOW'):
            dispatch_evaluation(db,row,'dev-admin',app.state.settings,now)
        assert db.scalar(select(func.count()).select_from(Command))==0


def test_simulated_policy_dispatch_uses_genuine_ledger_and_is_idempotent(room_app):
    app,_,now=room_app
    with app.state.session_factory() as db:
        policy=_policy_fixture(db,now)
        row=evaluate_policy(db,policy,'dev-admin',now)
        assert row.content['eligible_count']==1
        dispatch_evaluation(db,row,'dev-admin',app.state.settings,now)
        first=list(row.command_ids)
        assert len(first)==1 and db.get(Command,first[0]).status=='requested'
        assert evaluation_dict(db,row)['verified_count']==0
        assert evaluation_dict(db,row)['execution_status']=='pending'
        dispatch_evaluation(db,row,'dev-admin',app.state.settings,now)
        assert row.command_ids==first


def test_dispatch_rechecks_manual_override(room_app):
    app,_,now=room_app
    with app.state.session_factory() as db:
        policy=_policy_fixture(db,now); row=evaluate_policy(db,policy,'dev-admin',now)
        set_mode(db,db.get(Space,'room-A'),ModeIn(mode='manual',duration_seconds=60,reason='Cancel automation'),'dev-admin',now)
        with pytest.raises(DomainError,match='Fresh evidence'):
            dispatch_evaluation(db,row,'dev-admin',app.state.settings,now)
        assert db.scalar(select(func.count()).select_from(Command))==0


def test_maintenance_interlock_applies_to_existing_device_commands(room_app):
    from app.control import eligibility
    app,_,now=room_app
    with app.state.session_factory() as db:
        _policy_fixture(db,now)
        set_mode(db,db.get(Space,'room-A'),ModeIn(mode='maintenance',reason='Maintenance interlock'),'dev-admin',now)
        assert eligibility(db,db.get(Device,'SIM-A'),now)=='room_maintenance_interlock'


def test_anomaly_persistence_dedupe_and_clear(room_app):
    app,_,now=room_app
    with app.state.session_factory() as db:
        room=db.get(Space,'room-A')
        for i in range(6):evidence(db,now-timedelta(seconds=300-i*60),i+1)
        results=evaluate_room(db,room,now)
        alarm=next(a for a in results if a.type=='vacant_load')
        assert alarm.evidence['baseline_status']=='insufficient'
        assert alarm.evidence['persistence_seconds']>=300
        evaluate_room(db,room,now+timedelta(seconds=20))
        assert db.scalar(select(func.count()).select_from(RoomAnomaly).where(RoomAnomaly.type=='vacant_load'))==1
        evidence(db,now+timedelta(seconds=30),7,occupied=True)
        evaluate_room(db,room,now+timedelta(seconds=30))
        assert alarm.status=='resolved'


def test_insufficient_baseline_does_not_invent_high_load(room_app):
    app,_,now=room_app
    with app.state.session_factory() as db:
        for i in range(12):evidence(db,now-timedelta(seconds=660-i*60),i+1,occupied=True,power=9000.)
        alarms=evaluate_room(db,db.get(Space,'room-A'),now)
        assert all(a.type!='conditional_high_load' for a in alarms)


def test_baseline_excludes_future_and_recent_target_leakage(room_app):
    app,_,now=room_app
    with app.state.session_factory() as db:
        room=db.get(Space,'room-A')
        seq=1
        # Use weekday/weekend-aligned prior weeks, with three distinct dates.
        for days in (21,14,7):
            for hours in (1,0,-1):
                evidence(db,now-timedelta(days=days,hours=hours),seq,occupied=True,power=100.);seq+=1
        baseline=conditional_baseline(db,room,now,'occupied')
        assert baseline['baseline_status']=='sufficient'
        assert baseline['baseline_median_w']==100.
        evidence(db,now+timedelta(days=7),seq,occupied=True,power=100000.)
        evidence(db,now-timedelta(hours=1),seq+1,occupied=True,power=100000.)
        assert conditional_baseline(db,room,now,'occupied')==baseline


def test_http_room_scope_naive_time_and_pagination(room_app):
    app,client,now=room_app
    login=client.post(P+'/auth/login',json={'username':'viewer','password':'development-only'}).json()['data']
    with app.state.session_factory() as db:
        db.get(User,'dev-viewer').campus_ids=['A'];db.commit()
    result=client.get(P+'/classrooms?limit=2000').json()
    assert result['meta']['total']==1 and result['data'][0]['id']=='room-A'
    assert client.get(P+'/classrooms/room-B').status_code==404
    assert client.get(P+'/classrooms?at=2026-01-01T00:00:00').status_code==422
    assert client.patch(P+'/classrooms/room-A/mode',headers={'X-CSRF-Token':login['csrf_token']},json={'mode':'automatic','reason':'Unauthorized viewer'}).status_code==403


def canonical_presence(now):
    from app.iot_ingestion import contract
    return {'schema_version':1,'event_id':contract().event_identity('SIM-SENSE','boot-1','1'),'device_id':'SIM-SENSE','product_family':'PRESENCE',
        'boot_id':'boot-1','sequence':'1','observed_at':now.isoformat(),'received_at':now.isoformat(),'monotonic_ms':1000,
        'source_mode':'SIMULATED','source_protocol':'virtual-v1','time_quality':'authenticated','quality':'valid',
        'readings':[{'capability':'presence.radar','channel_id':'sensor.radar','value':False,'unit':'boolean','quality':'valid'}],'raw':{'simulated':True}}


def test_canonical_ingest_durable_identity_and_conflict(room_app):
    app,client,now=room_app
    body=canonical_presence(now);headers={'Authorization':'Bearer unit-test-fixture-token-not-real-secret-123'}
    response=client.post(P+'/ingest/events',headers=headers,json=body)
    assert response.status_code==200,response.text
    assert response.json()['data']['durable'] is True
    assert client.post(P+'/ingest/events',headers=headers,json=body).json()['data']['status']=='duplicate'
    altered=deepcopy(body);altered['readings'][0]['value']=True
    assert client.post(P+'/ingest/events',headers=headers,json=altered).status_code==409
    with app.state.session_factory() as db:
        assert db.scalar(select(func.count()).select_from(HardwareEvent))==1
        assert snapshots(db,[db.get(Space,'room-A')],now)[0]['occupancy']=='vacant'


def test_gateway_receipt_is_not_fresh_presence(room_app):
    app,client,now=room_app
    body=canonical_presence(now);body['observed_at']=None;body['time_quality']='gateway_received'
    response=client.post(P+'/ingest/events',headers={'Authorization':'Bearer unit-test-fixture-token-not-real-secret-123'},json=body)
    assert response.status_code==200,response.text
    with app.state.session_factory() as db:
        state=snapshots(db,[db.get(Space,'room-A')],now+timedelta(seconds=1))[0]
        assert state['occupancy']=='unknown'
        assert 'TIME_UNCERTAIN' in state['channels'][0]['quality_flags'] or any('TIME_UNCERTAIN' in c['quality_flags'] for c in state['channels'])


def test_queued_automatic_command_revoked_by_manual_override(room_app):
    from app.control import advance_commands
    app,_,now=room_app
    with app.state.session_factory() as db:
        policy=_policy_fixture(db,now);evaluation=evaluate_policy(db,policy,'dev-admin',now)
        dispatch_evaluation(db,evaluation,'dev-admin',app.state.settings,now)
        set_mode(db,db.get(Space,'room-A'),ModeIn(mode='manual',duration_seconds=300,reason='Emergency operator hold'),'dev-admin',now+timedelta(seconds=1))
        advance_commands(db,now+timedelta(seconds=2),app.state.settings)
        assert db.get(Command,evaluation.command_ids[0]).status=='rejected'
        assert 'override' in db.get(Command,evaluation.command_ids[0]).history[-1]['reason']


def test_queued_automatic_command_revoked_by_arrival(room_app):
    from app.control import advance_commands
    app,_,now=room_app
    with app.state.session_factory() as db:
        policy=_policy_fixture(db,now);evaluation=evaluate_policy(db,policy,'dev-admin',now)
        dispatch_evaluation(db,evaluation,'dev-admin',app.state.settings,now)
        sample(db,'channel-presence',now+timedelta(seconds=1),7,{'occupancy':'occupied'})
        advance_commands(db,now+timedelta(seconds=2),app.state.settings)
        command=db.get(Command,evaluation.command_ids[0])
        assert command.status=='rejected' and command.history[-1]['reason']=='vacancy_no_longer_observed'


def test_evidence_immutable_at_sql_boundary(room_app):
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError
    app,_,now=room_app
    with app.state.session_factory() as db:
        evidence(db,now,1);db.commit()
    with app.state.session_factory() as db:
        with pytest.raises(DBAPIError,match='append-only'):
            db.execute(text("UPDATE channel_observations SET quality='good'"))


def test_switch_ack_is_durable_but_never_physical_verification(room_app):
    app,client,now=room_app
    with app.state.session_factory() as db:
        create_device(db,dict(id='SIM-SWITCH',name='Switch',campus_id='A',building_id='building-A',space_id='room-A',kind='switch',
            source_mode='SIMULATED',critical=False,allow_control=False,capabilities=['lighting']),'test');db.commit()
    app.state.settings.adapter_allowed_device_ids += ['SIM-SWITCH']
    body={'device_id':'SIM-SWITCH','boot_id':'b'*32,'id':'command_test','seq':'1','channel':2,'result':'commanded',
        'physical_verification':False,'uptime_ms':'1000'}
    headers={'Authorization':'Bearer unit-test-fixture-token-not-real-secret-123'}
    response=client.post(P+'/ingest/channel-acks',headers=headers,json=body)
    assert response.status_code==200,response.text
    assert response.json()['data']['physical_verification'] is False
    assert client.post(P+'/ingest/channel-acks',headers=headers,json=body).json()['data']['status']=='duplicate'
    assert client.post(P+'/ingest/channel-acks',headers=headers,json=body|{'physical_verification':True}).status_code==422
    with app.state.session_factory() as db:
        assert db.scalar(select(func.count()).select_from(ChannelAcknowledgement))==1
        assert db.scalar(select(func.count()).select_from(Command))==0


def test_canonical_and_wire_routes_share_one_energy_identity(room_app):
    import json
    from pathlib import Path
    from app.iot_ingestion import contract
    app,client,now=room_app
    event=json.loads((Path(__file__).resolve().parents[2]/'packages/iot-contract/examples/plug-event.json').read_text(encoding="utf-8"))
    event['device_id']='SIM-A';event['raw']['device_id']='SIM-A'
    event['sequence']='99';event['raw']['sample_seq']='99'
    event['event_id']=contract().event_identity('SIM-A',event['boot_id'],'99')
    headers={'Authorization':'Bearer unit-test-fixture-token-not-real-secret-123'}
    legacy=client.post(P+'/ingest/firmware',headers=headers,json=event['raw'])
    assert legacy.status_code==200,legacy.text
    canonical=client.post(P+'/ingest/events',headers=headers,json=event)
    assert canonical.status_code==200,canonical.text
    assert client.post(P+'/ingest/events',headers=headers,json=event).json()['data']['status']=='duplicate'
    with app.state.session_factory() as db:
        assert db.scalar(select(func.count()).select_from(Telemetry).where(Telemetry.device_id=='SIM-A',Telemetry.sample_seq=='99'))==1
        assert db.scalar(select(func.count()).select_from(HardwareEvent))==1
        assert db.scalar(select(func.count()).select_from(ChannelObservation).where(ChannelObservation.channel_id=='SIM-A:meter.aggregate'))==1


def test_channel_sequence_time_conflict_does_not_become_truth(room_app):
    app,_,now=room_app
    with app.state.session_factory() as db:
        sample(db,'channel-presence',now,100,{'occupancy':'vacant'})
        row=sample(db,'channel-presence',now+timedelta(seconds=30),2,{'occupancy':'occupied'})
        assert 'SEQUENCE_TIME_CONFLICT' in row.quality_flags
        assert snapshots(db,[db.get(Space,'room-A')],now+timedelta(seconds=30))[0]['occupancy']=='unknown'


def test_manual_resolution_suppresses_continuing_episode_until_known_clear(room_app):
    from app.db import iso
    app,_,now=room_app
    with app.state.session_factory() as db:
        room=db.get(Space,'room-A')
        for i in range(6):evidence(db,now-timedelta(seconds=300-i*60),i+1)
        alarm=next(a for a in evaluate_room(db,room,now) if a.type=='vacant_load')
        alarm.status='resolved';alarm.resolved_at=now
        alarm.notes=[*alarm.notes,{'at':iso(now),'by':'dev-admin','action':'resolved','text':'Reviewed known ongoing equipment'}]
        for i in range(1,67):evidence(db,now+timedelta(seconds=i*60),6+i)
        evaluate_room(db,room,now+timedelta(seconds=3960))
        assert db.scalar(select(func.count()).select_from(RoomAnomaly).where(RoomAnomaly.type=='vacant_load'))==1
        evidence(db,now+timedelta(seconds=3970),100,occupied=True)
        evaluate_room(db,room,now+timedelta(seconds=3970))
        for i in range(6):evidence(db,now+timedelta(seconds=4000+i*60),101+i)
        evaluate_room(db,room,now+timedelta(seconds=4300))
        assert db.scalar(select(func.count()).select_from(RoomAnomaly).where(RoomAnomaly.type=='vacant_load'))==2


def test_baseline_rejects_unavailable_as_of_time_and_cross_source(room_app):
    app,_,now=room_app
    with app.state.session_factory() as db:
        room=db.get(Space,'room-A');seq=1
        for days in (21,14,7):
            for hours in (1,0,-1):
                at=now-timedelta(days=days,hours=hours)
                sample(db,'channel-presence',at,seq,{'occupancy':'occupied'},received_at=now+timedelta(days=1))
                sample(db,'channel-plug',at,seq,{'active_power_w':100.,'output_present':True,'desired_on':True,'fault_latched':False},received_at=now+timedelta(days=1));seq+=1
        assert conditional_baseline(db,room,now,'occupied')['baseline_status']=='insufficient'
        assert conditional_baseline(db,room,now+timedelta(days=2),'occupied',source_mode='REAL')['baseline_status']=='insufficient'


def test_room_execution_history_reopens_after_request_and_uses_observed_verification(room_app):
    from app.control import advance_commands
    app,client,now=room_app
    with app.state.session_factory() as db:
        policy=_policy_fixture(db,now);evaluation=evaluate_policy(db,policy,'dev-admin',now)
        dispatch_evaluation(db,evaluation,'dev-admin',app.state.settings,now)
        evaluation_id=evaluation.id
        for seconds in (1,2,3):advance_commands(db,now+timedelta(seconds=seconds),app.state.settings)
        db.commit()
    login=client.post(P+'/auth/login',json={'username':'admin','password':'development-only'}).json()['data']
    response=client.get(P+'/classrooms/room-A/evaluations')
    assert response.status_code==200,response.text
    row=next(r for r in response.json()['data'] if r['id']==evaluation_id)
    assert row['execution_status']=='verified' and row['verified_count']==1
    assert row['commands'][0]['result']['output_present'] is False
    assert row['commands'][0]['result']['voltage_absence_proven'] is False


def switch_fixture(db,now):
    device=create_device(db,dict(id='SIM-SWITCH',name='Three-gang Switch',campus_id='A',building_id='building-A',space_id='room-A',kind='switch',
        source_mode='SIMULATED',critical=False,allow_control=True,capabilities=['lighting','hold','shed','restore','metering']),'test')
    device.commissioned=True;device.minimum_dwell_seconds=0
    binding=db.scalar(select(Binding).where(Binding.device_id==device.id));binding.valid_from=now-timedelta(hours=2)
    for i in (1,2,3):
        c=register_channel(db,ChannelIn(id=f'switch-relay-{i}',device_id=device.id,channel_key=f'relay.{i}',name=f'Gang {i}',kind='lighting',capabilities=['relay.commanded'],controllable=True),'test')
        sample(db,c.id,now,1,{'desired_on':True,'actuator_reported_on':True,'fault_latched':False},boot='b'*32)
    register_channel(db,ChannelIn(id='switch-meter',device_id=device.id,channel_key='meter.aggregate',name='All three outputs',kind='power',capabilities=['power.active'],unit='W'),'test')
    sample(db,'switch-meter',now,1,{'active_power_w':300.},boot='b'*32)
    return device


def test_switch_requires_exact_channel_and_only_changes_target(room_app):
    from app.control import create_command,advance_commands
    from app.schemas import CommandIn
    app,_,now=room_app
    with app.state.session_factory() as db:
        switch_fixture(db,now)
        with pytest.raises(DomainError,match='exact Switch'):
            create_command(db,CommandIn(device_id='SIM-SWITCH',action='shed',reason='Explicit test'),'switch-no-target','dev-admin',now)
        command,_=create_command(db,CommandIn(device_id='SIM-SWITCH',channel_id='switch-relay-2',action='shed',reason='Gang two test'),
            'switch-gang-two','dev-admin',now)
        assert command.channel_key=='relay.2'
        advance_commands(db,now+timedelta(seconds=1));advance_commands(db,now+timedelta(seconds=2))
        assert command.status=='acknowledged_unverified' and command.result is None
        state=snapshots(db,[db.get(Space,'room-A')],now+timedelta(seconds=2))[0]
        relays={c['channel_key']:c for c in state['channels'] if c['device_id']=='SIM-SWITCH' and c['kind']=='lighting'}
        assert [relays[f'relay.{i}']['value']['actuator_reported_on'] for i in (1,2,3)]==[True,False,True]
        assert all(c['value'].get('output_present') is None and not c['feedback_supported'] for c in relays.values())
        assert state['lighting']=='mixed' and state['lighting_verification_kind']=='actuator_reported_only'


def test_switch_wrong_channel_boot_sequence_and_expired_ack_cannot_complete(room_app):
    from app.control import create_command,advance_commands
    from app.schemas import CommandIn
    from app.iot_ingestion import ingest_switch_ack
    app,_,now=room_app
    with app.state.session_factory() as db:
        switch_fixture(db,now)
        command,_=create_command(db,CommandIn(device_id='SIM-SWITCH',channel_id='switch-relay-2',action='shed',reason='Exact ACK test'),
            'switch-ack-gates','dev-admin',now)
        advance_commands(db,now+timedelta(seconds=1))
        ack={'device_id':'SIM-SWITCH','boot_id':'b'*32,'id':command.id,'seq':str(command.sequence),'channel':2,'result':'commanded','physical_verification':False,'uptime_ms':'1000'}
        for changes in ({'channel':1},{'boot_id':'c'*32},{'seq':'99'}):
            receipt,_=ingest_switch_ack(db,ack|changes,now+timedelta(seconds=2))
            assert not receipt.matched and command.status=='dispatched'
        ingest_switch_ack(db,ack,now+timedelta(seconds=31))
        assert command.status=='timed_out'


def test_switch_locks_are_channel_scoped_and_holds_block_only_target_automation(room_app):
    from app.control import create_command
    from app.schemas import CommandIn
    from app.channel_control import channel_hold_until
    app,_,now=room_app
    with app.state.session_factory() as db:
        switch_fixture(db,now)
        a,_=create_command(db,CommandIn(device_id='SIM-SWITCH',channel_id='switch-relay-1',action='shed',reason='Channel one hold',manual_hold_seconds=900),
            'switch-one-hold','dev-admin',now)
        b,_=create_command(db,CommandIn(device_id='SIM-SWITCH',channel_id='switch-relay-2',action='shed',reason='Channel two independent'),
            'switch-two-separate','dev-admin',now)
        assert a.sequence==1 and b.sequence==2
        assert channel_hold_until(db,'switch-relay-1',now)==now+timedelta(seconds=900)
        assert channel_hold_until(db,'switch-relay-2',now) is None
        with pytest.raises(DomainError,match='outstanding command'):
            create_command(db,CommandIn(device_id='SIM-SWITCH',channel_id='switch-relay-1',action='restore',reason='Duplicate pending gang'),
                'switch-one-again','dev-admin',now)


def test_rule_revision_threshold_hysteresis_and_history_are_preserved(room_app):
    from app.room_rules import patch_rule,rule_for
    from app.classroom_schemas import AnomalyRulePatch
    app,_,now=room_app
    with app.state.session_factory() as db:
        room=db.get(Space,'room-A')
        for i in range(6):evidence(db,now-timedelta(seconds=300-i*60),i+1,power=100.)
        first=next(a for a in evaluate_room(db,room,now) if a.type=='vacant_load')
        original=deepcopy(first.evidence)
        patch_rule(db,room,AnomalyRulePatch(expected_revision=0,reason='Set reviewed threshold',vacant_power_threshold_w=80.,clear_hysteresis_ratio=.25),'dev-admin',now+timedelta(seconds=1))
        assert first.status=='resolved' and first.evidence==original
        second=next(a for a in evaluate_room(db,room,now+timedelta(seconds=2)) if a.type=='vacant_load')
        assert second.evidence['rule_revision']==1 and second.evidence['threshold_w']==80. and second.evidence['clear_threshold_w']==60.
        evidence(db,now+timedelta(seconds=3),10,power=70.)
        evaluate_room(db,room,now+timedelta(seconds=3));assert second.status=='open'
        evidence(db,now+timedelta(seconds=4),11,power=59.)
        evaluate_room(db,room,now+timedelta(seconds=4));assert second.status=='resolved'
        with pytest.raises(DomainError,match='reload'):
            patch_rule(db,room,AnomalyRulePatch(expected_revision=0,reason='Stale edit'),'dev-admin',now)
        patch_rule(db,room,AnomalyRulePatch(expected_revision=1,reason='Only disable',enabled=False),'dev-admin',now)
        assert rule_for(db,room)['config']['vacant_power_threshold_w']==80.


def authenticated_sense_event(now):
    import json,hashlib
    from pathlib import Path
    from app.iot_ingestion import contract
    vector=json.loads((Path(__file__).resolve().parents[2]/'packages/iot-contract/examples/presence-gatt-v1-test-vector.json').read_text(encoding="utf-8"))
    response=bytes.fromhex(vector['response_hex']);boot=int.from_bytes(response[9:13],'little');seq=int.from_bytes(response[13:17],'little')
    raw={'response_hex':response.hex(),'manufacturer_data_hex':response[1:25].hex(),'authentication':'hmac-sha256-nonce-v1',
        'proof_sha256':hashlib.sha256(response).hexdigest(),'boot':boot,'sample_seq':seq,'identity':int.from_bytes(response[5:9],'little'),
        'evidence_flags':response[53],'radar_age_ms':int.from_bytes(response[45:49],'little')}
    return {'schema_version':1,'event_id':contract().event_identity('SIM-SENSE',f'{boot:08x}',str(seq)),'device_id':'SIM-SENSE','product_family':'PRESENCE',
        'boot_id':f'{boot:08x}','sequence':str(seq),'observed_at':None,'received_at':now.isoformat(),'monotonic_ms':1000,'source_mode':'REAL',
        'source_protocol':'presence-gatt-v1','time_quality':'gateway_received','quality':'valid','raw':raw,
        'readings':[{'capability':'presence.radar','channel_id':'sensor.radar','value':False,'unit':'boolean','quality':'valid',
            'details':{'authenticity':'authenticated_gatt_hmac_sha256','continuous_occupancy':True,'measurement_age_ms':100}}]}


def test_authenticated_relative_sense_is_bounded_knowledge_not_invented_device_time(room_app):
    from app.iot_ingestion import ingest_event
    app,_,now=room_app
    with app.state.session_factory() as db:
        db.get(Device,'SIM-SENSE').source_mode='REAL';db.flush()
        event=authenticated_sense_event(now)
        row,_=ingest_event(db,event,now+timedelta(seconds=1))
        assert row.observed_at is None
        room=db.get(Space,'room-A')
        assert snapshots(db,[room],now)[0]['occupancy']=='unknown'
        state=snapshots(db,[room],now+timedelta(seconds=1))[0]
        channel=next(c for c in state['channels'] if c['kind']=='presence')
        assert state['occupancy']=='vacant' and channel['observed_at'] is None
        assert channel['effective_at']==now+timedelta(seconds=1)
        assert channel['time_basis']=='authenticated_relative_receipt'
        assert channel['measurement_age_ms']==2100.
        assert channel['valid_until']==now+timedelta(seconds=3.9)
        assert snapshots(db,[room],now+timedelta(seconds=3.899))[0]['occupancy']=='vacant'
        assert snapshots(db,[room],now+timedelta(seconds=3.9))[0]['occupancy']=='unknown'


def test_delayed_authenticated_sense_proof_remains_unknown(room_app):
    from app.iot_ingestion import ingest_event
    app,_,now=room_app
    with app.state.session_factory() as db:
        db.get(Device,'SIM-SENSE').source_mode='REAL';db.flush()
        ingest_event(db,authenticated_sense_event(now-timedelta(minutes=5)),now)
        state=snapshots(db,[db.get(Space,'room-A')],now)[0]
        assert state['occupancy']=='unknown'


def test_switch_policy_uses_aggregate_gate_without_tripling_meter_or_faking_reduction(room_app):
    from app.control import advance_commands
    app,_,now=room_app
    with app.state.session_factory() as db:
        switch_fixture(db,now)
        for i in range(6):evidence(db,now-timedelta(seconds=300-i*60),i+1,power=100.)
        room=db.get(Space,'room-A')
        set_mode(db,room,ModeIn(mode='automatic',reason='Explicitly enable simulated policy'),'dev-admin',now-timedelta(hours=1))
        policy=create_policy(db,room,PolicyIn(name='Three-gang policy',mode='SIMULATED',starts_at=now-timedelta(hours=1),ends_at=now+timedelta(hours=1),
            channel_ids=['switch-relay-1','switch-relay-2','switch-relay-3'],vacant_for_seconds=300,minimum_power_w=5.,reason='All selected gangs'),'dev-admin')
        state=snapshots(db,[room],now)[0]
        assert state['observed_power_w']==400.  # 300 W aggregate + 100 W Plug, never 3×300 W.
        evaluation=evaluate_policy(db,policy,'dev-admin',now)
        assert evaluation.content['eligible_count']==3
        assert evaluation.content['modeled_reduction_w'] is None
        assert all(t['observed_power_w'] is None and t['aggregate_power_w']==300. for t in evaluation.content['targets'])
        dispatch_evaluation(db,evaluation,'dev-admin',app.state.settings,now)
        advance_commands(db,now+timedelta(seconds=1));advance_commands(db,now+timedelta(seconds=2))
        outcome=evaluation_dict(db,evaluation)
        assert outcome['unverified_count']==3 and outcome['verified_count']==outcome['failed_count']==0
        assert outcome['execution_status']=='acknowledged_unverified'
        assert snapshots(db,[room],now+timedelta(seconds=2))[0]['lighting']=='off'


def test_later_channel_installation_does_not_rewrite_earlier_vacancy(room_app):
    app,_,now=room_app
    with app.state.session_factory() as db:
        evidence(db,now-timedelta(seconds=60),1)
        channel=register_channel(db,ChannelIn(id='later-radar',device_id='SIM-SENSE',channel_key='sensor.radar2',name='Later radar',kind='presence',capabilities=['presence.radar']),'test')
        channel.introduced_at=now
        room=db.get(Space,'room-A')
        assert snapshots(db,[room],now-timedelta(seconds=30))[0]['occupancy']=='vacant'
        assert snapshots(db,[room],now)[0]['occupancy']=='unknown'


def test_switch_aggregate_enters_existing_telemetry_without_export_fabrication(room_app):
    import json
    from pathlib import Path
    from app.iot_ingestion import ingest_event,contract
    app,_,now=room_app
    with app.state.session_factory() as db:
        device=switch_fixture(db,now)
        event=json.loads((Path(__file__).resolve().parents[2]/'packages/iot-contract/examples/switch-event.json').read_text(encoding="utf-8"))
        event['device_id']=device.id;event['raw']['device_id']=device.id
        event['sequence']='100';event['raw']['sample_seq']='100'
        event['event_id']=contract().event_identity(device.id,event['boot_id'],'100')
        row,created=ingest_event(db,event,now+timedelta(seconds=1))
        assert created
        telemetry=db.get(Telemetry,device.latest_telemetry_id)
        assert telemetry.active_power_w==60. and telemetry.energy_import_wh==123.
        assert telemetry.energy_export_wh is None
        assert 'EXPORT_UNAVAILABLE' in telemetry.quality_flags and 'ENERGY_UNCERTAIN' in telemetry.quality_flags
        assert telemetry.quality=='uncertain' and telemetry.raw_payload['event_id']==row.id
        ingest_event(db,event,now+timedelta(seconds=2))
        assert db.scalar(select(func.count()).select_from(Telemetry).where(Telemetry.device_id==device.id))==1
        for channel in db.scalars(select(DeviceChannel).where(DeviceChannel.device_id==device.id,DeviceChannel.kind=='lighting')):
            latest=db.scalar(select(ChannelObservation).where(ChannelObservation.channel_id==channel.id).order_by(ChannelObservation.id.desc()).limit(1))
            assert 'active_power_w' not in latest.value and latest.value.get('output_present') is None


def test_classroom_devices_and_parent_accounting_share_one_antichain(room_app):
    from app.models import Circuit
    from app.accounting import compute_energy,selected_devices
    app,_,now=room_app
    with app.state.session_factory() as db:
        switch=switch_fixture(db,now)
        db.add(Circuit(id='room-parent-meter-boundary',campus_id='A',building_id='building-A',name='One building measurement boundary',kind='main',source_mode='SIMULATED'))
        db.flush()
        for device in db.scalars(select(Device).where(Device.campus_id=='A')):
            device.circuit_id='room-parent-meter-boundary'
            for binding in db.scalars(select(Binding).where(Binding.device_id==device.id)):
                binding.circuit_id='room-parent-meter-boundary'
        meter=create_device(db,dict(id='SIM-BOUNDARY',name='Building boundary',campus_id='A',building_id='building-A',circuit_id='room-parent-meter-boundary',
            kind='meter',source_mode='SIMULATED',critical=True,allow_control=False,capabilities=['metering']),'test')
        db.scalar(select(Binding).where(Binding.device_id==meter.id)).valid_from=now-timedelta(days=1)
        for seq,at,energy in ((1,now-timedelta(seconds=60),0.),(2,now,1000.)):
            ingest_sample(db,TelemetryIn(device_id=meter.id,boot_epoch='d'*32,sample_seq=str(seq),observed_at=at,time_source='simulated',time_uncertainty_ms=0.,
                active_power_w=60000.,voltage_v=230.,current_a=260.,energy_import_wh=energy,energy_export_wh=0.,valid=True,calibrated=True,
                energy_status='known',source_mode='SIMULATED',source_version='complete-boundary-fixture'),received_at=at)
        energy=compute_energy(db,campus_id='A',building_id='building-A',start=now-timedelta(seconds=60),end=now)
        assert energy['selected_device_ids']==['SIM-BOUNDARY'] and energy['known_kwh']==1.
        assert energy['source_mode']=='SIMULATED'
        with pytest.raises(DomainError,match='meter and a load'):
            compute_energy(db,start=now-timedelta(seconds=60),end=now,device_ids=['SIM-BOUNDARY','SIM-SWITCH'])


def test_late_failed_delivery_receipt_never_regresses_switch_terminal(room_app):
    from app.control import create_command,advance_commands
    from app.schemas import CommandIn
    from app.adapter import record_delivery
    from app.schemas import DeliveryIn
    app,_,now=room_app
    with app.state.session_factory() as db:
        switch_fixture(db,now)
        command,_=create_command(db,CommandIn(device_id='SIM-SWITCH',channel_id='switch-relay-1',action='shed',reason='Late receipt regression'),
            'late-switch-receipt','dev-admin',now)
        command.lease_id='lease-unit';command.lease_expires_at=now+timedelta(seconds=30)
        advance_commands(db,now+timedelta(seconds=1));advance_commands(db,now+timedelta(seconds=2))
        assert command.status=='acknowledged_unverified'
        db.flush()
        record_delivery(db,command.id,DeliveryIn(lease_id='lease-unit',status='failed',reason='mqtt_delivery_uncertain'),['SIM-SWITCH'],now+timedelta(seconds=3))
        assert command.status=='acknowledged_unverified'
