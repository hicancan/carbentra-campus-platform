"""Canonical device wire v2 gate. Units and quality are checked before durable receipt.
This layer does not bind assets, infer savings, or normalize away raw evidence.
"""
import json
from pathlib import Path
from jsonschema import Draft202012Validator
import math
import re

ID = re.compile(r'^[A-Za-z0-9_-]{1,47}$')
EPOCH = re.compile(r'^[0-9a-f]{32}$')
SEQUENCE = re.compile(r'^[1-9][0-9]{0,19}$')
BOARD = 'CARBENTRA-P16-EVT-B'
from . import SCHEMAS as APPLICATION_SCHEMAS
CONTRACTS=APPLICATION_SCHEMAS/'wire'
SCHEMAS={name:Draft202012Validator(json.loads((CONTRACTS/name).read_text(encoding="utf-8"))) for name in ['device-wire-v2.schema.json','device-ack-v2.schema.json']}

def schema_gate(name,message):
    if not SCHEMAS[name].is_valid(message):raise ValueError('wire schema violation')
SENSING = {'AC_PRESENT', 'NO_AC_PULSES_DETECTED', 'PRESENT_OR_STUCK_LOW_FAULT', 'UNKNOWN'}
INTERMEDIATE = {'REQUESTED_AWAITING_FEEDBACK', 'ACCEPTED_NO_CHANGE'}
OBSERVED = {'OBSERVED_VERIFIED', 'FAILED_FEEDBACK', 'TIMED_OUT', 'FAILED_SUPERSEDED'}
REJECTIONS = {'DUPLICATE','LOCAL_TRIP','OFFLINE_HOLD','NO_AUTH','WRONG_DEVICE','BAD_CLOCK','BAD_WINDOW','REPLAY','ID_CONFLICT','STALE_DATA','UNKNOWN_LOAD','CRITICAL_LOAD','CAPABILITY_DENIED','PROFILE_MISMATCH','MIN_DWELL','INVALID','NOT_COMMISSIONED','RATE_LIMIT','PERSISTENCE_FAILURE','SESSION_CHANGED','ACTUATION_DISABLED_OR_FAILED','BUSY_AWAITING_FEEDBACK','MANUAL_HOLD','MAINTENANCE'}


def number(message, key, low, high, integer=False):
    value = message.get(key)
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high or (integer and int(value) != value):
        raise ValueError('invalid ' + key)
    return value


def boolean(message, key):
    if type(message.get(key)) is not bool:
        raise ValueError('invalid boolean ' + key)
    return message[key]


def identity(message, device, sequence_key):
    if type(message.get('schema_version')) is not int or message['schema_version'] != 2:
        raise ValueError('schema_version 2 required')
    if message.get('device_id') != device or not isinstance(device,str) or not ID.fullmatch(device):
        raise ValueError('identity mismatch')
    epoch, seq = message.get('boot_epoch'), message.get(sequence_key)
    if not isinstance(epoch, str) or not EPOCH.fullmatch(epoch):
        raise ValueError('boot epoch required')
    if not isinstance(seq, str) or not SEQUENCE.fullmatch(seq) or int(seq) >= 2**64:
        raise ValueError('canonical uint64 sequence required')


def feedback(message):
    valid, present = boolean(message,'feedback_valid'), boolean(message,'output_present')
    sensing = message.get('output_sensing')
    if sensing not in SENSING or valid != (sensing in {'AC_PRESENT','NO_AC_PULSES_DETECTED'}) or present != (sensing == 'AC_PRESENT'):
        raise ValueError('inconsistent feedback')


def validate_telemetry(message, device):
    schema_gate('device-wire-v2.schema.json',message)
    identity(message, device, 'sample_seq')
    if message.get('board_revision') != BOARD:
        raise ValueError('unsupported board')
    for key in ('valid','calibrated','board_temperature_valid','desired_on','fault_latched','voltage_absence_proven'):
        boolean(message,key)
    if message['voltage_absence_proven'] is not False:
        raise ValueError('optical feedback never proves electrical safety')
    feedback(message)
    mono=number(message,'monotonic_ms',0,2**53-1,True)
    sampled=number(message,'measurement_monotonic_ms',0,mono,True)
    if message['valid']:
        if not message['calibrated'] or mono-sampled > 10000:
            raise ValueError('valid measurement requires calibration and freshness')
        for key,low,high in [('voltage_v',0,1000),('current_a',0,1000),('active_w',-1e6,1e6),('reactive_var',-1e6,1e6),('apparent_va',0,1e6),('pf',-1.01,1.01),('frequency_hz',0,1000)]:
            number(message,key,low,high)
    else:
        if any(key in message for key in ('voltage_v','current_a','active_w','reactive_var','apparent_va','pf','frequency_hz')):
            raise ValueError('invalid sample must not carry apparently usable measurements')
    if message['board_temperature_valid']:
        number(message,'board_temperature_c',-100,200)
    elif 'board_temperature_c' in message:
        raise ValueError('invalid board temperature must be absent')
    for key in ('energy_uncertain_intervals','ram_buffer_dropped','command_dropped'):
        number(message,key,0,2**32-1,True)
    for key in ('known_forward_wh_since_boot','known_reverse_wh_since_boot'):
        number(message,key,0,2**53-1)
    expected='calibrated_counts_known_intervals_since_boot_not_billing_certified' if message['calibrated'] else 'uncalibrated_no_energy_result'
    if message.get('energy_status') != expected:
        raise ValueError('inconsistent energy quality')
    if message.get('time_quality') == 'authenticated':
        low=number(message,'unix_lower_s',1700000000,4102444799,True)
        high=number(message,'unix_upper_s',low,min(4102444799,low+5),True)
        number(message,'unix_s',low,high,True)
    elif message.get('time_quality') == 'unknown':
        if any(key not in message or message[key] is not None for key in ('unix_s','unix_lower_s','unix_upper_s')):
            raise ValueError('unknown time must be null')
    else:
        raise ValueError('unknown time quality')
    for key in ('manual_hold_until_uptime_ms',):
        if key in message:
            value=message[key]
            if not isinstance(value,str) or not re.fullmatch(r'0|[1-9][0-9]{0,19}',value) or int(value)>=2**64:
                raise ValueError('invalid local control uint64')
    local=message.get('last_local_input')
    if local is not None:
        for key in ('event_seq','uptime_ms'):
            value=local[key]
            if not re.fullmatch(r'0|[1-9][0-9]{0,19}',value) or int(value)>=2**64:
                raise ValueError('invalid local input uint64')
        if int(local['uptime_ms'])>mono or local['pressed']!=(int(local['event_seq'])>0):
            raise ValueError('inconsistent local input observation')
    return message


def validate_ack(message, device):
    schema_gate('device-ack-v2.schema.json',message)
    identity(message, device, 'seq')
    cid=message.get('id')
    if not isinstance(cid,str) or not ID.fullmatch(cid):
        raise ValueError('bad command ID')
    status=message.get('status')
    if status not in INTERMEDIATE | OBSERVED | REJECTIONS:
        raise ValueError('unsupported acknowledgement status')
    if boolean(message,'terminal') != (status not in INTERMEDIATE):
        raise ValueError('inconsistent terminal status')
    for key in ('desired_on','fault_latched','voltage_absence_proven'):
        boolean(message,key)
    if message['voltage_absence_proven']:
        raise ValueError('invalid electrical safety claim')
    if status in INTERMEDIATE | OBSERVED:
        requested=number(message,'requested_monotonic_ms',0,2**53-1,True)
        deadline=number(message,'deadline_monotonic_ms',requested,min(requested+5000,2**53-1),True)
        if deadline <= requested:
            raise ValueError('invalid observation deadline')
    if status in OBSERVED:
        observed=number(message,'observed_monotonic_ms',0,2**53-1,True)
        feedback(message)
        if status == 'OBSERVED_VERIFIED' and (observed < requested+100 or observed >= deadline or message['fault_latched'] or not message['feedback_valid'] or message['output_present'] != message['desired_on']):
            raise ValueError('unverified observation cannot be success')
    return message
