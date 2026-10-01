"""HTTP identities must remain one stable, non-normalizing URL path segment."""
from urllib.parse import quote

import pytest

from app.models import Circuit, Device
from test_resource_scope import scoped, value


@pytest.mark.parametrize('resource,model', [('devices',Device),('circuits',Circuit)])
@pytest.mark.parametrize('identifier', ['.','..',' . ',' .. '])
def test_dot_segment_identity_is_rejected_without_persistence(scoped,resource,model,identifier):
    application,client,headers,records=scoped
    body={'id':identifier,'name':'Local malformed identity fixture','campus_id':records['A']['campus'],'source_mode':'SIMULATED'}
    response=client.post('/api/v1/'+resource,headers=headers,json=body)
    assert response.status_code==422,(resource,identifier,response.status_code,response.text)
    with application.state.session_factory() as db:
        assert db.get(model,identifier.strip()) is None


@pytest.mark.parametrize('resource', ['devices','circuits'])
@pytest.mark.parametrize('suffix', ['v1.2','v1..2','...'])
def test_safe_dotted_identity_roundtrips_exactly(scoped,resource,suffix):
    _,client,headers,records=scoped
    identifier='QA-URL-'+resource+'-'+suffix
    body={'id':identifier,'name':'Local dotted identity fixture','campus_id':records['A']['campus'],'source_mode':'SIMULATED'}
    result=value(client.post('/api/v1/'+resource,headers=headers,json=body),201)
    assert result['id']==identifier
    if resource=='devices':
        assert value(client.get('/api/v1/devices/'+quote(identifier,safe='')))['id']==identifier
    result=value(client.patch('/api/v1/'+resource+'/'+quote(identifier,safe=''),headers=headers,json={'name':'Local dotted identity renamed'}))
    assert result['id']==identifier and result['name']=='Local dotted identity renamed'
