import { describe, expect, it } from 'vitest'
import { physicalGateBlocker } from './control-eligibility'
import type { ControlEligibility } from './control-eligibility'
const now = Date.now()
const eligible: ControlEligibility = {
  channel_id: null,
  channel_key: 'relay.1',
  product_family: 'PLUG',
  verification_kind: 'independent_feedback',
  device_id: 'inert-fixture',
  device_name: 'Inert test device',
  source_mode: 'REAL',
  dispatch_mode: 'PHYSICAL',
  profile_revision: 1,
  eligible: true,
  allowed_actions: ['shed'],
  reasons: { hold: null, shed: null, restore: null },
  physical_deployment_enabled: true,
  load: { id: 'inert-load', name: 'INERT UI TEST LOAD', profile_id: 'test' },
  release: {
    id: 'release-fixture',
    status: 'released',
    valid_until: new Date(now + 60000).toISOString(),
    basis: 'operator_attestation',
  },
  checked_at: new Date(now).toISOString(),
  server_rechecks_on_submission_and_lease: true,
  consequence: 'Inert fixture; no actuator connected',
}
describe('future physical UI gate (inert data only)', () => {
  it('requires every independent release and freshness condition', () => {
    expect(physicalGateBlocker(eligible, 'inert-fixture', now, now)).toBeNull()
  })
  it.each([
    { physical_deployment_enabled: false },
    { dispatch_mode: 'DISABLED' },
    { source_mode: 'REPLAYED' },
    { release: null },
    { eligible: false },
    { profile_revision: 0 },
    { profile_revision: undefined },
    { allowed_actions: [] },
    { load: { id: null, name: null, profile_id: 'test' } },
    { release: { ...eligible.release!, status: 'pending' } },
  ])('fails closed for %j', (override) => {
    expect(
      physicalGateBlocker(
        { ...eligible, ...override } as ControlEligibility,
        'inert-fixture',
        now,
        now,
      ),
    ).not.toBeNull()
  })
  it('refuses stale checks, expired records and mismatched identities', () => {
    expect(physicalGateBlocker(eligible, 'other-device', now, now)).not.toBeNull()
    expect(physicalGateBlocker(eligible, 'inert-fixture', now - 16000, now)).not.toBeNull()
    expect(
      physicalGateBlocker(
        {
          ...eligible,
          release: { ...eligible.release!, valid_until: new Date(now - 1).toISOString() },
        },
        'inert-fixture',
        now,
        now,
      ),
    ).not.toBeNull()
  })
})
