import json
import unittest
from dataclasses import replace
from ingress import Ingress
from store import EdgeStore
from virtual_bridge import VirtualRoom

class VirtualBridgeTests(unittest.TestCase):
    def test_three_families_multiple_rooms_same_ingress(self):
        rooms=[VirtualRoom('a101'),VirtualRoom('a102')]
        devices=[]
        for i,room in enumerate(rooms):
            devices += [replace(e,ble_address=f'AA:BB:CC:DD:EE:{i+1:02X}') if e.ble_address else e for e in room.enrollments]
        store=EdgeStore(':memory:');ingress=Ingress(store,devices)
        try:
            for room in rooms:
                for topic,payload in room.messages():ingress.mqtt(topic,json.dumps(payload))
            self.assertEqual(store.status()['outbox_pending'],6)
            for e in devices:
                snapshot=store.snapshot(e.device_id)
                self.assertEqual(snapshot['event']['source_mode'],'SIMULATED')
            with self.assertRaises(ValueError):
                topic,payload=rooms[0].messages()[-1];payload['source_mode']='REAL';ingress.mqtt(topic,json.dumps(payload))
        finally:store.close()
