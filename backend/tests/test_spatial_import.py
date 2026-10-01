"""Reference-only package bootstrap and additive upgrade; no device/demo side effects."""
import copy
import json
from pathlib import Path
import pytest
from sqlalchemy import select,func
from app.config import Settings
from app.db import Base,make_engine,make_session_factory
from app.models import Campus,Building,Floor,Space,Device,Binding,Telemetry,User,CarbonFactor,Tariff,State,Audit
from app.spatial import canonical,sha,read_package,import_package,spatial_status
from app.common import DomainError


def package(root,seed):
    root.mkdir(parents=True,exist_ok=True)
    raw=canonical(seed)+b'\n';(root/'seed.json').write_bytes(raw)
    manifest={'schema_version':1,'format':'carbentra-spatial-runtime','source_version':seed['source_version'],'seed_url':'seed.json',
        'artifacts':{'seed.json':{'bytes':len(raw),'sha256':sha(raw)}}}
    manifest['version']=sha(canonical(manifest));(root/'manifest.json').write_bytes(canonical(manifest)+b'\n')
    return manifest['version']


def entry(ident,**values):
    return {'id':ident,'name':ident,'source_namespace':'njupt-search','source_id':ident,'source_version':'source-v1','synthetic':False,**values}


@pytest.fixture
def imported(tmp_path):
    seed={'schema_version':1,'format':'carbentra-spatial-seed','source_version':'source-v1','campuses':[entry('campus-a')],
        'buildings':[entry('building-a',campus_id='campus-a',levels=3)],'floors':[entry('floor-a',building_id='building-a',level=1)],
        'spaces':[entry('space-a',campus_id='campus-a',building_id='building-a',floor_id='floor-a')]}
    root=tmp_path/'package';package(root,seed)
    # Production configuration is validated normally; storage below is an isolated unit-test fixture.
    settings=Settings(env='production',database_url='postgresql+psycopg://operator@localhost/fixture',cookie_secure=True,auto_migrate=False,
        allowed_origins=['https://campus.example.invalid'],spatial_seed_path=root/'seed.json',spatial_manifest_path=root/'manifest.json')
    engine=make_engine('sqlite:///:memory:');Base.metadata.create_all(engine)
    with make_session_factory(engine)() as db:
        yield db,settings,seed,root
    engine.dispose()


def count(db,model):
    return db.scalar(select(func.count()).select_from(model))


def test_production_reference_check_and_bootstrap_create_no_accounts_devices_or_measurements(imported):
    db,settings,_,_=imported
    report=import_package(db,settings)
    assert report['applicable'] and report['resources']['buildings']['additions']==['building-a']
    assert count(db,Building)==count(db,State)==0
    result=import_package(db,settings,apply=True);db.commit()
    assert result['applied'] and result['changed']
    assert all(count(db,model)==1 for model in (Campus,Building,Floor,Space))
    assert all(count(db,model)==0 for model in (User,Device,Binding,Telemetry,CarbonFactor,Tariff))
    assert spatial_status(db,settings)['synchronized'] is True
    before=count(db,Audit);time=db.get(State,'spatial').value['imported_at']
    assert import_package(db,settings,apply=True)['changed'] is False;db.commit()
    assert count(db,Audit)==before and db.get(State,'spatial').value['imported_at']==time


def test_additive_upgrade_and_metadata_refresh_preserve_existing_bindings(imported):
    db,settings,seed,root=imported
    import_package(db,settings,apply=True);db.commit()
    from app.registry import create_device
    device=create_device(db,{'id':'INERT-REGISTRY','name':'Fixture without actuation','campus_id':'campus-a','building_id':'building-a',
        'floor_id':'floor-a','space_id':'space-a','kind':'sensor','source_mode':'REAL'},'test');db.commit()
    binding=db.scalar(select(Binding).where(Binding.device_id==device.id));snapshot=(binding.id,binding.valid_from,binding.space_id)
    old_version=db.get(State,'spatial').value['package_version']
    seed['source_version']='source-v2';seed['buildings'][0]['name']='Renamed reference';seed['buildings'].append(entry('building-b',campus_id='campus-a',levels=2));version=package(root,seed)
    status=spatial_status(db,settings)
    assert not status['synchronized'] and status['bundled']['package_version']==version and status['imported']['package_version']==old_version
    result=import_package(db,settings,apply=True);db.commit()
    assert result['resources']['buildings']['additions']==['building-b']
    assert db.get(Building,'building-a').name=='Renamed reference'
    assert (binding.id,binding.valid_from,binding.space_id)==snapshot and count(db,Binding)==1
    assert spatial_status(db,settings)['synchronized'] is True
    assert not import_package(db,settings,apply=True)['changed']


@pytest.mark.parametrize('change',['remove','parent','source'])
def test_destructive_or_identity_reconciliation_is_atomic_and_refused(imported,change):
    db,settings,seed,root=imported;import_package(db,settings,apply=True);db.commit()
    old=db.get(State,'spatial').value.copy()
    seed['campuses'].append(entry('campus-new'))
    if change=='remove':seed['spaces']=[]
    elif change=='parent':
        seed['buildings'][0]['campus_id']='campus-new';seed['spaces'][0]['campus_id']='campus-new'
    else:seed['buildings'][0]['source_id']='different-upstream-identity'
    package(root,seed)
    plan=import_package(db,settings);assert plan['applicable'] is False
    with pytest.raises(DomainError,match='reconciliation') as error:import_package(db,settings,apply=True)
    assert error.value.code=='spatial_reconciliation_required'
    assert db.get(Campus,'campus-new') is None and db.get(Space,'space-a') is not None
    assert db.get(State,'spatial').value==old


@pytest.mark.parametrize('corrupt',['manifest','seed','expected'])
def test_manifest_seed_and_operator_pin_integrity_are_required(imported,corrupt):
    _,settings,_,root=imported
    expected=None
    if corrupt=='manifest':
        data=json.loads((root/'manifest.json').read_text(encoding="utf-8"));data['source_version']='tampered';(root/'manifest.json').write_text(json.dumps(data), encoding="utf-8")
    elif corrupt=='seed':(root/'seed.json').write_bytes((root/'seed.json').read_bytes()+b' ')
    else:expected='0'*64
    with pytest.raises(DomainError) as error:read_package(settings,expected)
    assert error.value.code=='spatial_package_invalid'


def test_real_pinned_package_is_verified_without_demo_seed():
    seed,identity=read_package(Settings(worker_enabled=False))
    assert len(seed['campuses'])==3 and len(seed['buildings'])==136 and len(seed['floors'])==41 and len(seed['spaces'])==603
    assert len(identity['package_version'])==len(identity['seed_sha256'])==64


@pytest.mark.parametrize('value',[True,1.5,float('inf'),'unknown'])
def test_source_floor_values_are_not_silently_truncated(value):
    from app.spatial import source_integer
    with pytest.raises(DomainError):source_integer(value)


def test_explicit_cli_reference_bootstrap_never_starts_demo_or_auth(tmp_path):
    import os,subprocess,sys
    seed={'schema_version':1,'format':'carbentra-spatial-seed','source_version':'cli-fixture','campuses':[entry('cli-campus')],
        'buildings':[],'floors':[],'spaces':[]}
    root=tmp_path/'bundle';version=package(root,seed)
    url=f"sqlite:///{tmp_path/'reference.db'}"
    engine=make_engine(url);Base.metadata.create_all(engine)
    env={**os.environ,'CARBENTRA_ENV':'test','CARBENTRA_DATABASE_URL':url,'CARBENTRA_DEV_AUTH':'false','CARBENTRA_SEED_DEMO':'false',
        'CARBENTRA_SPATIAL_SEED_PATH':str(root/'seed.json'),'CARBENTRA_SPATIAL_MANIFEST_PATH':str(root/'manifest.json')}
    for action in ('--check','--apply'):
        run=subprocess.run([sys.executable,'-m','app.import_spatial',action,'--expected-version',version],env=env,capture_output=True,text=True)
        assert run.returncode==0,run.stderr+run.stdout
        assert json.loads(run.stdout)['reference_only'] is True
        with make_session_factory(engine)() as db:
            assert count(db,Campus)==(1 if action=='--apply' else 0)
            assert all(count(db,model)==0 for model in (User,Device,Telemetry,Tariff,CarbonFactor))
    engine.dispose()
