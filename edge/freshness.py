"""Control freshness, separate from durable receipt and historical ingestion.

Plug buffers its samples: arrival alone can never date a REAL Plug observation.
Switch has no device UTC; live non-retained publication and same-boot monotonic
progress remain its limited timing evidence, not an invented wall-clock value.
"""
from contract import timestamp

# A deliberately generous slow-device-clock allowance. Continuous publications
# tighten the bound again, without accumulating oscillator drift across uptime.
MONOTONIC_RATE_FLOOR = 0.99


def observation_freshness(event, now, maximum_age, clock_bound=None):
    received = timestamp(event['received_at']).timestamp()
    arrival_age = now - received
    age = max(0, arrival_age)
    observation_age = None
    reason = None
    reversed_clock = arrival_age < 0
    if reversed_clock:
        reason = 'gateway_clock_reversed'
    elif arrival_age > maximum_age:
        reason = 'arrival_stale'
    if event['source_mode'] == 'REPLAYED':
        reason = reason or 'replayed_source'

    mono = event['monotonic_ms']
    if clock_bound is not None and mono is not None:
        # Earliest receipt-minus-uptime bounds the latest possible boot origin.
        # A delayed/stalled sample cannot reset that bound on a new arrival.
        origin_upper, highwater, utc_low_highwater = clock_bound
        age = max(age, now - (origin_upper + mono / 1000 / MONOTONIC_RATE_FLOOR))
        if mono < highwater:
            reversed_clock = True
            reason = reason or 'device_monotonic_reversed'

    quality = event['time_quality']
    observed = event['observed_at']
    raw = event['raw']
    if event['source_protocol'] == 'plug-wire-v2':
        if quality == 'authenticated':
            low, high, central = (raw.get(key) for key in ('unix_lower_s', 'unix_upper_s', 'unix_s'))
            measured = raw.get('measurement_monotonic_ms')
            if (raw.get('time_quality') != 'authenticated' or observed is None
                    or any(type(v) not in (int, float) for v in (low, high, central, mono, measured))
                    or not low <= central <= high or not 0 <= high - low <= 5
                    or timestamp(observed).timestamp() != central
                    or raw.get('monotonic_ms') != mono or not 0 <= measured <= mono):
                reason = reason or 'inconsistent_observation_clock'
            elif low > received:
                # An uncertainty interval may straddle receipt, but cannot lie
                # wholly in its future. Do not silently clamp a future sample.
                reversed_clock = True
                reason = reason or 'future_observation'
            elif clock_bound is not None and utc_low_highwater is not None and high < utc_low_highwater:
                reversed_clock = True
                reason = reason or 'device_clock_reversed'
            else:
                # Use the oldest plausible time, never just its midpoint. The
                # electrical measurement can predate the captured control state.
                observation_age = max(0, now - low + (mono - measured) / 1000)
                age = max(age, observation_age)
        elif event['source_mode'] != 'SIMULATED':
            reason = reason or 'authenticated_observation_required'
        elif quality != 'unknown' or observed is not None:
            reason = reason or 'inconsistent_observation_clock'
    elif observed is not None:
        observed_age = now - timestamp(observed).timestamp()
        age = max(age, observed_age)
        if timestamp(observed).timestamp() > received:
            reversed_clock = True
            reason = reason or 'future_observation'
        if event['source_mode'] == 'REAL' and quality != 'authenticated':
            reason = reason or 'authenticated_observation_required'
        else:
            observation_age = max(0, observed_age)

    if age > maximum_age:
        reason = reason or 'observation_stale'
    return {'age_seconds': max(0, arrival_age), 'arrival_age_seconds': max(0, arrival_age),
            'observation_age_seconds': observation_age, 'control_age_seconds': age, 'fresh': reason is None,
            'clock_reversed': reversed_clock, 'freshness_reason': reason}
