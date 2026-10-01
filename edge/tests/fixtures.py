import json
from pathlib import Path
import struct
import hmac
from adapters import Enrollment, PlugAdapter, SwitchAdapter, PresenceAdapter, iso
from presence_auth import DOMAIN, UNKNOWN_AGE, ChallengeVerifier, authenticated_event
NOW = 1800000000.0
PLUG = Enrollment('virtual-plug-a101', 'PLUG', 'plug-wire-v2', 'SIMULATED', profile_id='lab-load')
SWITCH = Enrollment('virtual-switch-a101', 'SWITCH', 'switch-mqtt-v1', 'SIMULATED')
SENSE = Enrollment('virtual-sense-a101', 'PRESENCE', 'presence-gatt-v1', 'SIMULATED', 'AA:BB:CC:DD:EE:01', 0x12345678)
TEST_KEY = bytes(range(32))  # PUBLIC TEST FIXTURE ONLY, never a deployment key.

def plug_raw(seq=1, boot='a'*32, on=True):
    value = json.loads((Path(__file__).resolve().parents[2]/'packages/iot-contract/examples/device-telemetry-v2.json').read_text(encoding="utf-8"))
    value.update(device_id=PLUG.device_id, boot_epoch=boot, sample_seq=str(seq), desired_on=on,
        control_mode='auto', actuation_enabled=False, maintenance=False, manual_hold_until_uptime_ms='0',
        last_local_input={'channel':1,'event_seq':'0','uptime_ms':'0','pressed':False,'result':'none'})
    return value

def switch_raw(seq=1, boot='b'*32, on=False, uptime_ms=100000):
    return {'schema_version':1, 'device_type':'smart_switch', 'device_id':SWITCH.device_id, 'boot_id':boot,
        'sample_seq':str(seq), 'uptime_ms':str(uptime_ms), 'last_seq':'0', 'source_mode':'SIMULATED',
        'actuation_enabled':False, 'fault_latched':False, 'maintenance':False, 'protected_channel_mask':0,
        'channels':[{'channel':i,'channel_id':f'lighting-{i}', 'commanded_on':on, 'physically_verified_on':None,
            'feedback_quality':'unavailable_no_independent_sensor', 'control_mode':'auto', 'manual_hold_until_uptime_ms':'0'} for i in range(1,4)],
        'last_local_input':{'channel':0,'event_seq':'0','uptime_ms':'0','pressed':False,'result':'none'},
        'aggregate_meter':{'scope':'three_lighting_outputs_total','quality':'calibrated_readback','calibration_id':'TEST-FIXTURE',
            'observed_uptime_ms':str(uptime_ms),'status_bits':0,'voltage_v':230.0,'current_a':0.3,'active_power_w':60.0,
            'known_energy_wh':'123.000','energy_quality':'partial_lower_bound','persistent_storage_ok':True,'unknown_intervals':2,'checkpoint_interval_seconds':60}}

def presence_frame(seq=1, radar=2, boot=0x90abcdef, flags=208):
    return struct.pack('<BBBBIIIHHI',2,flags,radar,0,0x12345678,boot,seq,1200,3300,60)

def signed_response(nonce, seq=1, radar=2, boot=0x90abcdef, ages=(UNKNOWN_AGE,100,1500), evidence=29, key=TEST_KEY):
    body = b'\x01'+presence_frame(seq,radar,boot)+nonce+struct.pack('<III',*ages)+bytes([evidence])
    return body+hmac.digest(key,DOMAIN+body,'sha256')

def sense_event(seq=1, now=NOW, radar=2):
    verifier=ChallengeVerifier(TEST_KEY)
    nonce=verifier.challenge()
    return authenticated_event(SENSE,signed_response(nonce,seq,radar),verifier,now)

def command(device=SWITCH, now=NOW, seq=1, boot='b'*32):
    return {'schema_version':1,'id':'test-command-'+str(seq),'device_id':device.device_id,'product_family':device.product_family,
        'channel_id':'relay.1','capability':'relay.commanded','value':True,'sequence':str(seq),'issued_at':iso(now),
        'expires_at':iso(now+20),'boot_id':boot,'source_mode':device.source_mode,
        'authority':{'kind':'cloud','lease_id':'fixture-lease','lease_expires_at':iso(now+30)}}
