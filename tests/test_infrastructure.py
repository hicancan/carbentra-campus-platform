"""Static deployment safety checks; these do not claim Docker runtime verification."""
from pathlib import Path
import subprocess
import sys
import tomllib
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]


class DeploymentContractTests(unittest.TestCase):
    def setUp(self):
        self.dev = yaml.safe_load((ROOT / 'compose.yaml').read_text(encoding="utf-8"))
        self.prod = yaml.safe_load((ROOT / 'compose.prod.yaml').read_text(encoding="utf-8"))

    def test_only_web_has_loopback_published_port(self):
        for compose in [self.dev, self.prod]:
            for name, service in compose['services'].items():
                if name == 'web':
                    self.assertEqual(service['ports'], ['127.0.0.1:8080:8080'])
                else:
                    self.assertNotIn('ports', service)
            self.assertIs(compose['networks']['private']['internal'], True)
            self.assertEqual(compose['services']['web']['networks'], ['private', 'ingress'])
            for name in ['db', 'api', 'worker', 'analysis', 'migrate']:
                self.assertEqual(compose['services'][name]['networks'], ['private'])

    def test_app_hardening_and_no_host_access(self):
        for compose in [self.dev, self.prod]:
            for name in ['api', 'worker', 'analysis', 'web', 'migrate']:
                service = compose['services'][name]
                self.assertIs(service['read_only'], True)
                self.assertIn('ALL', service['cap_drop'])
                self.assertEqual(len(service['tmpfs']), 1)
                self.assertTrue(service['tmpfs'][0].startswith('/tmp:'))
                self.assertIn('noexec,nosuid', service['tmpfs'][0])
                self.assertIn('no-new-privileges:true', service['security_opt'])
                self.assertNotIn('privileged', service)
                self.assertNotIn('network_mode', service)
                self.assertNotIn('pid', service)
                self.assertNotIn('devices', service)
                self.assertNotIn('/var/run/docker.sock', str(service))

    def test_production_fail_closed_flags(self):
        env = self.prod['services']['api']['environment']
        self.assertEqual(env['CARBENTRA_ENV'], 'production')
        for key in ['DEV_AUTH', 'AUTO_MIGRATE', 'SEED_DEMO', 'SIMULATION_ENABLED']:
            self.assertEqual(env['CARBENTRA_' + key], 'false')
        self.assertEqual(env['CARBENTRA_COOKIE_SECURE'], 'true')
        self.assertEqual(env['CARBENTRA_PHYSICAL_DISPATCH_ENABLED'], 'false')
        self.assertEqual(env['CARBENTRA_PHYSICAL_RELEASE_IDS'], '[]')
        self.assertIn('CARBENTRA_DATABASE_URL_FILE', env)
        self.assertNotIn('CARBENTRA_DATABASE_URL', env)
        self.assertNotIn('CARBENTRA_ADMIN_PASSWORD_FILE', env)
        self.assertNotIn('development-', str(self.prod))

    def test_migration_and_readiness_order(self):
        for compose in [self.dev, self.prod]:
            services = compose['services']
            self.assertEqual(services['migrate']['depends_on']['db']['condition'], 'service_healthy')
            self.assertEqual(services['api']['depends_on']['migrate']['condition'], 'service_completed_successfully')
            self.assertEqual(services['worker']['depends_on']['api']['condition'], 'service_healthy')
            for name in ['db', 'api', 'worker', 'analysis', 'web']:
                self.assertIn('healthcheck', services[name])
            self.assertEqual(services['worker']['healthcheck']['test'], ['CMD', 'python', '-m', 'app.worker_health'])
            self.assertEqual(services['analysis']['command'], ['python', '-m', 'app.worker', '--role', 'analysis'])
            self.assertEqual(services['analysis']['healthcheck']['test'], ['CMD', 'python', '-m', 'app.worker_health', '--role', 'analysis'])
            self.assertEqual(services['analysis']['depends_on']['api']['condition'], 'service_healthy')
            self.assertNotIn('CARBENTRA_ADMIN_PASSWORD_FILE', services['analysis']['environment'])

    def test_images_and_dependencies_are_pinned(self):
        for compose in [self.dev, self.prod]:
            self.assertIn('@sha256:', compose['services']['db']['image'])
        for path in ['backend/Dockerfile', 'frontend/Dockerfile']:
            text = (ROOT / path).read_text(encoding="utf-8")
            for line in text.splitlines():
                if line.startswith('ARG ') and '_IMAGE=' in line:
                    self.assertIn('@sha256:', line)
            self.assertIn('USER ', text)
        lock = tomllib.loads((ROOT / 'uv.lock').read_text(encoding='utf-8'))
        self.assertTrue(lock['package'])
        for package in lock['package']:
            self.assertTrue(package['version'])
            if 'registry' in package['source']:
                for artifact in [*package.get('wheels', []), *([package['sdist']] if 'sdist' in package else [])]:
                    self.assertTrue(artifact['hash'].startswith('sha256:'))
        self.assertIn('uv sync --locked --no-dev', (ROOT / 'backend/Dockerfile').read_text(encoding='utf-8'))
        self.assertTrue((ROOT / 'frontend/package-lock.json').is_file())
        self.assertIn('COPY --chown=10001:10001 packages/product/dist/', (ROOT / 'backend/Dockerfile').read_text(encoding="utf-8"))
        ignore = (ROOT / '.dockerignore').read_text(encoding="utf-8")
        self.assertIn('backend/tests', ignore)
        self.assertIn('COPY --chown=10001:10001 packages/spatial/dist/', (ROOT / 'backend/Dockerfile').read_text(encoding="utf-8"))
        self.assertLess(ignore.index('!packages/product/dist/**'), ignore.index('**/*.key'))
        nginx = (ROOT / 'infra/nginx.conf').read_text(encoding="utf-8")
        self.assertIn('gzip_types model/gltf-binary;', nginx)
        self.assertIn('gzip_vary on;', nginx)
        self.assertNotIn('application/json;', nginx)

    def test_transport_is_opt_in_and_physical_dispatch_off(self):
        compose = yaml.safe_load((ROOT / 'compose.transport.yaml').read_text(encoding="utf-8"))
        for name in ['broker', 'edge', 'platform-tls']:
            service = compose['services'][name]
            self.assertEqual(service['profiles'], ['transport'])
            self.assertIs(service['read_only'], True)
            self.assertIn('ALL', service['cap_drop'])
        edge = compose['services']['edge']
        self.assertNotIn('--enable-virtual-commands', edge['command'])
        self.assertEqual(edge['environment']['CARBENTRA_ENABLE_PHYSICAL_DISPATCH'], 'false')
        self.assertEqual(edge['environment']['CARBENTRA_PHYSICAL_RELEASES_JSON'], '{}')
        self.assertIn('https://platform-tls:8443', edge['command'])
        self.assertNotIn('additional_contexts', edge['build'])
        self.assertEqual(edge['build']['context'], '.')
        self.assertEqual(edge['build']['dockerfile'], 'infra/edge.Dockerfile')
        self.assertEqual(edge['depends_on']['platform-tls']['condition'], 'service_healthy')
        self.assertIn('healthcheck', compose['services']['platform-tls'])
        config = (ROOT / 'infra/nginx-transport.conf').read_text(encoding="utf-8")
        for name in ['client_body', 'proxy', 'fastcgi', 'uwsgi', 'scgi']:
            self.assertIn(name + '_temp_path /tmp/', config)
        self.assertEqual(edge['networks'], ['transport'])
        self.assertEqual(compose['services']['broker']['user'], '1883:1883')
        self.assertEqual(compose['services']['broker']['entrypoint'], ['sh', '/etc/carbentra/mosquitto-entrypoint.sh'])
        script = (ROOT / 'infra/mosquitto-entrypoint.sh').read_text(encoding="utf-8")
        self.assertIn('umask 077', script)
        self.assertIn('chmod 0700', script)
        self.assertIn('chmod 0600', script)
        self.assertNotIn('chown', script)
        self.assertEqual(compose['services']['broker']['ports'], ['127.0.0.1:18883:8883'])
        self.assertIs(compose['networks']['transport']['internal'], True)

    def test_broker_config_requires_per_certificate_auth(self):
        config = (ROOT / 'infra/mosquitto.conf').read_text(encoding="utf-8")
        for directive in ['require_certificate true', 'use_identity_as_username true', 'allow_anonymous false', 'retain_available false', 'max_packet_size 8192']:
            self.assertIn(directive, config)
        self.assertNotIn('message_size_limit ', config)
        acl = (ROOT / 'infra/mosquitto.acl.example').read_text(encoding="utf-8")
        permissions = [line for line in acl.splitlines() if line.startswith('topic ')]
        self.assertTrue(permissions)
        self.assertTrue(all('#' not in line and '+' not in line for line in permissions))

    def test_entrypoint_rejects_missing_or_ambiguous_secrets(self):
        import os
        import tempfile
        script = str(ROOT / 'infra/container-entrypoint.py')
        with tempfile.TemporaryDirectory() as temp:
            secret = Path(temp) / 'secret'
            secret.write_text('test-only-one-line-secret\n', encoding="utf-8")
            env = dict(os.environ, CARBENTRA_ADMIN_PASSWORD_FILE=str(secret))
            env.pop('CARBENTRA_ADMIN_PASSWORD', None)
            result = subprocess.run([sys.executable, script, sys.executable, '-c',
                "import os; assert os.environ['CARBENTRA_ADMIN_PASSWORD'] == 'test-only-one-line-secret'; assert 'CARBENTRA_ADMIN_PASSWORD_FILE' not in os.environ"], env=env, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            env['CARBENTRA_ADMIN_PASSWORD'] = 'other-value'
            result = subprocess.run([sys.executable, script, 'true'], env=env, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn(b'test-only-one-line-secret', result.stderr)
            self.assertNotIn(b'other-value', result.stderr)
            del env['CARBENTRA_ADMIN_PASSWORD']
            secret.write_text('', encoding="utf-8")
            result = subprocess.run([sys.executable, script, 'true'], env=env, capture_output=True)
            self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
