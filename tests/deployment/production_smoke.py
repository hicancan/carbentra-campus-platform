#!/usr/bin/env python3
"""HTTPS and session checks against an explicitly disposable local production-mode fixture."""
import argparse
from http.cookiejar import CookieJar
import json
from pathlib import Path
import ssl
import socket
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import build_opener, HTTPCookieProcessor, HTTPSHandler, Request, ProxyHandler

parser = argparse.ArgumentParser()
parser.add_argument('--base-url', default='https://localhost:8443')
parser.add_argument('--cleartext-url', default='http://localhost:8080')
parser.add_argument('--ca-file', required=True)
parser.add_argument('--password-file', required=True)
parser.add_argument('--username', default='container-test-admin')
parser.add_argument('--disposable-fixture', action='store_true', required=True)
args = parser.parse_args()
for url in [args.base_url, args.cleartext_url]:
    parsed = urlparse(url)
    if parsed.hostname not in {'localhost', '127.0.0.1', '::1'} or parsed.username or parsed.password:
        raise SystemExit('Only loopback test fixtures are allowed')
if urlparse(args.base_url).scheme != 'https' or urlparse(args.cleartext_url).scheme != 'http':
    raise SystemExit('Expected HTTPS fixture and HTTP secure-cookie probe')
if not args.username.startswith('container-test-'):
    raise SystemExit('A container-test- fixture administrator is required')
password = Path(args.password_file).read_text(encoding="utf-8").strip()
jar = CookieJar()
client = build_opener(ProxyHandler({}), HTTPCookieProcessor(jar), HTTPSHandler(context=ssl.create_default_context(cafile=args.ca_file)))


def call(path, method='GET', body=None, headers=None, base=None):
    headers = dict(headers or {})
    if body is not None:
        headers['Content-Type'] = 'application/json'
    req = Request((base or args.base_url) + path, data=json.dumps(body).encode() if body is not None else None, headers=headers, method=method)
    try:
        response = client.open(req, timeout=120)
    except HTTPError as exc:
        response = exc
    raw = response.read()
    try:
        data = json.loads(raw)
    except ValueError:
        data = None
    return response.status, data, response.headers


results = []
def passed(name):
    results.append(name)
    print(json.dumps({'check': name, 'status': 'passed'}), flush=True)

# Validate certificate failures before any fixture password is sent.
parsed_tls = urlparse(args.base_url)
for label, context, server_name in [
    ('untrusted_fixture_certificate_rejected', ssl.create_default_context(), parsed_tls.hostname),
    ('wrong_tls_hostname_rejected', ssl.create_default_context(cafile=args.ca_file), 'wrong-host.invalid'),
]:
    try:
        with socket.create_connection((parsed_tls.hostname, parsed_tls.port or 443), timeout=120) as raw:
            with context.wrap_socket(raw, server_hostname=server_name):
                pass
    except ssl.SSLCertVerificationError:
        passed(label)
    else:
        raise AssertionError(label + ': certificate unexpectedly accepted')

status, _, _ = call('/api/v1/auth/login', 'POST', {'username': 'admin', 'password': 'development-only'})
assert status == 401, status
passed('development_fixture_credentials_rejected')
status, data, headers = call('/api/v1/auth/login', 'POST', {'username': args.username, 'password': password})
assert status == 200, (status, data)
csrf = data['data']['csrf_token']
cookies = headers.get_all('Set-Cookie')
assert cookies and all('secure' in x.lower() and 'httponly' in x.lower() and 'samesite=lax' in x.lower() for x in cookies)
assert all(cookie.secure for cookie in jar)
# Retain only in memory to verify server-side revocation, never print the value.
session_cookie = '; '.join(f'{cookie.name}={cookie.value}' for cookie in jar)
assert headers.get('Strict-Transport-Security')
assert call('/api/v1/auth/me')[0] == 200
passed('verified_https_login_secure_httponly_samesite_cookie_hsts')
assert call('/api/v1/auth/me', base=args.cleartext_url)[0] == 401
passed('secure_session_not_sent_over_cleartext')
status, status_data, _ = call('/api/v1/system/status')
assert status == 200
state = status_data['data']
assert state['mode'] == 'production', state
assert state['database']['dialect'] == 'postgresql'
assert state['physical_control']['enabled'] is False
assert state['simulation']['enabled'] is False
status, devices, _ = call('/api/v1/devices')
assert status == 200 and devices['meta']['total'] == 0
for path in ['/api/v1/tariffs', '/api/v1/carbon/factors']:
    code, payload, _ = call(path)
    assert code == 200 and payload['data'] == [], (path, code, payload)
passed('production_postgresql_empty_registry_no_synthetic_prices_no_simulation_no_physical_control')
assert call('/api/v1/settings', 'PATCH', {'stale_after_seconds': 120})[0] == 403
assert call('/api/v1/settings', 'PATCH', {'stale_after_seconds': 120}, {'X-CSRF-Token': csrf, 'Origin': 'https://attacker.invalid'})[0] == 403
assert call('/api/v1/settings', 'PATCH', {'stale_after_seconds': 120}, {'X-CSRF-Token': csrf, 'Origin': args.base_url})[0] == 200
passed('csrf_and_explicit_https_origin_enforced')
assert call('/api/v1/auth/logout', 'POST', {}, {'X-CSRF-Token': csrf, 'Origin': args.base_url})[0] == 200
assert call('/api/v1/auth/me')[0] == 401
assert call('/api/v1/auth/me', headers={'Cookie': session_cookie})[0] == 401
passed('production_session_revoked_on_logout_and_cookie_replay_rejected')
print(json.dumps({'passed': len(results), 'failed': 0, 'fixture_only': True}))
