"""Static public-demo packaging assertions, never a Docker cold-start claim."""
from pathlib import Path
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_standalone_public_demo_is_isolated_and_bounded():
    compose = yaml.safe_load((ROOT / "compose.public-demo.yaml").read_text())
    services = compose["services"]
    assert set(services) == {"db", "migrate", "demo-init", "api", "worker", "analysis", "web", "gateway"}
    for name, service in services.items():
        assert service["cpus"] > 0 and service["mem_limit"] and service["pids_limit"]
        assert service["logging"]["options"]["max-file"] == "2"
        assert "privileged" not in service and "network_mode" not in service
        assert "devices" not in service and "/var/run/docker.sock" not in str(service)
        if name != "gateway":
            assert "ports" not in service
            assert service["networks"] == ["private"]
        if name != "db":
            assert service["read_only"] and service["cap_drop"] == ["ALL"]
    assert compose["networks"]["private"]["internal"]
    import ipaddress
    addressing = compose['networks']['private']['ipam']['config'][0]
    def resolved(value):
        return value.replace('${CARBENTRA_DEMO_NETWORK_PREFIX:-172.30.88}', '172.30.88')
    subnet = ipaddress.ip_network(resolved(addressing['subnet']))
    dynamic = ipaddress.ip_network(resolved(addressing['ip_range']))
    gateway = ipaddress.ip_address(resolved(services['gateway']['networks']['private']['ipv4_address']))
    assert dynamic.subnet_of(subnet) and gateway in subnet and gateway not in dynamic
    assert "carbentra-public-demo-${CARBENTRA_PUBLIC_DEMO_ID" in compose["name"]
    assert all("127.0.0.1" in port for port in services["gateway"]["ports"])
    assert services["db"]["environment"]["POSTGRES_DB"] == "carbentra_public_demo"
    for name in ("api", "worker", "analysis", "migrate", "demo-init"):
        env = services[name]["environment"]
        assert env["CARBENTRA_ENV"] == "production"
        assert env["CARBENTRA_DEPLOYMENT_MODE"] == "public_simulation"
        assert env["CARBENTRA_COOKIE_SECURE"] == "true"
        assert env["CARBENTRA_SIMULATION_ENABLED"] == "true"
        for key in ("DEV_AUTH", "SEED_DEMO", "AUTO_MIGRATE", "PHYSICAL_DISPATCH_ENABLED", "WORKER_ENABLED"):
            assert env[f"CARBENTRA_{key}"] == "false"
        assert env["CARBENTRA_PHYSICAL_RELEASE_IDS"] == "[]"
        assert env["CARBENTRA_ADAPTER_ALLOWED_DEVICE_IDS"] == "[]"
        assert "CARBENTRA_ADAPTER_TOKEN" not in env
        assert services[name]["command"][:3] == ["python", "-m", "app.public_demo"]
        if name != "demo-init":
            assert services[name]["secrets"] == ["database_url"]
            assert not any("PASSWORD" in key for key in env)
    assert services["migrate"]["depends_on"]["db"]["condition"] == "service_healthy"
    assert services["demo-init"]["depends_on"]["migrate"]["condition"] == "service_completed_successfully"
    assert services["api"]["depends_on"]["demo-init"]["condition"] == "service_completed_successfully"
    for name in ("worker", "analysis"):
        assert services[name]["depends_on"]["api"]["condition"] == "service_healthy"
    for name in ("db", "gateway"):
        assert "@sha256:" in services[name]["image"]


def test_gateway_tls_forwarding_limits_and_no_transport():
    config = (ROOT / "infra/public-demo/nginx.conf.template").read_text()
    assert "ssl_protocols TLSv1.2 TLSv1.3;" in config
    assert "ssl_reject_handshake on;" in config
    assert "proxy_set_header X-Forwarded-For $remote_addr;" in config
    assert "$proxy_add_x_forwarded_for" not in config
    assert "Strict-Transport-Security" in config
    assert "location ^~ /api/v1/ingest/ { return 403; }" in config
    assert "location ^~ /api/v1/adapter/ { return 403; }" in config
    assert "zone=login_total" in config and "limit_conn connections 16;" in config
    assert "access_log off;" in config
    assert "CARBENTRA-Mode 'public-simulation-only'" in config
    bootstrap = (ROOT / "infra/public-demo/postgres-init.sh").read_text()
    assert "COMMENT ON DATABASE carbentra_public_demo" in bootstrap
    assert "NOSUPERUSER NOCREATEDB NOCREATEROLE" in bootstrap
    assert "REVOKE ALL ON DATABASE carbentra_public_demo FROM PUBLIC" in bootstrap


def test_public_demo_checks_are_in_default_ci_and_local_verification():
    import tomllib
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert "tests/test_public_demo_deployment.py" in project["tool"]["pytest"]["ini_options"]["testpaths"]
    for filename in (".github/workflows/verify.yml", "tools/verify-local.ps1"):
        content = (ROOT / filename).read_text()
        assert "tests/test_public_demo_deployment.py" in content
        assert "public-demo-test-database.py" in content
        assert "CARBENTRA_PUBLIC_DEMO_TEST_DATABASE_URL" in content
    bootstrap = (ROOT / "infra/public-demo/postgres-init.sh").read_text()
    assert "--set=app_password" not in bootstrap
    assert "\\getenv app_password CARBENTRA_INIT_DB_PASSWORD" in bootstrap


def test_secret_helper_is_exclusive_external_and_private(tmp_path):
    import importlib.util
    import os
    import stat
    import pytest
    spec = importlib.util.spec_from_file_location("demo_secrets", ROOT / "tools/public-demo-secrets.py")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    if os.name != 'posix':
        with pytest.raises(ValueError, match='POSIX permission enforcement'):
            helper.provision(tmp_path / 'test-only-secrets')
        assert not (tmp_path / 'test-only-secrets').exists()
        return
    directory = helper.provision(tmp_path / "test-only-secrets")
    assert stat.S_IMODE(directory.stat().st_mode) == 0o700
    assert len(list(directory.iterdir())) == 6
    values = {path.name: path.read_text().strip() for path in directory.iterdir()}
    assert len(set(values.values())) == 6
    assert all(stat.S_IMODE(path.stat().st_mode) == 0o444 for path in directory.iterdir())
    assert values["database_password"] in values["database_url"]
    with pytest.raises(FileExistsError):
        helper.provision(directory)
    with pytest.raises(ValueError, match="outside"):
        helper.provision(ROOT / "forbidden-test-secrets")


@pytest.mark.parametrize('failure', ['network', 'malformed_json'])
def test_public_demo_smoke_partial_execution_never_reports_passed(tmp_path, monkeypatch, failure):
    import json
    import runpy
    import ssl
    import sys
    from types import SimpleNamespace
    from urllib.error import URLError
    import urllib.request
    output = tmp_path / 'partial-smoke.json'
    calls = []
    class Opener:
        def open(self, request, timeout=None):
            calls.append(request.full_url)
            if len(calls) == 1:
                return SimpleNamespace(status=200, headers={'Content-Type': 'text/html'}, read=lambda: b'<html>fixture</html>')
            if failure == 'network':
                raise URLError('synthetic connection failure')
            return SimpleNamespace(status=200, headers={'Content-Type': 'application/json'}, read=lambda: b'not-json')
    monkeypatch.setattr(urllib.request, 'build_opener', lambda *_: Opener())
    monkeypatch.setattr(ssl, 'create_default_context', lambda **_: None)
    monkeypatch.setattr(sys, 'argv', ['public_demo_smoke.py', '--base-url', 'https://localhost:18444',
        '--fixture-directory', str(tmp_path), '--output', str(output), '--disposable-fixture'])
    with pytest.raises((URLError, json.JSONDecodeError)):
        runpy.run_path(str(ROOT / 'tests/deployment/public_demo_smoke.py'), run_name='__main__')
    result = json.loads(output.read_text(encoding='utf-8'))
    assert len(result['checks']) == 1 and result['checks'][0]['passed']
    assert result['completed'] is False and result['passed'] is False
    assert result['error_type'] in {'URLError', 'JSONDecodeError'}
