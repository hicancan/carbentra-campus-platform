"""Actual FastAPI application with isolated SIMULATED network-test registry only.

Not a replacement server or production bootstrap. Uses the real application,
models, auth, ingestion, command ledger, adapter leases and ACK transitions.
"""
import argparse
from contextlib import asynccontextmanager
from pathlib import Path
import sys
import os
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from app.main import create_app
from app.config import Settings
from app.models import Campus, Building, Space, DeviceChannel
from app.registry import create_device


def build(database, token):
    ids=[f'virtual-{family}-{room}' for room in ('a101','a102') for family in ('plug','switch','sense')]
    app=create_app(Settings(env='test',database_url='sqlite:///'+str(database),dev_auth=True,
        worker_enabled=False,simulation_enabled=False,adapter_token=token,adapter_allowed_device_ids=ids))
    if os.environ.get('CARBENTRA_TEST_LOSE_FIRST_DELIVERY')=='true':
        from fastapi.responses import JSONResponse
        lost=set()
        @app.middleware('http')
        async def lose_first_delivery(request,call_next):
            if request.method=='POST' and request.url.path.endswith('/delivery') and request.url.path not in lost:
                lost.add(request.url.path)
                return JSONResponse({'error':{'code':'synthetic_network_outage'}},status_code=503)
            return await call_next(request)
    original=app.router.lifespan_context
    @asynccontextmanager
    async def lifespan(application):
        async with original(application):
            with application.state.session_factory() as db:
                if db.get(Campus,'network-campus') is None:
                    db.add(Campus(id='network-campus',name='Virtual integration campus',source='synthetic_network_test'))
                    db.flush();db.add(Building(id='network-building',campus_id='network-campus',name='Virtual integration building',source='synthetic_network_test'))
                    db.flush()
                    for room in ('a101','a102'):
                        db.add(Space(id=room,campus_id='network-campus',building_id='network-building',name='Virtual '+room,kind='classroom_reference',source='synthetic_network_test',confidence='synthetic'))
                    db.flush()
                    for room in ('a101','a102'):
                        for family,kind in [('plug','smart_plug'),('switch','switch'),('sense','presence')]:
                            ident=f'virtual-{family}-{room}'
                            device=create_device(db,dict(id=ident,name=ident,campus_id='network-campus',building_id='network-building',space_id=room,kind=kind,source_mode='SIMULATED',critical=False,allow_control=family!='sense',capabilities=['hold','shed','restore','metering'] if family!='sense' else ['presence']), 'network-test')
                            device.commissioned=True;device.dispatch_mode='VIRTUAL';device.minimum_dwell_seconds=0;device.profile_id='lab-load'
                            if family=='switch':
                                for i in (1,2,3):
                                    db.add(DeviceChannel(id=f'{ident}:relay.{i}',device_id=ident,campus_id='network-campus',channel_key=f'relay.{i}',name=f'Virtual lighting {i}',kind='lighting',unit=None,freshness_seconds=10,capabilities=['relay.commanded','control.mode','control.manual_hold_until'],controllable=True))
                                db.add(DeviceChannel(id=f'{ident}:meter.aggregate',device_id=ident,campus_id='network-campus',channel_key='meter.aggregate',name='Virtual aggregate meter',kind='power',unit='W',freshness_seconds=10,capabilities=['power.active','energy.import'],controllable=False))
                    db.commit()
            yield
    app.router.lifespan_context=lifespan
    return app

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--database',type=Path,required=True);p.add_argument('--port',type=int,required=True);args=p.parse_args()
    import uvicorn
    uvicorn.run(build(args.database,os.environ['CARBENTRA_ADAPTER_TOKEN']),host='127.0.0.1',port=args.port,log_level='warning')
