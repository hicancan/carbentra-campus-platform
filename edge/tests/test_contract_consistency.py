import copy
import json
from pathlib import Path
import unittest
from fixtures import *
from contract import validate_event, validate_descriptor, PRODUCTS
from adapters import descriptor

class ContractConsistencyTests(unittest.TestCase):
    def test_wrong_channel_family_and_unsupported_feedback_rejected(self):
        value=SwitchAdapter.telemetry(SWITCH,switch_raw(),NOW)
        value['readings'][0]['channel_id']='relay.4'
        with self.assertRaises(ValueError):validate_event(value)
        value=descriptor(SWITCH);value['channels'][0]['capabilities'][1]['available']=True
        with self.assertRaises(ValueError):validate_descriptor(value)
        self.assertFalse(next(cap for channel in PRODUCTS['SWITCH']['channels'] for cap in channel['capabilities'] if cap['capability']=='energy.export')['available'])
    def test_uncalibrated_raw_light_never_lux(self):
        value=sense_event()
        light=next(r for r in value['readings'] if r['capability']=='illuminance.raw')
        self.assertEqual((light['unit'],light['quality']),('raw_count','uncalibrated'))
        light['unit']='lux'
        with self.assertRaises(ValueError):validate_event(value)
    def test_unsigned_ad_cannot_upgrade_itself_to_trusted_vacancy(self):
        from dataclasses import replace
        value=PresenceAdapter.telemetry(replace(SENSE,protocol='presence-ble-v2'),presence_frame(radar=1),NOW)
        radar=next(r for r in value['readings'] if r['capability']=='presence.radar')
        radar['quality']='valid';radar['details']['continuous_occupancy']=True
        with self.assertRaises(ValueError):validate_event(value)
    def test_proof_mutations_cannot_invent_signed_values_or_identity(self):
        for kind in ('proof','identity','age','radar'):
            value=sense_event(radar=1)
            if kind=='proof':value['raw']['proof_sha256']='0'*64
            if kind=='identity':value['raw']['identity']=1
            if kind=='age':value['raw']['radar_age_ms']=0
            if kind=='radar':next(r for r in value['readings'] if r['capability']=='presence.radar')['value']=True
            with self.subTest(kind=kind),self.assertRaises(ValueError):validate_event(value)
