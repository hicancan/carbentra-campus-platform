"""Optional actual Bleak/BlueZ advertisement listener, radio OFF unless requested.

No connection, pairing, enrollment, key generation, or sensor configuration occurs.
Manufacturer data remains unauthenticated evidence regardless of enrollment.
"""
from __future__ import annotations
import asyncio
import sqlite3
import time
from ingress import Ingress
from store import EdgeStore


async def scan(database, enrollments, stop, adapter=None, scanner_factory=None):
    if scanner_factory is None:
        from bleak import BleakScanner
        scanner_factory = BleakScanner
    store = EdgeStore(database)
    ingress = Ingress(store, enrollments)
    queue = asyncio.Queue(maxsize=256)
    dropped = 0
    gatt_tasks = {}
    last_gatt_attempt = {}
    allowed = {e.ble_address.lower() for e in enrollments if e.ble_address and e.source_mode == 'REAL'}
    if not allowed:
        store.close()
        raise ValueError('BLE scanning requires explicitly enrolled REAL sensor addresses')

    def detected(device, advertisement):
        nonlocal dropped
        if device.address.lower() not in allowed:
            return
        # Copy immutable bytes from the transport callback; do not retain library objects.
        item = (device.address, {key: bytes(value) for key, value in advertisement.manufacturer_data.items()}, time.time())
        try:
            queue.put_nowait(item)
        except asyncio.QueueFull:
            dropped += 1

    options = {'detection_callback': detected}
    if adapter:
        options['bluez'] = {'adapter': adapter}
    try:
        async with scanner_factory(**options):
            store.health('ble', {'status': 'scanning', 'dropped': dropped, 'authenticated': False})
            while not stop.is_set():
                try:
                    address, data, now = await asyncio.wait_for(queue.get(), timeout=0.25)
                except asyncio.TimeoutError:
                    continue
                try:
                    ingress.ble(address, data, now)
                    enrollment = next(e for e in enrollments if e.ble_address and e.ble_address.lower() == address.lower())
                    if enrollment.protocol == 'presence-gatt-v1' and enrollment.auth_key_file:
                        previous = gatt_tasks.get(enrollment.device_id)
                        if previous is not None and previous.done():
                            try:
                                previous.result()
                            except Exception:
                                pass  # The authenticated client already persisted its health failure.
                        if (previous is None or previous.done()) and time.monotonic() - last_gatt_attempt.get(enrollment.device_id, -10) >= 2:
                            from presence_auth import fetch_authenticated
                            last_gatt_attempt[enrollment.device_id] = time.monotonic()
                            gatt_tasks[enrollment.device_id] = asyncio.create_task(fetch_authenticated(enrollment, database))
                except (ValueError, sqlite3.Error) as error:
                    store.health('ble:last_rejection', {'error': type(error).__name__, 'dropped': dropped})
                finally:
                    queue.task_done()
    except Exception as error:
        store.health('ble', {'status': 'unavailable', 'error': type(error).__name__, 'dropped': dropped, 'authenticated': False})
        raise
    finally:
        for task in gatt_tasks.values():
            task.cancel()
        if gatt_tasks:
            await asyncio.gather(*gatt_tasks.values(), return_exceptions=True)
        store.close()
