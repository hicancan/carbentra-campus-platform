"""Real streaming HTTP authorization, including revocation while connected."""
import json
import queue
import threading
import time

import httpx
import pytest
import uvicorn
from sqlalchemy import select,func
from app.models import Event
from test_resource_scope import scoped,new_user,value,P


def wait_for(fn,seconds=5):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        result=fn()
        if result:return result
        time.sleep(.05)
    raise AssertionError('Expected streaming condition did not occur')


def test_sse_filters_events_and_revalidates_revoked_session(scoped):
    application,admin,headers,records=scoped
    user,client,_=new_user(scoped)
    server=uvicorn.Server(uvicorn.Config(application,host='127.0.0.1',port=18123,lifespan='off',log_level='warning',proxy_headers=False))
    thread=threading.Thread(target=server.run,daemon=True)
    thread.start()
    wait_for(lambda:server.started)
    received=[];opened=threading.Event();closed=threading.Event();stop=threading.Event();errors=[]
    with application.state.session_factory() as db:
        cursor=db.scalar(select(func.max(Event.id))) or 0
    cookie=client.cookies.get('carbentra_session')
    def stream():
        try:
            with httpx.Client(timeout=httpx.Timeout(10,read=10),trust_env=False) as transport:
                with transport.stream('GET',f'http://127.0.0.1:18123{P}/events?after_id={cursor}',headers={'Cookie':'carbentra_session='+cookie}) as response:
                    assert response.status_code==200
                    opened.set()
                    for line in response.iter_lines():
                        if line.startswith('data: '):received.append(json.loads(line[6:]))
                        if stop.is_set():break
        except Exception as exc:errors.append(str(exc))
        finally:closed.set()
    reader=threading.Thread(target=stream,daemon=True)
    reader.start()
    try:
        assert opened.wait(5),errors
        value(admin.patch(P+'/devices/'+records['B']['device'],headers=headers,json={'name':'QA unobservable campus B event'}))
        value(admin.patch(P+'/devices/'+records['A']['device'],headers=headers,json={'name':'QA observable campus A event'}))
        wait_for(lambda:any(e['entity_id']==records['A']['device'] for e in received))
        assert all(e['campus_id']=='QA-SCOPE-A' for e in received),received
        value(admin.patch(P+'/users/'+user['id'],headers=headers,json={'campus_ids':[]}))
        assert client.get(P+'/auth/me').status_code==401
        with application.state.session_factory() as db:
            revoked_cursor=db.scalar(select(func.max(Event.id))) or 0
        time.sleep(1.1)
        value(admin.patch(P+'/devices/'+records['A']['device'],headers=headers,json={'name':'QA event after session revocation'}))
        closed.wait(2.5)
        after=[e for e in received if e['id']>revoked_cursor]
        assert not after,'SSE delivered resource events after session/scope revocation: '+json.dumps(after)
        assert closed.is_set(),'Revoked SSE stream remained open beyond revalidation interval'
    finally:
        stop.set();client.close();server.should_exit=True
        reader.join(timeout=3);thread.join(timeout=3)
