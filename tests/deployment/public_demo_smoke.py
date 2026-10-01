"""Real trusted HTTPS checks against an explicitly disposable public simulation."""
import argparse
from http.cookiejar import CookieJar
import json
from pathlib import Path
import ssl
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import build_opener, HTTPCookieProcessor, HTTPSHandler, ProxyHandler, Request

parser = argparse.ArgumentParser()
parser.add_argument('--base-url', required=True)
parser.add_argument('--fixture-directory', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--disposable-fixture', required=True, action='store_true')
args = parser.parse_args()
url = urlparse(args.base_url)
if url.scheme != 'https' or url.hostname not in {'localhost', '127.0.0.1'} or url.username or url.password:
    raise SystemExit('Only an explicit local HTTPS fixture is permitted')
fixture = args.fixture_directory
checks = []
completed = False
failure = None


def check(name, condition):
    checks.append({'name': name, 'passed': bool(condition)})
    if not condition:
        raise AssertionError(name)


def client():
    return build_opener(ProxyHandler({}), HTTPCookieProcessor(CookieJar()), HTTPSHandler(context=context))


def call(opener, path, method='GET', body=None, headers=None):
    headers = dict(headers or {})
    if body is not None:
        headers['Content-Type'] = 'application/json'
    request = Request(args.base_url + path, method=method, headers=headers,
                      data=json.dumps(body).encode() if body is not None else None)
    try:
        response = opener.open(request, timeout=120)
    except HTTPError as error:
        response = error
    raw = response.read()
    payload = json.loads(raw) if 'application/json' in response.headers.get('Content-Type', '') else None
    return response.status, response.headers, payload


try:
    context = ssl.create_default_context(cafile=str(fixture / 'platform-ca.crt'))
    anonymous = client()
    check('full frontend served over trusted HTTPS', call(anonymous, '/')[0] == 200)
    status, headers, _ = call(anonymous, '/health/ready')
    check('API healthy and public simulation header', status == 200 and headers.get('X-CARBENTRA-Mode') == 'public-simulation-only')
    check('HSTS present', bool(headers.get('Strict-Transport-Security')))
    check('unauthenticated API rejected', call(anonymous, '/api/v1/campuses')[0] == 401)
    try:
        build_opener(ProxyHandler({}), HTTPSHandler(context=ssl.create_default_context())).open(args.base_url, timeout=10)
    except URLError as error:
        check('disposable CA is actually required', isinstance(error.reason, ssl.SSLCertVerificationError))
    else:
        check('disposable CA is actually required', False)
    check('development credentials rejected', call(anonymous, '/api/v1/auth/login', 'POST', {'username': 'admin', 'password': 'development-only'})[0] == 401)
    for role, username, filename in [('viewer', 'visitor', 'demo_visitor_password'),
                                     ('operator', 'simulation-operator', 'demo_operator_password')]:
        opener = client()
        status, headers, payload = call(opener, '/api/v1/auth/login', 'POST',
            {'username': username, 'password': (fixture / filename).read_text(encoding='utf-8').strip()})
        check(role + ' real hashed login', status == 200 and payload['data']['user']['role'] == role)
        cookie = headers.get('Set-Cookie', '')
        check(role + ' secure cookie', all(value in cookie for value in ('Secure', 'HttpOnly', 'SameSite=lax')))
        csrf = {'X-CSRF-Token': payload['data']['csrf_token']}
        check(role + ' campus read', call(opener, '/api/v1/campuses')[0] == 200)
        check(role + ' metadata map read', call(opener, '/api/v1/assets/manifest')[0] == 200)
        check(role + ' external ingest denied', call(opener, '/api/v1/ingest/events', 'POST', {}, csrf)[0] == 403)
        check(role + ' registry mutation denied', call(opener, '/api/v1/devices', 'POST', {}, csrf)[0] == 403)
        check(role + ' missing CSRF denied', call(opener, '/api/v1/commands', 'POST', {})[0] == 403)
        check(role + ' cross-origin write denied', call(opener, '/api/v1/commands', 'POST', {}, csrf | {'Origin': 'https://untrusted.example'})[0] == 403)
        check(role + ' command permission boundary', call(opener, '/api/v1/commands', 'POST', {}, csrf)[0] == (403 if role == 'viewer' else 422))
        check(role + ' cannot administer users', call(opener, '/api/v1/users')[0] == 403)
        check(role + ' logout requires CSRF', call(opener, '/api/v1/auth/logout', 'POST', {})[0] == 403)
        check(role + ' logout revokes session', call(opener, '/api/v1/auth/logout', 'POST', {}, csrf)[0] == 200 and call(opener, '/api/v1/campuses')[0] == 401)
    completed = True
except Exception as error:
    # Keep credential-bearing response bodies and local connection details out of
    # the artifact, while recording failures that happen between named assertions.
    failure = type(error).__name__
    raise
finally:
    args.output.write_text(json.dumps({'scope': 'disposable local public-simulation HTTPS; no physical or public deployment',
                                      'checks': checks, 'completed': completed, 'error_type': failure,
                                      'passed': completed and bool(checks) and all(row['passed'] for row in checks)}, indent=2) + '\n', encoding='utf-8')
print(f'Public simulation trusted HTTPS: {len(checks)} checks passed')
