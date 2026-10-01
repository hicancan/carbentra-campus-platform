"""Exact secret handling and account-local authentication abuse boundaries."""
import pytest
from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app


@pytest.fixture
def auth_app(tmp_path):
    application=create_app(Settings(env='test',database_url=f'sqlite:///{tmp_path}/auth.sqlite3',dev_auth=True,seed_demo=False,worker_enabled=False))
    with TestClient(application,raise_server_exceptions=False) as client:yield client


def test_password_whitespace_is_meaningful_and_roundtrips_exactly(auth_app):
    admin=auth_app.post('/api/v1/auth/login',json={'username':'admin','password':'development-only'})
    assert admin.status_code==200
    headers={'X-CSRF-Token':admin.json()['data']['csrf_token']}
    exact='  QA exact local password 000000  '
    create=auth_app.post('/api/v1/users',headers=headers,json={'username':'qa-spaces','display_name':'QA exact password fixture','role':'viewer','campus_ids':[],'password':exact})
    assert create.status_code==201,create.text
    response=auth_app.post('/api/v1/auth/login',json={'username':'qa-spaces','password':exact})
    assert response.status_code==200,'Stored password cannot be used verbatim: '+response.text
    assert auth_app.post('/api/v1/auth/login',json={'username':'qa-spaces','password':exact.strip()}).status_code==401,'Distinct password accepted after secret normalization'


def test_one_accounts_failures_do_not_lock_other_account_at_same_proxy_address(auth_app):
    for _ in range(8):
        response=auth_app.post('/api/v1/auth/login',json={'username':'viewer','password':'QA wrong password'})
        assert response.status_code==401,response.text
    blocked=auth_app.post('/api/v1/auth/login',json={'username':'viewer','password':'QA wrong password'})
    assert blocked.status_code==429
    other=auth_app.post('/api/v1/auth/login',json={'username':'operator','password':'development-only'})
    assert other.status_code==200,'Per-address-only limiter lets one account block every account behind the same proxy: '+other.text


@pytest.mark.parametrize("content_type",["application/json","Application/JSON","application/vnd.carbentra+json"])
def test_strict_json_gate_covers_all_supported_json_media_types(auth_app,content_type):
    response=auth_app.post('/api/v1/auth/login',headers={'Content-Type':content_type},content='{"username":"viewer","username":"admin","password":"development-only"}')
    assert response.status_code in {415,422},f"Duplicate-key JSON bypassed strict gate via {content_type}: {response.status_code}"


def test_deeply_nested_json_is_a_bounded_client_error(auth_app):
    response=auth_app.post('/api/v1/auth/login',headers={'Content-Type':'application/json'},content='['*2000+'0'+']'*2000)
    assert response.status_code==422,response.text


@pytest.mark.parametrize("changes",[{"enabled":False},{"role":"viewer"},{"campus_ids":[]}])
def test_last_global_administrator_cannot_be_removed_when_only_scoped_admin_remains(auth_app,changes):
    auth=auth_app.post('/api/v1/auth/login',json={'username':'admin','password':'development-only'})
    assert auth.status_code==200
    headers={'X-CSRF-Token':auth.json()['data']['csrf_token']}
    created=auth_app.post('/api/v1/users',headers=headers,json={'username':'qa-scoped-admin','display_name':'QA scoped admin fixture','role':'admin','campus_ids':[],'password':'qa-scoped-admin-password-000000'})
    assert created.status_code==201,created.text
    response=auth_app.patch('/api/v1/users/dev-admin',headers=headers,json=changes)
    assert response.status_code==409,'Scoped-only administrators cannot restore the last disabled global admin; platform management was locked out'


def test_global_administrator_handoff_remains_possible(auth_app):
    auth=auth_app.post('/api/v1/auth/login',json={'username':'admin','password':'development-only'})
    headers={'X-CSRF-Token':auth.json()['data']['csrf_token']}
    created=auth_app.post('/api/v1/users',headers=headers,json={'username':'qa-next-global','display_name':'QA next global administrator','role':'admin','campus_ids':None,'password':'qa-next-global-password-000000'})
    assert created.status_code==201,created.text
    response=auth_app.patch('/api/v1/users/dev-admin',headers=headers,json={'enabled':False})
    assert response.status_code==200,'Another global administrator exists, so this handoff should be permitted: '+response.text
    assert auth_app.get('/api/v1/auth/me').status_code==401
    signed_in=auth_app.post('/api/v1/auth/login',json={'username':'qa-next-global','password':'qa-next-global-password-000000'})
    assert signed_in.status_code==200
    assert auth_app.get('/api/v1/users').status_code==200


def test_nonascii_wrong_fixture_password_is_unauthorized_not_server_error(auth_app):
    response=auth_app.post('/api/v1/auth/login',json={'username':'admin','password':'错误的密码'})
    assert response.status_code==401,response.text


def test_nonascii_csrf_header_is_forbidden_not_server_error(auth_app):
    auth=auth_app.post('/api/v1/auth/login',json={'username':'admin','password':'development-only'})
    assert auth.status_code==200
    response=auth_app.patch('/api/v1/settings',headers=[(b'X-CSRF-Token',b'\xe9')],json={})
    assert response.status_code==403,response.text


def test_nonascii_adapter_identity_is_unauthorized_not_server_error(auth_app):
    from pydantic import SecretStr
    auth_app.app.state.settings.adapter_token=SecretStr('local-auth-acceptance-only-000000000000')
    response=auth_app.get('/api/v1/adapter/commands',headers=[(b'Authorization',b'Bearer \xe9')])
    assert response.status_code==401,response.text


@pytest.mark.parametrize('field',['username','password'])
def test_unpaired_unicode_surrogate_is_a_validation_error(auth_app,field):
    import json
    body={'username':'admin','password':'QA wrong fixture password'}
    body[field]='\ud800'
    response=auth_app.post('/api/v1/auth/login',content=json.dumps(body),headers={'Content-Type':'application/json'})
    assert response.status_code==422,response.text
    assert 'QA wrong fixture password' not in response.text


@pytest.mark.parametrize('peer, trusted, forwarded, expected',[
    ('127.0.0.1', [], '198.51.100.1', '127.0.0.1'),
    ('127.0.0.1', ['127.0.0.1/32'], '198.51.100.1, 203.0.113.7', '203.0.113.7'),
    ('127.0.0.1', ['127.0.0.1/32','10.0.0.0/24'], '203.0.113.7, 10.0.0.2', '203.0.113.7'),
    ('127.0.0.1', ['127.0.0.1/32'], '203.0.113.7, invalid', '127.0.0.1'),
])
def test_forwarded_client_address_requires_a_verified_proxy_chain(peer,trusted,forwarded,expected):
    from types import SimpleNamespace
    from starlette.requests import Request
    from app.security import client_address
    application=SimpleNamespace(state=SimpleNamespace(settings=SimpleNamespace(trusted_proxy_cidrs=trusted)))
    request=Request({'type':'http','client':(peer,12345),'headers':[(b'x-forwarded-for',forwarded.encode())],'app':application})
    assert client_address(request)==expected


def test_spoofed_forwarded_addresses_do_not_reset_login_limit(auth_app):
    for index in range(8):
        response=auth_app.post('/api/v1/auth/login',headers={'X-Forwarded-For':f'198.51.100.{index+1}'},
            json={'username':'viewer','password':'QA incorrect fixture password'})
        assert response.status_code==401,response.text
    response=auth_app.post('/api/v1/auth/login',headers={'X-Forwarded-For':'203.0.113.200'},
        json={'username':'viewer','password':'QA incorrect fixture password'})
    assert response.status_code==429,response.text
