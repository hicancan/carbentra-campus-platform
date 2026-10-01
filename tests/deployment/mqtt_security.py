#!/usr/bin/env python3
"""Bounded raw MQTT 3.1.1 negatives against a disposable loopback TLS broker.

Raw frames verify actual server enforcement rather than a client library's local
size precheck. No valid telemetry, command or physical actuation is published.
"""
import argparse
import json
from pathlib import Path
import socket
import ssl
from uuid import uuid4

parser = argparse.ArgumentParser()
parser.add_argument('--fixture-config', type=Path, required=True)
parser.add_argument('--disposable-fixture', action='store_true', required=True)
args = parser.parse_args()
fixture = json.loads(args.fixture_config.read_text(encoding="utf-8"))
assert fixture['fixture'] == 'local-development-acceptance'
host, port = fixture['broker_host'], fixture['broker_port']
assert host in {'127.0.0.1', 'localhost', '::1'} and 1 <= port <= 65535
entry = fixture['devices'][0]
assert entry['id'].startswith('VIRTUAL-QA-')

def mqtt_string(value):
    value = value.encode()
    return len(value).to_bytes(2, 'big') + value

def packet(header, body):
    size = len(body)
    length = bytearray()
    while True:
        byte = size % 128
        size //= 128
        length.append(byte | (128 if size else 0))
        if not size:
            break
    return bytes([header]) + length + body

def context(client_certificate):
    result = ssl.create_default_context(cafile=fixture['ca'])
    if client_certificate:
        result.load_cert_chain(entry['certificate'], entry['key'])
    return result

def connect_frame():
    return packet(0x10, mqtt_string('MQTT') + b'\x04\x02\x00\x1e' + mqtt_string('qa-limit-' + uuid4().hex[:8]))

def recv_exact(stream, size):
    result = b''
    while len(result) < size:
        data = stream.recv(size - len(result))
        if not data:
            raise EOFError('Unexpected close before authenticated CONNACK')
        result += data
    return result

def positive():
    with socket.create_connection((host, port), timeout=30) as raw:
        with context(True).wrap_socket(raw, server_hostname=host) as stream:
            stream.sendall(connect_frame())
            assert recv_exact(stream, 4) == b'\x20\x02\x00\x00', 'Authenticated CONNACK failed'
            stream.sendall(b'\xe0\x00')
    return {'server_certificate_and_hostname_verified': True, 'client_certificate_accepted': True}

def certless():
    try:
        with socket.create_connection((host, port), timeout=30) as raw:
            with context(False).wrap_socket(raw, server_hostname=host) as stream:
                stream.sendall(connect_frame())
                assert not stream.recv(4), 'Broker accepted a certificate-less MQTT client'
    except ssl.SSLCertVerificationError:
        raise  # A bad server fixture must never masquerade as client-auth rejection.
    except (ssl.SSLError, ConnectionResetError):
        pass
    return {'client_certificate_required': True, 'server_verification_unchanged': True}

def oversized():
    value = packet(0x32, mqtt_string(f"carbentra/v1/{entry['id']}/telemetry") + b'\x00\x01' + b'x' * 8193)
    assert len(value) > 8192
    with socket.create_connection((host, port), timeout=30) as raw:
        with context(True).wrap_socket(raw, server_hostname=host) as stream:
            stream.sendall(connect_frame())
            assert recv_exact(stream, 4) == b'\x20\x02\x00\x00'
            try:
                stream.sendall(value)
                assert not stream.recv(4), 'Oversized packet received a response instead of disconnection'
            except ssl.SSLCertVerificationError:
                raise
            except (ssl.SSLError, ConnectionResetError, BrokenPipeError):
                pass
    return {'packet_bytes': len(value), 'payload_bytes': 8193, 'whole_packet_limit': 8192,
            'actual_wire_publish_attempted': True, 'broker_disconnected_authenticated_client': True}

checks = []
for name, fn in [('verified_mutual_tls_connection', positive), ('missing_client_certificate_rejected', certless), ('oversized_packet_rejected', oversized)]:
    try:
        checks.append({'check': name, 'status': 'passed', 'detail': fn()})
    except Exception as exc:
        checks.append({'check': name, 'status': 'failed', 'error_type': type(exc).__name__, 'error': str(exc)})
        if name == 'verified_mutual_tls_connection':
            break
result = {'checks': checks, 'passed': sum(x['status'] == 'passed' for x in checks),
          'failed': sum(x['status'] == 'failed' for x in checks), 'physical_dispatch': False, 'fixture_only': True}
print(json.dumps(result, indent=2))
raise SystemExit(bool(result['failed']))
