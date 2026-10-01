"""Create expiring, disposable localhost deployment fixtures; never production secrets."""
import argparse
from datetime import datetime, timedelta, timezone
import ipaddress
import json
from pathlib import Path
import secrets

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

parser = argparse.ArgumentParser()
parser.add_argument('--directory', type=Path, required=True)
parser.add_argument('--mqtt-port', type=int, default=8884)
parser.add_argument('--disposable-fixture', action='store_true', required=True)
args = parser.parse_args()
root = args.directory.resolve()
if root.exists() and any(root.iterdir()):
    raise SystemExit('Refusing to overwrite an existing fixture directory')
root.mkdir(parents=True, exist_ok=True, mode=0o700)


def write(name, value):
    path = root / name
    path.write_bytes(value if isinstance(value, bytes) else value.encode('utf-8'))
    # Protected containing directory; individual Compose secret mounts readable
    # by their non-root container service identities.
    path.chmod(0o444)


now = datetime.now(timezone.utc)
ca_key = ec.generate_private_key(ec.SECP256R1())
ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Disposable CARBENTRA local QA CA')])
ca = (x509.CertificateBuilder().subject_name(ca_name).issuer_name(ca_name)
      .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
      .not_valid_before(now - timedelta(minutes=1)).not_valid_after(now + timedelta(hours=4))
      .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
      .sign(ca_key, hashes.SHA256()))
for filename in ('mqtt-ca.crt', 'platform-ca.crt'):
    write(filename, ca.public_bytes(serialization.Encoding.PEM))
for name, cn, server in [('broker', 'broker', True), ('platform', 'platform-tls', True),
                         ('edge', 'edge-qa', False), ('device-01', 'VIRTUAL-QA-01', False)]:
    key = ec.generate_private_key(ec.SECP256R1())
    builder = (x509.CertificateBuilder()
               .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)]))
               .issuer_name(ca_name).public_key(key.public_key()).serial_number(x509.random_serial_number())
               .not_valid_before(now - timedelta(minutes=1)).not_valid_after(now + timedelta(hours=4))
               .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
               .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH if server
                                                    else ExtendedKeyUsageOID.CLIENT_AUTH]), critical=False))
    if server:
        builder = builder.add_extension(x509.SubjectAlternativeName([
            x509.DNSName(cn), x509.DNSName('localhost'), x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]), critical=False)
    write(name + '.crt', builder.sign(ca_key, hashes.SHA256()).public_bytes(serialization.Encoding.PEM))
    write(name + '.key', key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                         serialization.NoEncryption()))
db_password = secrets.token_urlsafe(36)
for name, value in {
    'postgres_password': secrets.token_urlsafe(36), 'database_password': db_password,
    'database_url': f'postgresql+psycopg://carbentra:{db_password}@db:5432/carbentra',
    'admin_password': secrets.token_urlsafe(36), 'adapter_token': secrets.token_urlsafe(36),
}.items():
    write(name, value + '\n')
write('devices.json', json.dumps({'enrollments': [{'device_id': 'VIRTUAL-QA-01', 'product_family': 'PLUG',
    'protocol': 'plug-wire-v2', 'source_mode': 'SIMULATED'}]}) + '\n')
write('mosquitto.acl', '''user edge-qa
topic read carbentra/v1/VIRTUAL-QA-01/telemetry
topic read carbentra/v1/VIRTUAL-QA-01/ack
topic write carbentra/v1/VIRTUAL-QA-01/receipt
topic write carbentra/v1/VIRTUAL-QA-01/time
topic write carbentra/v1/VIRTUAL-QA-01/cmd
user VIRTUAL-QA-01
topic write carbentra/v1/VIRTUAL-QA-01/telemetry
topic read carbentra/v1/VIRTUAL-QA-01/cmd
''')
write('mqtt-fixture.json', json.dumps({'fixture': 'local-development-acceptance',
    'broker_host': '127.0.0.1', 'broker_port': args.mqtt_port, 'ca': str(root / 'mqtt-ca.crt'),
    'devices': [{'id': 'VIRTUAL-QA-01', 'certificate': str(root / 'device-01.crt'), 'key': str(root / 'device-01.key')}]}, indent=2))
print('Created expiring local-only fixture; no credential values logged.')
