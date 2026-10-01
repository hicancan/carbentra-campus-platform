"""CARBENTRA unified enrolled-device gateway. Actual dispatch defaults OFF."""
from __future__ import annotations
import argparse
import asyncio
import json
import os
from pathlib import Path
import signal
import sqlite3
import ssl
import threading
import time
from adapters import descriptor
from config import enrollments
from ingress import Ingress
from service import strict_json
from store import EdgeStore


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('broker', 'ca', 'certificate', 'key', 'devices', 'database'):
        p.add_argument('--' + name, required=True)
    p.add_argument('--port', type=int, default=8883)
    p.add_argument('--client-id', default='carbentra-building-edge')
    p.add_argument('--platform-url')
    p.add_argument('--enable-virtual-commands', action='store_true')
    p.add_argument('--enable-ble', action='store_true', help='Explicitly start enrolled-device scan; requires BlueZ/D-Bus and actual radio')
    p.add_argument('--ble-adapter', help='Optional BlueZ adapter name, e.g. hci0')
    p.add_argument('--rules', help='Operator-provisioned bounded local rule bundle; evaluated only by default')
    p.add_argument('--enable-local-rules', action='store_true', help='Dispatch authorized rule candidates; independent virtual/physical gates still apply')
    p.add_argument('--export-descriptors', help='Write enrolled capability descriptors here and exit, without starting transports')
    args = p.parse_args(argv)
    configuration = strict_json(Path(args.devices).read_bytes(), maximum=65536)
    try:
        devices = enrollments(configuration)
    except (TypeError, ValueError) as error:
        p.error(str(error))
    if args.export_descriptors:
        Path(args.export_descriptors).write_text(json.dumps([descriptor(e) for e in devices], ensure_ascii=False, indent=2) + '\n', encoding="utf-8")
        return
    flag = os.environ.get('CARBENTRA_ENABLE_PHYSICAL_DISPATCH', 'false')
    if flag not in {'true', 'false'}:
        p.error('CARBENTRA_ENABLE_PHYSICAL_DISPATCH must be exactly true or false')
    physical = flag == 'true'
    releases = strict_json(os.environ.get('CARBENTRA_PHYSICAL_RELEASES_JSON', '{}'))
    if not isinstance(releases, dict):
        p.error('physical releases must be an explicit per-device object')
    if (args.enable_virtual_commands or physical) and not args.platform_url:
        p.error('command transport requires authenticated platform configuration')
    if args.enable_ble:
        from presence_auth import load_key
        for e in devices:
            if e.protocol == 'presence-gatt-v1':
                load_key(e.auth_key_file)  # Fail startup rather than silently downgrade trusted enrollment.
    import paho.mqtt.client as mqtt
    store = EdgeStore(args.database)
    from migrations import migrate_legacy_outbox
    migration = migrate_legacy_outbox(store, devices)
    if migration.get('quarantined'):
        print('Legacy migration retained quarantined rows for operator review:', migration['quarantined'], flush=True)
    ingress = Ingress(store, devices)
    stop = threading.Event()
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=args.client_id, clean_session=True)
    client.tls_set(ca_certs=args.ca, certfile=args.certificate, keyfile=args.key, tls_version=ssl.PROTOCOL_TLS_CLIENT)
    client.tls_insecure_set(False)
    client.reconnect_delay_set(min_delay=1, max_delay=30)

    def publish(topic, payload):
        if not client.is_connected():
            return False
        result = client.publish(topic, payload, qos=1, retain=False)
        result.wait_for_publish(timeout=5)
        return result.rc == mqtt.MQTT_ERR_SUCCESS and result.is_published()

    def on_connect(c, userdata, flags, reason, properties):
        if reason != 0:
            return
        for topic in ingress.topics():
            c.subscribe(topic, qos=1)
        store.health('mqtt', {'connected': True, 'reconciliation': 'fresh_observations_required_no_desired_state_replay'})

    def on_disconnect(c, userdata, flags, reason, properties):
        store.health('mqtt', {'connected': False})

    def on_message(c, userdata, msg):
        try:
            result = ingress.mqtt(msg.topic, msg.payload, msg.retain)
            if result:
                c.publish(result[0], json.dumps(result[1], separators=(',', ':')), qos=1, retain=False)
        except (ValueError, UnicodeError, json.JSONDecodeError, sqlite3.Error) as error:
            store.health('mqtt:last_rejection', {'error': type(error).__name__})
            print('Rejected device payload:', type(error).__name__, flush=True)

    client.on_connect, client.on_disconnect, client.on_message = on_connect, on_disconnect, on_message
    threads = []
    if args.platform_url:
        from platform_forwarder import Forwarder
        from platform_http import PlatformHTTP
        token = os.environ.get('CARBENTRA_ADAPTER_TOKEN', '')
        forwarder = Forwarder(args.database, args.platform_url, token)
        def forward():
            while not stop.is_set():
                try:
                    if forwarder.once() and forwarder.last_attempt_succeeded:
                        continue
                except sqlite3.Error:
                    pass
                stop.wait(.2)
        threads.append(threading.Thread(target=forward, name='canonical-outbox', daemon=True))
        if args.enable_virtual_commands or physical:
            from command_transport import CommandTransport
            from channel_transport import ChannelTransport
            from leased_dispatcher import LeasedDispatcher
            # One backend lease stream; concrete Plug wire and typed Switch
            # commands route through their actual protocol adapters.
            plugs = [e for e in devices if e.product_family == 'PLUG']
            transport = CommandTransport(args.database, [e.device_id for e in plugs],
                [e.device_id for e in plugs if e.source_mode == 'SIMULATED'] if args.enable_virtual_commands else [],
                publish, http=PlatformHTTP(args.platform_url, token), ready=client.is_connected,
                physical_enabled=physical and bool({e.device_id for e in plugs} & set(releases)),
                physical_releases={e.device_id: releases[e.device_id] for e in plugs if e.device_id in releases})
            channel_transport = ChannelTransport(args.database, devices, publish, enable_virtual=args.enable_virtual_commands, physical_enabled=physical, physical_releases=releases)
            dispatcher = LeasedDispatcher(PlatformHTTP(args.platform_url, token), transport, channel_transport, client.is_connected)
            def commands():
                while not stop.is_set():
                    try:
                        dispatcher.once()
                    except (ValueError, OSError, sqlite3.Error):
                        pass
                    stop.wait(1)
            threads.append(threading.Thread(target=commands, name='typed-lease-inbox', daemon=True))
    if args.rules or args.enable_local_rules:
        from rules import RuleEngine
        from channel_transport import ChannelTransport
        engine = RuleEngine(args.database)
        if args.rules:
            engine.install(strict_json(Path(args.rules).read_bytes(), maximum=65536))
        local_transport = ChannelTransport(args.database, devices, publish,
            enable_virtual=args.enable_virtual_commands, physical_enabled=physical, physical_releases=releases)
        def rules():
            while not stop.is_set():
                try:
                    candidates = engine.once(connected=False)
                    if args.enable_local_rules and client.is_connected():
                        for candidate in candidates:
                            if candidate['command']:
                                local_transport.process(candidate['command'])
                except (ValueError, OSError, sqlite3.Error):
                    pass
                stop.wait(1)
        threads.append(threading.Thread(target=rules, name='bounded-local-rules', daemon=True))
    if args.enable_ble:
        from ble_scanner import scan
        def ble():
            try:
                asyncio.run(scan(args.database, devices, stop, adapter=args.ble_adapter))
            except Exception as error:
                print('BLE unavailable:', type(error).__name__, flush=True)
        threads.append(threading.Thread(target=ble, name='enrolled-ble-input', daemon=True))
    def terminate(*_):
        stop.set()
        client.disconnect()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, terminate)
    try:
        for thread in threads:
            thread.start()
        client.connect(args.broker, args.port, keepalive=30)
        client.loop_forever(retry_first_connection=True)
    finally:
        stop.set()
        for thread in threads:
            thread.join(timeout=7)
        store.close()


if __name__ == '__main__':
    main()
