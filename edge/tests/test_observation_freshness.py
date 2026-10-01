"""Synthetic inputs and memory publishers only; no network or physical IO."""
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from channel_transport import ChannelTransport
from fixtures import *
from rules import RuleEngine
from store import EdgeStore


REAL_PLUG = replace(PLUG, device_id='freshness-fixture-plug', source_mode='REAL')


def timed_plug(seq=1, observed=NOW, low=None, high=None, mono=5000, measured=None, boot='a'*32):
    raw = plug_raw(seq=seq, boot=boot, on=False)
    raw.update(device_id=REAL_PLUG.device_id, actuation_enabled=True,
               time_quality='authenticated', unix_s=observed,
               unix_lower_s=observed if low is None else low,
               unix_upper_s=observed if high is None else high,
               monotonic_ms=mono, measurement_monotonic_ms=mono if measured is None else measured,
               calibrated=True, valid=True, voltage_v=230, current_a=.5, active_w=100,
               reactive_var=0, apparent_va=115, pf=.87, frequency_hz=50,
               energy_status='calibrated_counts_known_intervals_since_boot_not_billing_certified')
    return raw


class ObservationFreshnessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / 'edge.sqlite')
        self.store = EdgeStore(self.db)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def accept(self, raw, received=NOW):
        value = PlugAdapter.telemetry(REAL_PLUG, raw, received)
        self.store.accept_event(value)
        return self.store.snapshot(REAL_PLUG.device_id, received, maximum_age=5)

    def transport(self, device=REAL_PLUG):
        published = []
        transport = ChannelTransport(self.db, [device], lambda *args: published.append(args) or True,
                                     physical_enabled=True, physical_releases={device.device_id: 'test-release'})
        cmd = command(device=device, boot='a'*32)
        cmd['authority']['release_id'] = 'test-release'
        return transport, cmd, published

    def rule(self):
        sensor = replace(SENSE, source_mode='REAL')
        verifier = ChallengeVerifier(TEST_KEY)
        nonce = verifier.challenge()
        self.store.accept_event(authenticated_event(sensor, signed_response(nonce), verifier, NOW), authenticated=True)
        engine = RuleEngine(self.db)
        engine.install({'schema_version': 1, 'revision': 1, 'valid_until': iso(NOW+200), 'rules': [{
            'id': 'freshness-fixture', 'sensor_device_id': sensor.device_id, 'target_device_id': REAL_PLUG.device_id,
            'channel_id': 'relay.1', 'when_present': True, 'desired_on': True,
            'stable_for_seconds': 0, 'maximum_age_seconds': 5,
            'lease': {'lease_id': 'freshness-lease', 'issuer': 'operator', 'issued_at': iso(NOW-1),
                      'expires_at': iso(NOW+100), 'offline_until': iso(NOW+50),
                      'sequence_start': '100', 'sequence_end': '110', 'release_id': 'test-release'}}]})
        return engine

    def test_buffered_real_plug_is_durable_but_neither_rule_nor_transport_can_use_it(self):
        snapshot = self.accept(timed_plug(observed=NOW-300, low=NOW-301, high=NOW-299))
        self.assertEqual(snapshot['arrival_age_seconds'], 0)
        self.assertEqual(snapshot['observation_age_seconds'], 301)
        self.assertFalse(snapshot['fresh'])
        self.assertEqual(self.store.status()['outbox_pending'], 1)
        evaluation = self.rule().once(connected=False, now=NOW)[0]
        self.assertEqual(evaluation['reason'], 'target_unknown_or_stale')
        self.assertIsNone(evaluation['command'])
        transport, cmd, published = self.transport()
        self.assertEqual(transport.process(cmd, NOW)['reason'], 'fresh_observation_required')
        self.assertEqual(published, [])

    def test_fresh_authenticated_interval_preserves_local_rule_and_cloud_commands(self):
        snapshot = self.accept(timed_plug(low=NOW-1, high=NOW+1, measured=4500))
        self.assertTrue(snapshot['fresh'])
        self.assertEqual(snapshot['observation_age_seconds'], 1.5)
        candidate = self.rule().once(connected=False, now=NOW)[0]
        self.assertEqual(candidate['reason'], 'authorized_candidate')
        transport, cmd, published = self.transport()
        self.assertEqual(transport.process(cmd, NOW)['status'], 'published')
        self.assertEqual(transport.process(candidate['command'], NOW)['status'], 'published')
        self.assertEqual(len(published), 2)

    def test_unknown_real_clock_does_not_gain_trust_from_fresh_arrival(self):
        raw = timed_plug()
        raw.update(time_quality='unknown', unix_s=None, unix_lower_s=None, unix_upper_s=None)
        snapshot = self.accept(raw)
        self.assertFalse(snapshot['fresh'])
        self.assertEqual(snapshot['freshness_reason'], 'authenticated_observation_required')
        self.assertIsNone(snapshot['observation_age_seconds'])
        simulation = replace(REAL_PLUG, device_id='simulation-clock-fixture', source_mode='SIMULATED')
        raw['device_id'] = simulation.device_id
        self.store.accept_event(PlugAdapter.telemetry(simulation, raw, NOW))
        self.assertTrue(self.store.snapshot(simulation.device_id, NOW)['fresh'])

    def test_oldest_interval_endpoint_and_measurement_age_both_count(self):
        snapshot = self.accept(timed_plug(observed=NOW-4, low=NOW-5, high=NOW-3, measured=4500))
        self.assertFalse(snapshot['fresh'])
        self.assertEqual(snapshot['observation_age_seconds'], 5.5)
        # Exact boundary is usable; any further elapsed time consumes the budget.
        self.assertTrue(self.store.snapshot(REAL_PLUG.device_id, NOW-.5, maximum_age=5)['clock_reversed'])
        self.accept(timed_plug(seq=2, observed=NOW, low=NOW-4, high=NOW, mono=6000, measured=5000))
        self.assertTrue(self.store.snapshot(REAL_PLUG.device_id, NOW, maximum_age=5)['fresh'])
        self.assertFalse(self.store.snapshot(REAL_PLUG.device_id, NOW+.001, maximum_age=5)['fresh'])

    def test_future_observation_and_gateway_rollback_fail_closed(self):
        snapshot = self.accept(timed_plug(observed=NOW+2, low=NOW+1, high=NOW+3))
        self.assertFalse(snapshot['fresh'])
        self.assertTrue(snapshot['clock_reversed'])
        self.assertEqual(snapshot['freshness_reason'], 'future_observation')
        self.assertFalse(self.store.snapshot(REAL_PLUG.device_id, NOW-1)['fresh'])

    def test_untrusted_or_inconsistent_canonical_clock_does_not_authorize(self):
        for case in ('device_clock', 'mismatched_observed', 'wide_interval', 'mismatched_monotonic'):
            with self.subTest(case=case):
                event = PlugAdapter.telemetry(REAL_PLUG, timed_plug(), NOW)
                if case == 'device_clock': event['time_quality'] = 'device_clock'
                if case == 'mismatched_observed': event['observed_at'] = iso(NOW-1)
                if case == 'wide_interval': event['raw']['unix_lower_s'] = NOW-6
                if case == 'mismatched_monotonic': event['monotonic_ms'] += 1
                store = EdgeStore(':memory:')
                try:
                    store.accept_event(event)
                    self.assertFalse(store.snapshot(REAL_PLUG.device_id, NOW)['fresh'])
                finally:
                    store.close()

    def test_same_boot_monotonic_and_utc_rollback_are_not_fresh(self):
        self.accept(timed_plug())
        snapshot = self.accept(timed_plug(seq=2, observed=NOW+1, mono=4000), NOW+1)
        self.assertEqual(snapshot['freshness_reason'], 'device_monotonic_reversed')
        snapshot = self.accept(timed_plug(seq=3, observed=NOW-1, mono=6000), NOW+2)
        self.assertEqual(snapshot['freshness_reason'], 'device_clock_reversed')
        self.assertFalse(snapshot['fresh'])
        self.assertTrue(self.accept(timed_plug(seq=4, observed=NOW+3, mono=8000), NOW+3)['fresh'])

    def test_stalled_clock_bound_survives_restart_and_boot_change_is_explicit(self):
        self.accept(timed_plug())
        self.store.close()
        self.store = EdgeStore(self.db)
        snapshot = self.accept(timed_plug(seq=2, observed=NOW+11), NOW+11)
        self.assertFalse(snapshot['fresh'])
        self.assertEqual(snapshot['control_age_seconds'], 11)
        self.assertTrue(self.accept(timed_plug(boot='c'*32, observed=NOW+12, mono=1000), NOW+12)['fresh'])
        self.accept(timed_plug(seq=3, observed=NOW+13, mono=18000), NOW+13)
        self.assertEqual(self.store.snapshot(REAL_PLUG.device_id, NOW+13)['event']['boot_id'], 'c'*32)

    def test_upgrade_seeds_monotonic_bound_from_original_cached_receipt(self):
        self.accept(timed_plug())
        self.store.db.execute('DROP TABLE observation_clocks')
        self.store.db.commit()
        self.store.close()
        self.store = EdgeStore(self.db)
        snapshot = self.accept(timed_plug(seq=2, observed=NOW+11), NOW+11)
        self.assertFalse(snapshot['fresh'])
        self.assertEqual(snapshot['control_age_seconds'], 11)

    def test_live_real_switch_keeps_clockless_cloud_path_without_inventing_utc(self):
        real = replace(SWITCH, source_mode='REAL')
        for seq, now in ((1, NOW), (2, NOW+60)):
            raw = switch_raw(seq=seq, uptime_ms=100000+int((now-NOW)*1000))
            raw.update(source_mode='REAL', actuation_enabled=True)
            self.store.accept_event(SwitchAdapter.telemetry(real, raw, now))
        snapshot = self.store.snapshot(real.device_id, NOW+60)
        self.assertTrue(snapshot['fresh'])
        self.assertIsNone(snapshot['event']['observed_at'])
        self.assertIsNone(snapshot['observation_age_seconds'])
        transport, cmd, published = self.transport(real)
        cmd = command(device=real, now=NOW+60)
        cmd['authority']['release_id'] = 'test-release'
        self.assertEqual(transport.process(cmd, NOW+60)['status'], 'published')
        self.assertEqual(len(published), 1)

    def test_replayed_source_is_never_a_fresh_control_snapshot(self):
        replayed = replace(REAL_PLUG, source_mode='REPLAYED')
        self.store.accept_event(PlugAdapter.telemetry(replayed, timed_plug(), NOW))
        self.assertFalse(self.store.snapshot(replayed.device_id, NOW)['fresh'])
