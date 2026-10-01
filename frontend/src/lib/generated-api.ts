// Generated from packages/contracts/openapi.json. Do not edit.
// Source SHA-256: f6bb5edc131d5fa92310134d4e0cd20eeb28079f70ee1742c2fce168d7e6d5a2
// Regenerate with npm run api:generate; validate with npm run api:check.

export interface paths {
  '/api/v1/adapter/commands': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Adapter Commands */
    get: operations['adapter_commands_api_v1_adapter_commands_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/adapter/commands/{command_id}/delivery': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /** Adapter Delivery */
    post: operations['adapter_delivery_api_v1_adapter_commands__command_id__delivery_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/alarms': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Alarms */
    get: operations['alarms_api_v1_alarms_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/alarms/{alarm_id}': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Alarm Detail */
    get: operations['alarm_detail_api_v1_alarms__alarm_id__get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/alarms/{alarm_id}/acknowledge': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /** Alarm Ack */
    post: operations['alarm_ack_api_v1_alarms__alarm_id__acknowledge_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/alarms/{alarm_id}/notes': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /** Alarm Note */
    post: operations['alarm_note_api_v1_alarms__alarm_id__notes_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/alarms/{alarm_id}/resolve': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /** Alarm Resolve */
    post: operations['alarm_resolve_api_v1_alarms__alarm_id__resolve_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/assets/manifest': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Assets Manifest */
    get: operations['assets_manifest_api_v1_assets_manifest_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/assets/product/hero': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Product Hero */
    get: operations['product_hero_api_v1_assets_product_hero_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/assets/product/manifest': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Product Manifest */
    get: operations['product_manifest_api_v1_assets_product_manifest_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/assets/product/model': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Product Model */
    get: operations['product_model_api_v1_assets_product_model_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/audit': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Audit Log */
    get: operations['audit_log_api_v1_audit_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/auth/login': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /** Auth Login */
    post: operations['auth_login_api_v1_auth_login_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/auth/logout': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /** Auth Logout */
    post: operations['auth_logout_api_v1_auth_logout_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/auth/me': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Auth Me */
    get: operations['auth_me_api_v1_auth_me_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/buildings': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Buildings */
    get: operations['buildings_api_v1_buildings_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/buildings/{building_id}': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Building Detail */
    get: operations['building_detail_api_v1_buildings__building_id__get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/campuses': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Campuses */
    get: operations['campuses_api_v1_campuses_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/carbon/factors': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Factors */
    get: operations['factors_api_v1_carbon_factors_get']
    put?: never
    /** Factor Create */
    post: operations['factor_create_api_v1_carbon_factors_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/carbon/summary': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Carbon Summary */
    get: operations['carbon_summary_api_v1_carbon_summary_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/channels': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /** New Channel */
    post: operations['new_channel_api_v1_channels_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/circuits': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /** Circuit Create */
    post: operations['circuit_create_api_v1_circuits_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/circuits/{circuit_id}': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    /** Circuit Update */
    patch: operations['circuit_update_api_v1_circuits__circuit_id__patch']
    trace?: never
  }
  '/api/v1/classrooms': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Rooms */
    get: operations['rooms_api_v1_classrooms_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/classrooms/anomalies': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Anomalies */
    get: operations['anomalies_api_v1_classrooms_anomalies_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/classrooms/anomalies/evaluate': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /** Evaluate Anomalies */
    post: operations['evaluate_anomalies_api_v1_classrooms_anomalies_evaluate_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/classrooms/anomalies/{anomaly_id}/acknowledge': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /** Acknowledge */
    post: operations['acknowledge_api_v1_classrooms_anomalies__anomaly_id__acknowledge_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/classrooms/anomalies/{anomaly_id}/resolve': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /** Resolve */
    post: operations['resolve_api_v1_classrooms_anomalies__anomaly_id__resolve_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/classrooms/anomaly-rules/batch': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    /** Change Anomaly Rules */
    patch: operations['change_anomaly_rules_api_v1_classrooms_anomaly_rules_batch_patch']
    trace?: never
  }
  '/api/v1/classrooms/distribution': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Distribution */
    get: operations['distribution_api_v1_classrooms_distribution_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/classrooms/evaluations/{evaluation_id}': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Evaluation */
    get: operations['evaluation_api_v1_classrooms_evaluations__evaluation_id__get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/classrooms/evaluations/{evaluation_id}/dispatch': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /** Dispatch */
    post: operations['dispatch_api_v1_classrooms_evaluations__evaluation_id__dispatch_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/classrooms/policies/{policy_id}': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    /** Change Policy */
    patch: operations['change_policy_api_v1_classrooms_policies__policy_id__patch']
    trace?: never
  }
  '/api/v1/classrooms/policies/{policy_id}/evaluate': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /** Evaluate Policy */
    post: operations['evaluate_policy_api_v1_classrooms_policies__policy_id__evaluate_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/classrooms/{room_id}': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Room */
    get: operations['room_api_v1_classrooms__room_id__get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/classrooms/{room_id}/anomaly-rule': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Anomaly Rule */
    get: operations['anomaly_rule_api_v1_classrooms__room_id__anomaly_rule_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    /** Change Anomaly Rule */
    patch: operations['change_anomaly_rule_api_v1_classrooms__room_id__anomaly_rule_patch']
    trace?: never
  }
  '/api/v1/classrooms/{room_id}/channels': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Room Channels */
    get: operations['room_channels_api_v1_classrooms__room_id__channels_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/classrooms/{room_id}/evaluations': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Room Evaluations */
    get: operations['room_evaluations_api_v1_classrooms__room_id__evaluations_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/classrooms/{room_id}/mode': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Modes */
    get: operations['modes_api_v1_classrooms__room_id__mode_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    /** Change Mode */
    patch: operations['change_mode_api_v1_classrooms__room_id__mode_patch']
    trace?: never
  }
  '/api/v1/classrooms/{room_id}/policies': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Policies */
    get: operations['policies_api_v1_classrooms__room_id__policies_get']
    put?: never
    /** New Policy */
    post: operations['new_policy_api_v1_classrooms__room_id__policies_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/classrooms/{room_id}/timeline': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Room Timeline */
    get: operations['room_timeline_api_v1_classrooms__room_id__timeline_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/commands': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Commands */
    get: operations['commands_api_v1_commands_get']
    put?: never
    /** Command Create */
    post: operations['command_create_api_v1_commands_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/commands/{command_id}': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Command Detail */
    get: operations['command_detail_api_v1_commands__command_id__get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/cost/summary': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Cost Summary */
    get: operations['cost_summary_api_v1_cost_summary_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/devices': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Devices */
    get: operations['devices_api_v1_devices_get']
    put?: never
    /** Device Create */
    post: operations['device_create_api_v1_devices_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/devices/{device_id}': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Device Detail */
    get: operations['device_detail_api_v1_devices__device_id__get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    /** Device Update */
    patch: operations['device_update_api_v1_devices__device_id__patch']
    trace?: never
  }
  '/api/v1/devices/{device_id}/binding': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    /** Device Binding */
    put: operations['device_binding_api_v1_devices__device_id__binding_put']
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/devices/{device_id}/commissioning': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Commissioning List */
    get: operations['commissioning_list_api_v1_devices__device_id__commissioning_get']
    put?: never
    /** Commissioning Create */
    post: operations['commissioning_create_api_v1_devices__device_id__commissioning_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/devices/{device_id}/commissioning/release': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /** Commissioning Release */
    post: operations['commissioning_release_api_v1_devices__device_id__commissioning_release_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/devices/{device_id}/commissioning/{release_id}/revoke': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /** Commissioning Revoke */
    post: operations['commissioning_revoke_api_v1_devices__device_id__commissioning__release_id__revoke_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/devices/{device_id}/control-eligibility': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Control Eligibility */
    get: operations['control_eligibility_api_v1_devices__device_id__control_eligibility_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/devices/{device_id}/telemetry': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Device Telemetry */
    get: operations['device_telemetry_api_v1_devices__device_id__telemetry_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/energy/balance': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Energy Balance */
    get: operations['energy_balance_api_v1_energy_balance_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/energy/breakdown': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Energy Breakdown */
    get: operations['energy_breakdown_api_v1_energy_breakdown_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/energy/summary': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Energy Summary */
    get: operations['energy_summary_api_v1_energy_summary_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/events': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Events */
    get: operations['events_api_v1_events_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/floors': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Floors */
    get: operations['floors_api_v1_floors_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/forecasts': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Forecasts */
    get: operations['forecasts_api_v1_forecasts_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/forecasts/refresh': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /** Forecast Refresh */
    post: operations['forecast_refresh_api_v1_forecasts_refresh_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/ingest/ack': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /** Adapter Ack */
    post: operations['adapter_ack_api_v1_ingest_ack_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/ingest/channel-acks': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /** Channel Ack */
    post: operations['channel_ack_api_v1_ingest_channel_acks_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/ingest/channels': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /** Channel Samples */
    post: operations['channel_samples_api_v1_ingest_channels_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/ingest/events': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /** Canonical Event */
    post: operations['canonical_event_api_v1_ingest_events_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/ingest/firmware': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /** Ingest Firmware */
    post: operations['ingest_firmware_api_v1_ingest_firmware_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/ingest/telemetry': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /** Ingest */
    post: operations['ingest_api_v1_ingest_telemetry_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/overview': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Overview Route */
    get: operations['overview_route_api_v1_overview_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/reports': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Reports */
    get: operations['reports_api_v1_reports_get']
    put?: never
    /** Report Create */
    post: operations['report_create_api_v1_reports_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/reports/{report_id}': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Report Detail */
    get: operations['report_detail_api_v1_reports__report_id__get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/reports/{report_id}/export': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Report Export */
    get: operations['report_export_api_v1_reports__report_id__export_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/schedules': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Schedules */
    get: operations['schedules_api_v1_schedules_get']
    put?: never
    /** Schedule Create */
    post: operations['schedule_create_api_v1_schedules_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/schedules/import': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /** Schedule Import */
    post: operations['schedule_import_api_v1_schedules_import_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/schedules/{schedule_id}': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    /** Schedule Update */
    put: operations['schedule_update_api_v1_schedules__schedule_id__put']
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/schedules/{schedule_id}/cancel': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /** Schedule Cancel */
    post: operations['schedule_cancel_api_v1_schedules__schedule_id__cancel_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/settings': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Settings Read */
    get: operations['settings_read_api_v1_settings_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    /** Settings Update */
    patch: operations['settings_update_api_v1_settings_patch']
    trace?: never
  }
  '/api/v1/spaces': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Spaces */
    get: operations['spaces_api_v1_spaces_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/strategies': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Strategies */
    get: operations['strategies_api_v1_strategies_get']
    put?: never
    /** Strategy Create */
    post: operations['strategy_create_api_v1_strategies_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/strategies/{strategy_id}/approve': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /** Strategy Approve */
    post: operations['strategy_approve_api_v1_strategies__strategy_id__approve_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/strategies/{strategy_id}/dispatch': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /** Strategy Dispatch */
    post: operations['strategy_dispatch_api_v1_strategies__strategy_id__dispatch_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/strategies/{strategy_id}/evaluate': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /** Strategy Evaluate */
    post: operations['strategy_evaluate_api_v1_strategies__strategy_id__evaluate_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/system/status': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** System Status */
    get: operations['system_status_api_v1_system_status_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/tariffs': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Tariffs */
    get: operations['tariffs_api_v1_tariffs_get']
    put?: never
    /** Tariff Create */
    post: operations['tariff_create_api_v1_tariffs_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/telemetry': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Telemetry */
    get: operations['telemetry_api_v1_telemetry_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/topology': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Topology */
    get: operations['topology_api_v1_topology_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/users': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Users List */
    get: operations['users_list_api_v1_users_get']
    put?: never
    /** User Create */
    post: operations['user_create_api_v1_users_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/api/v1/users/{user_id}': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    /** User Update */
    patch: operations['user_update_api_v1_users__user_id__patch']
    trace?: never
  }
  '/api/v1/users/{user_id}/password': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    get?: never
    put?: never
    /** User Password */
    post: operations['user_password_api_v1_users__user_id__password_post']
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/health/live': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Live */
    get: operations['live_health_live_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
  '/health/ready': {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    /** Ready */
    get: operations['ready_health_ready_get']
    put?: never
    post?: never
    delete?: never
    options?: never
    head?: never
    patch?: never
    trace?: never
  }
}
export type webhooks = Record<string, never>
export interface components {
  schemas: {
    /** AnomalyEvidence */
    AnomalyEvidence: {
      /** Baseline Condition */
      baseline_condition: string
      /** Baseline Mad W */
      baseline_mad_w: number | null
      /** Baseline Median W */
      baseline_median_w: number | null
      /** Baseline Sample Count */
      baseline_sample_count: number
      /**
       * Baseline Status
       * @enum {string}
       */
      baseline_status: 'sufficient' | 'insufficient' | 'not_applicable'
      /** Clear Threshold W */
      clear_threshold_w?: number | null
      /**
       * Evaluated At
       * Format: date-time
       */
      evaluated_at: string
      /** Explanation */
      explanation: string
      /** Observation Ids */
      observation_ids: number[]
      /** Observed Power W */
      observed_power_w: number | null
      /** Persistence Seconds */
      persistence_seconds: number
      /** Quality Flags */
      quality_flags: string[]
      /** Required Persistence Seconds */
      required_persistence_seconds: number
      /**
       * Rule Revision
       * @default 0
       */
      rule_revision: number
      /** Rule Version */
      rule_version: string
      /** Threshold W */
      threshold_w: number | null
    }
    /** AnomalyNote */
    AnomalyNote: {
      /** Action */
      action: string
      /**
       * At
       * Format: date-time
       */
      at: string
      /** By */
      by: string
      /** Text */
      text: string
    }
    /** AnomalyResponse */
    AnomalyResponse: {
      /** Building Id */
      building_id: string
      /** Campus Id */
      campus_id: string
      /**
       * Episode Start
       * Format: date-time
       */
      episode_start: string
      evidence: components['schemas']['AnomalyEvidence']
      /** Id */
      id: string
      /**
       * Last Observed At
       * Format: date-time
       */
      last_observed_at: string
      /** Notes */
      notes: components['schemas']['AnomalyNote'][]
      /** Resolved At */
      resolved_at: string | null
      /** Severity */
      severity: string
      /**
       * Source Mode
       * @enum {string}
       */
      source_mode: 'SIMULATED' | 'REPLAYED' | 'REAL' | 'UNKNOWN' | 'MIXED'
      /** Space Id */
      space_id: string
      /**
       * Status
       * @enum {string}
       */
      status: 'open' | 'acknowledged' | 'resolved'
      /** Type */
      type: string
    }
    /** AnomalyRuleBatchPatch */
    AnomalyRuleBatchPatch: {
      /**
       * Baseline Mad Multiplier
       * @default 3
       */
      baseline_mad_multiplier: number
      /**
       * Baseline Multiplier
       * @default 1.8
       */
      baseline_multiplier: number
      /**
       * Clear Hysteresis Ratio
       * @default 0.1
       */
      clear_hysteresis_ratio: number
      /**
       * Data Quality Persistence Seconds
       * @default 300
       */
      data_quality_persistence_seconds: number
      /**
       * Enabled
       * @default true
       */
      enabled: boolean
      /** Expected Revisions */
      expected_revisions: {
        [key: string]: number
      }
      /**
       * High Load Minimum W
       * @default 100
       */
      high_load_minimum_w: number
      /**
       * High Load Persistence Seconds
       * @default 600
       */
      high_load_persistence_seconds: number
      /** Reason */
      reason: string
      /** Room Ids */
      room_ids: string[]
      /**
       * Vacant Persistence Seconds
       * @default 300
       */
      vacant_persistence_seconds: number
      /**
       * Vacant Power Threshold W
       * @default 50
       */
      vacant_power_threshold_w: number
    }
    /** AnomalyRuleConfig */
    AnomalyRuleConfig: {
      /**
       * Baseline Mad Multiplier
       * @default 3
       */
      baseline_mad_multiplier: number
      /**
       * Baseline Multiplier
       * @default 1.8
       */
      baseline_multiplier: number
      /**
       * Clear Hysteresis Ratio
       * @default 0.1
       */
      clear_hysteresis_ratio: number
      /**
       * Data Quality Persistence Seconds
       * @default 300
       */
      data_quality_persistence_seconds: number
      /**
       * Enabled
       * @default true
       */
      enabled: boolean
      /**
       * High Load Minimum W
       * @default 100
       */
      high_load_minimum_w: number
      /**
       * High Load Persistence Seconds
       * @default 600
       */
      high_load_persistence_seconds: number
      /**
       * Vacant Persistence Seconds
       * @default 300
       */
      vacant_persistence_seconds: number
      /**
       * Vacant Power Threshold W
       * @default 50
       */
      vacant_power_threshold_w: number
    }
    /** AnomalyRulePatch */
    AnomalyRulePatch: {
      /**
       * Baseline Mad Multiplier
       * @default 3
       */
      baseline_mad_multiplier: number
      /**
       * Baseline Multiplier
       * @default 1.8
       */
      baseline_multiplier: number
      /**
       * Clear Hysteresis Ratio
       * @default 0.1
       */
      clear_hysteresis_ratio: number
      /**
       * Data Quality Persistence Seconds
       * @default 300
       */
      data_quality_persistence_seconds: number
      /**
       * Enabled
       * @default true
       */
      enabled: boolean
      /** Expected Revision */
      expected_revision: number
      /**
       * High Load Minimum W
       * @default 100
       */
      high_load_minimum_w: number
      /**
       * High Load Persistence Seconds
       * @default 600
       */
      high_load_persistence_seconds: number
      /** Reason */
      reason: string
      /**
       * Vacant Persistence Seconds
       * @default 300
       */
      vacant_persistence_seconds: number
      /**
       * Vacant Power Threshold W
       * @default 50
       */
      vacant_power_threshold_w: number
    }
    /** AnomalyRuleResponse */
    AnomalyRuleResponse: {
      config: components['schemas']['AnomalyRuleConfig']
      /**
       * Defaults Are Engineering Assumptions
       * @default true
       * @constant
       */
      defaults_are_engineering_assumptions: true
      /** Reason */
      reason: string
      /** Revision */
      revision: number
      /** Space Id */
      space_id: string
      /** Updated At */
      updated_at: string | null
      /** Updated By */
      updated_by: string | null
    }
    /** AuthResponse */
    AuthResponse: {
      /** Csrf Token */
      csrf_token: string
      /**
       * Expires At
       * Format: date-time
       */
      expires_at: string
      user: components['schemas']['UserResponse']
    }
    /** BindingIn */
    BindingIn: {
      /** Building Id */
      building_id?: string | null
      /** Campus Id */
      campus_id: string
      /** Circuit Id */
      circuit_id?: string | null
      /** Floor Id */
      floor_id?: string | null
      /** Reason */
      reason: string
      /** Space Id */
      space_id?: string | null
    }
    /** BindingResponse */
    BindingResponse: {
      /** Actor */
      actor: string
      /** Building Id */
      building_id: string | null
      /** Campus Id */
      campus_id: string
      /** Circuit Id */
      circuit_id: string | null
      /** Device Id */
      device_id: string
      /** Floor Id */
      floor_id: string | null
      /** Id */
      id: number
      /** Reason */
      reason: string
      /** Space Id */
      space_id: string | null
      /**
       * Valid From
       * Format: date-time
       */
      valid_from: string
      /** Valid To */
      valid_to: string | null
    }
    /** CarbonSummaryResponse */
    CarbonSummaryResponse: {
      /** Coverage Ratio */
      coverage_ratio: number | null
      /** Device Count */
      device_count: number
      /** Excluded Intervals */
      excluded_intervals: number
      /** Export Kwh */
      export_kwh: number | null
      factor: components['schemas']['FactorResponse'] | null
      /** Factor Id */
      factor_id: string | null
      /** Factors Used */
      factors_used: string[]
      /** Interval Count */
      interval_count: number
      /** Kg Co2E */
      kg_co2e: number | null
      /** Known Kwh */
      known_kwh: number | null
      /** Method */
      method: string
      /**
       * Period End
       * Format: date-time
       */
      period_end: string
      /**
       * Period Start
       * Format: date-time
       */
      period_start: string
      /** Quality */
      quality: string
      /** Queried Sample Count */
      queried_sample_count: number
      /**
       * Reduction Claim
       * @constant
       */
      reduction_claim: false
      /** Selected Device Ids */
      selected_device_ids: string[]
      /**
       * Source Mode
       * @enum {string}
       */
      source_mode: 'SIMULATED' | 'REPLAYED' | 'REAL' | 'UNKNOWN' | 'MIXED'
      /** Warnings */
      warnings: string[]
    }
    /** ChannelBatch */
    ChannelBatch: {
      /** Samples */
      samples: components['schemas']['ChannelSample'][]
    }
    /** ChannelBatchReceipt */
    ChannelBatchReceipt: {
      /**
       * Durable
       * @constant
       */
      durable: true
      /** Receipts */
      receipts: components['schemas']['ChannelReceipt'][]
    }
    /** ChannelDefinition */
    ChannelDefinition: {
      /** Campus Id */
      campus_id: string
      /** Capabilities */
      capabilities: string[]
      /** Channel Key */
      channel_key: string
      /**
       * Controllable
       * @default false
       */
      controllable: boolean
      /**
       * Created At
       * Format: date-time
       */
      created_at: string
      /** Device Id */
      device_id: string
      /**
       * Freshness Seconds
       * @default 120
       */
      freshness_seconds: number
      /** Id */
      id: string
      /** Introduced At */
      introduced_at?: string | null
      /**
       * Kind
       * @enum {string}
       */
      kind: 'presence' | 'lighting' | 'socket' | 'power' | 'temperature' | 'illuminance' | 'co2'
      /** Last Control At */
      last_control_at?: string | null
      /** Name */
      name: string
      /** Unit */
      unit?: ('W' | 'Wh' | 'degC' | 'lux' | 'raw_count' | 'ppm') | null
    }
    /** ChannelIn */
    ChannelIn: {
      /** Capabilities */
      capabilities: string[]
      /** Channel Key */
      channel_key: string
      /**
       * Controllable
       * @default false
       */
      controllable: boolean
      /** Device Id */
      device_id: string
      /**
       * Freshness Seconds
       * @default 120
       */
      freshness_seconds: number
      /** Id */
      id: string
      /**
       * Kind
       * @enum {string}
       */
      kind: 'presence' | 'lighting' | 'socket' | 'power' | 'temperature' | 'illuminance' | 'co2'
      /** Name */
      name: string
      /** Unit */
      unit?: ('W' | 'Wh' | 'degC' | 'lux' | 'raw_count' | 'ppm') | null
    }
    /** ChannelReceipt */
    ChannelReceipt: {
      /** Channel Id */
      channel_id: string
      /** Observation Id */
      observation_id: number
      /** Quality */
      quality: string
      /**
       * Status
       * @enum {string}
       */
      status: 'stored' | 'duplicate'
    }
    /** ChannelSample */
    ChannelSample: {
      /** Boot Epoch */
      boot_epoch: string
      /** Channel Id */
      channel_id: string
      /** Observed At */
      observed_at: string | null
      /** Sample Seq */
      sample_seq: string
      /**
       * Source Mode
       * @enum {string}
       */
      source_mode: 'SIMULATED' | 'REPLAYED' | 'REAL'
      /** Source Version */
      source_version: string
      /**
       * Time Source
       * @enum {string}
       */
      time_source: 'authenticated' | 'simulated' | 'device_clock' | 'received_only'
      /** Time Uncertainty Ms */
      time_uncertainty_ms?: number | null
      /** Valid */
      valid: boolean
      value: components['schemas']['ChannelValue']
    }
    /** ChannelSnapshot */
    ChannelSnapshot: {
      /** Allowed Actions */
      allowed_actions: ('hold' | 'shed' | 'restore')[]
      /** Binding Id */
      binding_id: number | null
      /** Block Reason */
      block_reason: string | null
      /** Capabilities */
      capabilities: string[]
      /** Channel Id */
      channel_id: string
      /** Channel Key */
      channel_key: string
      /** Controllable */
      controllable: boolean
      /** Device Id */
      device_id: string
      /** Effective At */
      effective_at: string | null
      /** Feedback Supported */
      feedback_supported: boolean
      /**
       * Kind
       * @enum {string}
       */
      kind: 'presence' | 'lighting' | 'socket' | 'power' | 'temperature' | 'illuminance' | 'co2'
      /** Manual Hold Scope */
      manual_hold_scope: 'backend_edge' | null
      /** Manual Hold Until */
      manual_hold_until: string | null
      /** Measurement Age Ms */
      measurement_age_ms: number | null
      /** Name */
      name: string
      /** Observation Id */
      observation_id: number | null
      /** Observed At */
      observed_at: string | null
      /**
       * Online Status
       * @enum {string}
       */
      online_status: 'online' | 'stale' | 'offline' | 'unknown'
      /**
       * Product Family
       * @enum {string}
       */
      product_family: 'PLUG' | 'SWITCH' | 'PRESENCE' | 'METER' | 'SENSOR'
      /**
       * Quality
       * @enum {string}
       */
      quality: 'good' | 'uncertain' | 'invalid' | 'stale' | 'unknown'
      /** Quality Flags */
      quality_flags: string[]
      /** Received At */
      received_at: string | null
      /**
       * Source Mode
       * @enum {string}
       */
      source_mode: 'SIMULATED' | 'REPLAYED' | 'REAL' | 'UNKNOWN' | 'MIXED'
      /** Source Version */
      source_version: string | null
      /**
       * Time Basis
       * @enum {string}
       */
      time_basis: 'device_observed' | 'authenticated_relative_receipt' | 'received_only' | 'unknown'
      /** Unit */
      unit: string | null
      /** Valid Until */
      valid_until: string | null
      value: components['schemas']['ChannelValue'] | null
      /**
       * Verification Kind
       * @enum {string}
       */
      verification_kind: 'independent_feedback' | 'actuator_reported_only' | 'not_applicable'
    }
    /** ChannelValue */
    ChannelValue: {
      /** Active Power W */
      active_power_w?: number | null
      /** Actuator Reported On */
      actuator_reported_on?: boolean | null
      /** Desired On */
      desired_on?: boolean | null
      /** Fault Latched */
      fault_latched?: boolean | null
      /** Number */
      number?: number | null
      /** Occupancy */
      occupancy?: ('occupied' | 'vacant' | 'unknown') | null
      /** Output Present */
      output_present?: boolean | null
    }
    /** CircuitIn */
    CircuitIn: {
      /** Building Id */
      building_id?: string | null
      /** Campus Id */
      campus_id: string
      /** Id */
      id: string
      /**
       * Kind
       * @default branch
       * @enum {string}
       */
      kind: 'main' | 'branch' | 'load'
      /** Name */
      name: string
      /** Parent Id */
      parent_id?: string | null
      /**
       * Source Mode
       * @default SIMULATED
       * @enum {string}
       */
      source_mode: 'SIMULATED' | 'REPLAYED' | 'REAL'
      /** Space Id */
      space_id?: string | null
    }
    /** CircuitPatch */
    CircuitPatch: {
      /** Name */
      name?: string | null
      /** Parent Id */
      parent_id?: string | null
    }
    /** CommandHistoryResponse */
    CommandHistoryResponse: {
      /**
       * At
       * Format: date-time
       */
      at: string
      /** Evidence */
      evidence: {
        [key: string]: components['schemas']['JsonValue']
      }
      /** Reason */
      reason: string
      /**
       * Status
       * @enum {string}
       */
      status:
        | 'requested'
        | 'dispatched'
        | 'acknowledged'
        | 'verified'
        | 'acknowledged_unverified'
        | 'rejected'
        | 'failed'
        | 'timed_out'
    }
    /** CommandIn */
    CommandIn: {
      /**
       * Action
       * @enum {string}
       */
      action: 'hold' | 'shed' | 'restore'
      /** Channel Id */
      channel_id?: string | null
      /** Device Id */
      device_id: string
      /**
       * Expires In Seconds
       * @default 30
       */
      expires_in_seconds: number
      /** Manual Hold Seconds */
      manual_hold_seconds?: number | null
      physical_confirmation?: components['schemas']['PhysicalConfirmation'] | null
      /** Reason */
      reason: string
      /**
       * Simulation Scenario
       * @default success
       * @enum {string}
       */
      simulation_scenario: 'success' | 'reject' | 'fail' | 'timeout'
    }
    /** CommandResponse */
    CommandResponse: {
      /**
       * Action
       * @enum {string}
       */
      action: 'hold' | 'shed' | 'restore'
      /** Building Id */
      building_id: string | null
      /** Campus Id */
      campus_id: string
      /** Channel Id */
      channel_id: string | null
      /** Channel Key */
      channel_key: string
      /** Created By */
      created_by: string
      /** Delivery Receipt */
      delivery_receipt: {
        [key: string]: components['schemas']['JsonValue']
      } | null
      /** Device Id */
      device_id: string
      /**
       * Dispatch Mode
       * @enum {string}
       */
      dispatch_mode: 'IN_PROCESS' | 'VIRTUAL' | 'PHYSICAL' | 'DISABLED'
      /** Expected Boot Epoch */
      expected_boot_epoch: string | null
      /**
       * Expires At
       * Format: date-time
       */
      expires_at: string
      /** History */
      history: components['schemas']['CommandHistoryResponse'][]
      /** Id */
      id: string
      /** Idempotency Key */
      idempotency_key: string
      /**
       * Issued At
       * Format: date-time
       */
      issued_at: string
      /** Lease Expires At */
      lease_expires_at: string | null
      /** Lease Id */
      lease_id: string | null
      /** Manual Hold Seconds */
      manual_hold_seconds: number | null
      /**
       * Product Family
       * @enum {string}
       */
      product_family: 'PLUG' | 'SWITCH'
      /** Profile Revision */
      profile_revision: number
      /** Reason */
      reason: string
      result: components['schemas']['CommandResultResponse'] | null
      /**
       * Sequence
       * @description Exact unsigned 64-bit counter encoded as a canonical decimal string, never a JSON number
       */
      sequence: string
      /**
       * Simulation Scenario
       * @enum {string}
       */
      simulation_scenario: 'success' | 'reject' | 'fail' | 'timeout'
      /**
       * Source Mode
       * @enum {string}
       */
      source_mode: 'SIMULATED' | 'REPLAYED' | 'REAL'
      /**
       * Status
       * @enum {string}
       */
      status:
        | 'requested'
        | 'dispatched'
        | 'acknowledged'
        | 'verified'
        | 'acknowledged_unverified'
        | 'rejected'
        | 'failed'
        | 'timed_out'
    }
    /** CommandResultResponse */
    CommandResultResponse: {
      /** Boot Epoch */
      boot_epoch: string
      /** Desired On */
      desired_on: boolean
      /** Observation Id */
      observation_id: number
      /**
       * Observed At
       * Format: date-time
       */
      observed_at: string
      /** Output Present */
      output_present: boolean
      /**
       * Sequence
       * @description Exact unsigned 64-bit counter encoded as a canonical decimal string, never a JSON number
       */
      sequence: string
      /** Simulated */
      simulated: boolean
      /**
       * Voltage Absence Proven
       * @constant
       */
      voltage_absence_proven: false
    }
    /** CommissioningIn */
    CommissioningIn: {
      /** Calibration Ref */
      calibration_ref: string
      /** Hardware Revision */
      hardware_revision: string
      /** Id */
      id: string
      /** Installation Approval Ref */
      installation_approval_ref: string
      /** Load Id */
      load_id: string
      /** Load Name */
      load_name: string
      /** Profile Id */
      profile_id: string
      /** Safety Assessment Ref */
      safety_assessment_ref: string
      /**
       * Valid Until
       * Format: date-time
       */
      valid_until: string
    }
    /** ControlEligibilityResponse */
    ControlEligibilityResponse: {
      /** Allowed Actions */
      allowed_actions: ('hold' | 'shed' | 'restore')[]
      /** Channel Id */
      channel_id?: string | null
      /**
       * Channel Key
       * @default relay.1
       */
      channel_key: string
      /**
       * Checked At
       * Format: date-time
       */
      checked_at: string
      /** Consequence */
      consequence: string
      /** Device Id */
      device_id: string
      /** Device Name */
      device_name: string
      /**
       * Dispatch Mode
       * @enum {string}
       */
      dispatch_mode: 'IN_PROCESS' | 'VIRTUAL' | 'PHYSICAL' | 'DISABLED'
      /** Eligible */
      eligible: boolean
      load: components['schemas']['ControlLoadResponse']
      /** Physical Deployment Enabled */
      physical_deployment_enabled: boolean
      /**
       * Product Family
       * @default PLUG
       * @enum {string}
       */
      product_family: 'PLUG' | 'SWITCH'
      /** Profile Revision */
      profile_revision: number
      reasons: components['schemas']['ControlReasonsResponse']
      release: components['schemas']['ControlReleaseResponse'] | null
      /**
       * Server Rechecks On Submission And Lease
       * @constant
       */
      server_rechecks_on_submission_and_lease: true
      /**
       * Source Mode
       * @enum {string}
       */
      source_mode: 'SIMULATED' | 'REPLAYED' | 'REAL'
      /**
       * Verification Kind
       * @default independent_feedback
       * @enum {string}
       */
      verification_kind: 'independent_feedback' | 'actuator_reported_only'
    }
    /** ControlLoadResponse */
    ControlLoadResponse: {
      /** Id */
      id: string | null
      /** Name */
      name: string | null
      /** Profile Id */
      profile_id: string
    }
    /** ControlReasonsResponse */
    ControlReasonsResponse: {
      /** Hold */
      hold: string | null
      /** Restore */
      restore: string | null
      /** Shed */
      shed: string | null
    }
    /** ControlReleaseResponse */
    ControlReleaseResponse: {
      /**
       * Basis
       * @constant
       */
      basis: 'operator_attestation'
      /** Id */
      id: string
      /** Status */
      status: string
      /**
       * Valid Until
       * Format: date-time
       */
      valid_until: string
    }
    /** CostSummaryResponse */
    CostSummaryResponse: {
      /** Allocation Method */
      allocation_method?: string | null
      /** Amount */
      amount: number | null
      /** Boundary Estimated Intervals */
      boundary_estimated_intervals: number
      /** Boundary Unresolved Intervals */
      boundary_unresolved_intervals: number | null
      /**
       * Charge Type
       * @constant
       */
      charge_type: 'configured_energy_charge_estimate'
      /** Coverage Ratio */
      coverage_ratio: number | null
      /** Currency */
      currency: string | null
      /** Derived Price Windows */
      derived_price_windows?: number | null
      /** Device Count */
      device_count: number
      /** Excluded Components */
      excluded_components: string[]
      /** Excluded Intervals */
      excluded_intervals: number
      /** Export Kwh */
      export_kwh: number | null
      /** Interval Count */
      interval_count: number
      /** Known Kwh */
      known_kwh: number | null
      /** Method */
      method: string
      /**
       * Period End
       * Format: date-time
       */
      period_end: string
      /**
       * Period Start
       * Format: date-time
       */
      period_start: string
      /** Pricing Coverage Ratio */
      pricing_coverage_ratio: number | null
      pricing_error?: components['schemas']['PricingError'] | null
      /**
       * Pricing Mode
       * @enum {string}
       */
      pricing_mode: 'strict' | 'proportional_estimate'
      /** Quality */
      quality: string
      /** Queried Sample Count */
      queried_sample_count: number
      /** Selected Device Ids */
      selected_device_ids: string[]
      /**
       * Settlement Bill
       * @constant
       */
      settlement_bill: false
      /**
       * Source Mode
       * @enum {string}
       */
      source_mode: 'SIMULATED' | 'REPLAYED' | 'REAL' | 'UNKNOWN' | 'MIXED'
      tariff: components['schemas']['TariffResponse'] | null
      /** Tariff Id */
      tariff_id: string | null
      /** Tariffs Used */
      tariffs_used: string[]
      /** Warnings */
      warnings: string[]
    }
    /** DeliveryIn */
    DeliveryIn: {
      /** Lease Id */
      lease_id: string
      /**
       * Reason
       * @default
       */
      reason: string
      /**
       * Status
       * @enum {string}
       */
      status: 'published' | 'failed' | 'expired'
    }
    /** DeviceDetailResponse */
    DeviceDetailResponse: {
      /** Allow Control */
      allow_control: boolean
      /** Binding History */
      binding_history: components['schemas']['BindingResponse'][]
      /** Building Id */
      building_id: string | null
      /** Campus Id */
      campus_id: string
      /** Capabilities */
      capabilities: string[]
      /** Circuit Id */
      circuit_id: string | null
      /** Command Count */
      command_count: number
      /** Commissioned */
      commissioned: boolean
      /**
       * Created At
       * Format: date-time
       */
      created_at: string
      /** Critical */
      critical: boolean
      /**
       * Dispatch Mode
       * @enum {string}
       */
      dispatch_mode: 'IN_PROCESS' | 'VIRTUAL' | 'PHYSICAL' | 'DISABLED'
      /** Floor Id */
      floor_id: string | null
      /** Id */
      id: string
      /**
       * Kind
       * @enum {string}
       */
      kind: 'smart_plug' | 'meter' | 'sensor' | 'switch' | 'presence' | 'light'
      /** Last Seen At */
      last_seen_at: string | null
      latest: components['schemas']['TelemetryResponse'] | null
      /** Minimum Dwell Seconds */
      minimum_dwell_seconds: number
      /** Name */
      name: string
      /** Physical Release Id */
      physical_release_id: string | null
      /** Profile Id */
      profile_id: string
      /** Profile Revision */
      profile_revision: number
      /** Provenance */
      provenance: {
        [key: string]: components['schemas']['JsonValue']
      }
      /**
       * Source Mode
       * @enum {string}
       */
      source_mode: 'SIMULATED' | 'REPLAYED' | 'REAL'
      /** Space Id */
      space_id: string | null
      /**
       * Status
       * @enum {string}
       */
      status: 'online' | 'stale' | 'offline' | 'unknown'
      /**
       * Updated At
       * Format: date-time
       */
      updated_at: string
    }
    /** DeviceIn */
    DeviceIn: {
      /**
       * Allow Control
       * @default false
       */
      allow_control: boolean
      /** Building Id */
      building_id?: string | null
      /** Campus Id */
      campus_id: string
      /** Capabilities */
      capabilities?: (
        | 'metering'
        | 'temperature'
        | 'hold'
        | 'shed'
        | 'restore'
        | 'presence'
        | 'lighting'
        | 'illuminance'
        | 'co2'
        | 'relay_feedback'
      )[]
      /** Circuit Id */
      circuit_id?: string | null
      /**
       * Critical
       * @default true
       */
      critical: boolean
      /** Floor Id */
      floor_id?: string | null
      /** Id */
      id: string
      /**
       * Kind
       * @default smart_plug
       * @enum {string}
       */
      kind: 'smart_plug' | 'meter' | 'sensor' | 'switch' | 'presence' | 'light'
      /** Name */
      name: string
      /**
       * Source Mode
       * @enum {string}
       */
      source_mode: 'SIMULATED' | 'REPLAYED' | 'REAL'
      /** Space Id */
      space_id?: string | null
    }
    /** DevicePatch */
    DevicePatch: {
      /** Allow Control */
      allow_control?: boolean | null
      /** Commissioned */
      commissioned?: boolean | null
      /** Critical */
      critical?: boolean | null
      /** Dispatch Mode */
      dispatch_mode?: ('IN_PROCESS' | 'VIRTUAL' | 'DISABLED') | null
      /** Name */
      name?: string | null
    }
    /** DeviceResponse */
    DeviceResponse: {
      /** Allow Control */
      allow_control: boolean
      /** Building Id */
      building_id: string | null
      /** Campus Id */
      campus_id: string
      /** Capabilities */
      capabilities: string[]
      /** Circuit Id */
      circuit_id: string | null
      /** Commissioned */
      commissioned: boolean
      /**
       * Created At
       * Format: date-time
       */
      created_at: string
      /** Critical */
      critical: boolean
      /**
       * Dispatch Mode
       * @enum {string}
       */
      dispatch_mode: 'IN_PROCESS' | 'VIRTUAL' | 'PHYSICAL' | 'DISABLED'
      /** Floor Id */
      floor_id: string | null
      /** Id */
      id: string
      /**
       * Kind
       * @enum {string}
       */
      kind: 'smart_plug' | 'meter' | 'sensor' | 'switch' | 'presence' | 'light'
      /** Last Seen At */
      last_seen_at: string | null
      latest: components['schemas']['TelemetryResponse'] | null
      /** Minimum Dwell Seconds */
      minimum_dwell_seconds: number
      /** Name */
      name: string
      /** Physical Release Id */
      physical_release_id: string | null
      /** Profile Id */
      profile_id: string
      /** Profile Revision */
      profile_revision: number
      /** Provenance */
      provenance: {
        [key: string]: components['schemas']['JsonValue']
      }
      /**
       * Source Mode
       * @enum {string}
       */
      source_mode: 'SIMULATED' | 'REPLAYED' | 'REAL'
      /** Space Id */
      space_id: string | null
      /**
       * Status
       * @enum {string}
       */
      status: 'online' | 'stale' | 'offline' | 'unknown'
      /**
       * Updated At
       * Format: date-time
       */
      updated_at: string
    }
    /** DispatchIn */
    DispatchIn: {
      /** Evaluation Id */
      evaluation_id: string
      /** Reason */
      reason: string
    }
    /** DistributionGroup */
    DistributionGroup: {
      durations?: components['schemas']['StateDurations'] | null
      /** Id */
      id: string
      /** Known Power Rooms */
      known_power_rooms: number
      /** Lighting */
      lighting: {
        [key: string]: number
      }
      /** Name */
      name: string
      /** Observed Power W */
      observed_power_w: number | null
      /** Occupancy */
      occupancy: {
        [key: string]: number
      }
      /** Room Count */
      room_count: number
      /** Sockets */
      sockets: {
        [key: string]: number
      }
      /** Source Modes */
      source_modes: string[]
    }
    /** DistributionResponse */
    DistributionResponse: {
      /**
       * At
       * Format: date-time
       */
      at: string
      /** End */
      end: string | null
      /**
       * Group By
       * @enum {string}
       */
      group_by: 'campus' | 'building' | 'floor'
      /** Groups */
      groups: components['schemas']['DistributionGroup'][]
      /** Semantics */
      semantics: string
      /** Source Modes */
      source_modes: string[]
      /** Start */
      start: string | null
      /** Total Rooms */
      total_rooms: number
    }
    /** EnergyBalanceResponse */
    EnergyBalanceResponse: {
      /** Children Kwh */
      children_kwh: number | null
      /** Parent Kwh */
      parent_kwh: number | null
      /** Quality */
      quality: string
      /** Residual Kwh */
      residual_kwh: number | null
      /** Warnings */
      warnings: string[]
    }
    /** EnergyBreakdownResponse */
    EnergyBreakdownResponse: {
      /** Coverage Ratio */
      coverage_ratio: number
      /** Device Count */
      device_count: number
      /** Id */
      id: string | null
      /** Known Kwh */
      known_kwh: number | null
      /** Name */
      name: string
      /** Quality */
      quality: string
      /**
       * Source Mode
       * @enum {string}
       */
      source_mode: 'SIMULATED' | 'REPLAYED' | 'REAL' | 'UNKNOWN' | 'MIXED'
    }
    /** EnergySummaryResponse */
    EnergySummaryResponse: {
      /** Coverage Ratio */
      coverage_ratio: number | null
      /** Device Count */
      device_count: number
      /** Excluded Intervals */
      excluded_intervals: number
      /** Export Kwh */
      export_kwh: number | null
      /** Interval Count */
      interval_count: number
      /** Known Kwh */
      known_kwh: number | null
      /** Method */
      method: string
      /**
       * Period End
       * Format: date-time
       */
      period_end: string
      /**
       * Period Start
       * Format: date-time
       */
      period_start: string
      /** Quality */
      quality: string
      /** Queried Sample Count */
      queried_sample_count: number
      /** Selected Device Ids */
      selected_device_ids: string[]
      /**
       * Source Mode
       * @enum {string}
       */
      source_mode: 'SIMULATED' | 'REPLAYED' | 'REAL' | 'UNKNOWN' | 'MIXED'
      /** Warnings */
      warnings: string[]
    }
    /** Envelope[AnomalyResponse] */
    Envelope_AnomalyResponse_: {
      data: components['schemas']['AnomalyResponse']
      /** Meta */
      meta?: {
        [key: string]: components['schemas']['JsonValue']
      } | null
    }
    /** Envelope[AnomalyRuleResponse] */
    Envelope_AnomalyRuleResponse_: {
      data: components['schemas']['AnomalyRuleResponse']
      /** Meta */
      meta?: {
        [key: string]: components['schemas']['JsonValue']
      } | null
    }
    /** Envelope[AuthResponse] */
    Envelope_AuthResponse_: {
      data: components['schemas']['AuthResponse']
      /** Meta */
      meta?: {
        [key: string]: components['schemas']['JsonValue']
      } | null
    }
    /** Envelope[CarbonSummaryResponse] */
    Envelope_CarbonSummaryResponse_: {
      data: components['schemas']['CarbonSummaryResponse']
      /** Meta */
      meta?: {
        [key: string]: components['schemas']['JsonValue']
      } | null
    }
    /** Envelope[ChannelBatchReceipt] */
    Envelope_ChannelBatchReceipt_: {
      data: components['schemas']['ChannelBatchReceipt']
      /** Meta */
      meta?: {
        [key: string]: components['schemas']['JsonValue']
      } | null
    }
    /** Envelope[ChannelDefinition] */
    Envelope_ChannelDefinition_: {
      data: components['schemas']['ChannelDefinition']
      /** Meta */
      meta?: {
        [key: string]: components['schemas']['JsonValue']
      } | null
    }
    /** Envelope[CommandResponse] */
    Envelope_CommandResponse_: {
      data: components['schemas']['CommandResponse']
      /** Meta */
      meta?: {
        [key: string]: components['schemas']['JsonValue']
      } | null
    }
    /** Envelope[ControlEligibilityResponse] */
    Envelope_ControlEligibilityResponse_: {
      data: components['schemas']['ControlEligibilityResponse']
      /** Meta */
      meta?: {
        [key: string]: components['schemas']['JsonValue']
      } | null
    }
    /** Envelope[CostSummaryResponse] */
    Envelope_CostSummaryResponse_: {
      data: components['schemas']['CostSummaryResponse']
      /** Meta */
      meta?: {
        [key: string]: components['schemas']['JsonValue']
      } | null
    }
    /** Envelope[DeviceDetailResponse] */
    Envelope_DeviceDetailResponse_: {
      data: components['schemas']['DeviceDetailResponse']
      /** Meta */
      meta?: {
        [key: string]: components['schemas']['JsonValue']
      } | null
    }
    /** Envelope[DeviceResponse] */
    Envelope_DeviceResponse_: {
      data: components['schemas']['DeviceResponse']
      /** Meta */
      meta?: {
        [key: string]: components['schemas']['JsonValue']
      } | null
    }
    /** Envelope[DistributionResponse] */
    Envelope_DistributionResponse_: {
      data: components['schemas']['DistributionResponse']
      /** Meta */
      meta?: {
        [key: string]: components['schemas']['JsonValue']
      } | null
    }
    /** Envelope[EnergyBalanceResponse] */
    Envelope_EnergyBalanceResponse_: {
      data: components['schemas']['EnergyBalanceResponse']
      /** Meta */
      meta?: {
        [key: string]: components['schemas']['JsonValue']
      } | null
    }
    /** Envelope[EnergySummaryResponse] */
    Envelope_EnergySummaryResponse_: {
      data: components['schemas']['EnergySummaryResponse']
      /** Meta */
      meta?: {
        [key: string]: components['schemas']['JsonValue']
      } | null
    }
    /** Envelope[EvaluationResponse] */
    Envelope_EvaluationResponse_: {
      data: components['schemas']['EvaluationResponse']
      /** Meta */
      meta?: {
        [key: string]: components['schemas']['JsonValue']
      } | null
    }
    /** Envelope[FactorResponse] */
    Envelope_FactorResponse_: {
      data: components['schemas']['FactorResponse']
      /** Meta */
      meta?: {
        [key: string]: components['schemas']['JsonValue']
      } | null
    }
    /** Envelope[ForecastResponse] */
    Envelope_ForecastResponse_: {
      data: components['schemas']['ForecastResponse']
      /** Meta */
      meta?: {
        [key: string]: components['schemas']['JsonValue']
      } | null
    }
    /** Envelope[IoTAckReceipt] */
    Envelope_IoTAckReceipt_: {
      data: components['schemas']['IoTAckReceipt']
      /** Meta */
      meta?: {
        [key: string]: components['schemas']['JsonValue']
      } | null
    }
    /** Envelope[IoTEventReceipt] */
    Envelope_IoTEventReceipt_: {
      data: components['schemas']['IoTEventReceipt']
      /** Meta */
      meta?: {
        [key: string]: components['schemas']['JsonValue']
      } | null
    }
    /** Envelope[LogoutResponse] */
    Envelope_LogoutResponse_: {
      data: components['schemas']['LogoutResponse']
      /** Meta */
      meta?: {
        [key: string]: components['schemas']['JsonValue']
      } | null
    }
    /** Envelope[ModeResponse] */
    Envelope_ModeResponse_: {
      data: components['schemas']['ModeResponse']
      /** Meta */
      meta?: {
        [key: string]: components['schemas']['JsonValue']
      } | null
    }
    /** Envelope[PolicyResponse] */
    Envelope_PolicyResponse_: {
      data: components['schemas']['PolicyResponse']
      /** Meta */
      meta?: {
        [key: string]: components['schemas']['JsonValue']
      } | null
    }
    /** Envelope[RoomSnapshot] */
    Envelope_RoomSnapshot_: {
      data: components['schemas']['RoomSnapshot']
      /** Meta */
      meta?: {
        [key: string]: components['schemas']['JsonValue']
      } | null
    }
    /** Envelope[TariffResponse] */
    Envelope_TariffResponse_: {
      data: components['schemas']['TariffResponse']
      /** Meta */
      meta?: {
        [key: string]: components['schemas']['JsonValue']
      } | null
    }
    /** Envelope[TimelineResponse] */
    Envelope_TimelineResponse_: {
      data: components['schemas']['TimelineResponse']
      /** Meta */
      meta?: {
        [key: string]: components['schemas']['JsonValue']
      } | null
    }
    /** Envelope[list[AnomalyResponse]] */
    Envelope_list_AnomalyResponse__: {
      /** Data */
      data: components['schemas']['AnomalyResponse'][]
      /** Meta */
      meta?: {
        [key: string]: components['schemas']['JsonValue']
      } | null
    }
    /** Envelope[list[AnomalyRuleResponse]] */
    Envelope_list_AnomalyRuleResponse__: {
      /** Data */
      data: components['schemas']['AnomalyRuleResponse'][]
      /** Meta */
      meta?: {
        [key: string]: components['schemas']['JsonValue']
      } | null
    }
    /** Envelope[list[ChannelSnapshot]] */
    Envelope_list_ChannelSnapshot__: {
      /** Data */
      data: components['schemas']['ChannelSnapshot'][]
      /** Meta */
      meta?: {
        [key: string]: components['schemas']['JsonValue']
      } | null
    }
    /** Envelope[list[CommandResponse]] */
    Envelope_list_CommandResponse__: {
      /** Data */
      data: components['schemas']['CommandResponse'][]
      /** Meta */
      meta?: {
        [key: string]: components['schemas']['JsonValue']
      } | null
    }
    /** Envelope[list[DeviceResponse]] */
    Envelope_list_DeviceResponse__: {
      /** Data */
      data: components['schemas']['DeviceResponse'][]
      /** Meta */
      meta?: {
        [key: string]: components['schemas']['JsonValue']
      } | null
    }
    /** Envelope[list[EnergyBreakdownResponse]] */
    Envelope_list_EnergyBreakdownResponse__: {
      /** Data */
      data: components['schemas']['EnergyBreakdownResponse'][]
      /** Meta */
      meta?: {
        [key: string]: components['schemas']['JsonValue']
      } | null
    }
    /** Envelope[list[EvaluationResponse]] */
    Envelope_list_EvaluationResponse__: {
      /** Data */
      data: components['schemas']['EvaluationResponse'][]
      /** Meta */
      meta?: {
        [key: string]: components['schemas']['JsonValue']
      } | null
    }
    /** Envelope[list[FactorResponse]] */
    Envelope_list_FactorResponse__: {
      /** Data */
      data: components['schemas']['FactorResponse'][]
      /** Meta */
      meta?: {
        [key: string]: components['schemas']['JsonValue']
      } | null
    }
    /** Envelope[list[ModeResponse]] */
    Envelope_list_ModeResponse__: {
      /** Data */
      data: components['schemas']['ModeResponse'][]
      /** Meta */
      meta?: {
        [key: string]: components['schemas']['JsonValue']
      } | null
    }
    /** Envelope[list[PolicyResponse]] */
    Envelope_list_PolicyResponse__: {
      /** Data */
      data: components['schemas']['PolicyResponse'][]
      /** Meta */
      meta?: {
        [key: string]: components['schemas']['JsonValue']
      } | null
    }
    /** Envelope[list[RoomSnapshot]] */
    Envelope_list_RoomSnapshot__: {
      /** Data */
      data: components['schemas']['RoomSnapshot'][]
      /** Meta */
      meta?: {
        [key: string]: components['schemas']['JsonValue']
      } | null
    }
    /** Envelope[list[TariffResponse]] */
    Envelope_list_TariffResponse__: {
      /** Data */
      data: components['schemas']['TariffResponse'][]
      /** Meta */
      meta?: {
        [key: string]: components['schemas']['JsonValue']
      } | null
    }
    /** Envelope[list[TelemetryResponse]] */
    Envelope_list_TelemetryResponse__: {
      /** Data */
      data: components['schemas']['TelemetryResponse'][]
      /** Meta */
      meta?: {
        [key: string]: components['schemas']['JsonValue']
      } | null
    }
    /** ErrorDetails */
    ErrorDetails: {
      /** Code */
      code: string
      details?: components['schemas']['JsonValue']
      /** Message */
      message: string
      /** Request Id */
      request_id: string
    }
    /** ErrorEnvelope */
    ErrorEnvelope: {
      error: components['schemas']['ErrorDetails']
    }
    /** EvaluateAnomaliesIn */
    EvaluateAnomaliesIn: {
      /** Building Id */
      building_id?: string | null
      /** Campus Id */
      campus_id?: string | null
      /** Space Id */
      space_id?: string | null
    }
    /** EvaluationContent */
    EvaluationContent: {
      /** Eligible Count */
      eligible_count: number
      /** Explanation */
      explanation: string
      /**
       * Mode
       * @enum {string}
       */
      mode: 'manual' | 'automatic' | 'maintenance' | 'fault'
      /** Modeled Reduction W */
      modeled_reduction_w: number | null
      /**
       * Occupancy
       * @enum {string}
       */
      occupancy: 'occupied' | 'vacant' | 'unknown'
      /**
       * Savings Claim
       * @default false
       * @constant
       */
      savings_claim: false
      /**
       * Source Mode
       * @enum {string}
       */
      source_mode: 'SIMULATED' | 'MIXED' | 'UNKNOWN'
      /** Targets */
      targets: components['schemas']['EvaluationTarget'][]
      /** Vacancy Seconds */
      vacancy_seconds: number
    }
    /** EvaluationResponse */
    EvaluationResponse: {
      /**
       * At
       * Format: date-time
       */
      at: string
      /** Campus Id */
      campus_id: string
      /** Command Ids */
      command_ids: string[]
      /** Commands */
      commands: components['schemas']['CommandResponse'][]
      content: components['schemas']['EvaluationContent']
      /** Created By */
      created_by: string
      /** Dispatched At */
      dispatched_at: string | null
      /**
       * Execution Status
       * @enum {string}
       */
      execution_status:
        | 'shadow'
        | 'not_dispatched'
        | 'pending'
        | 'verified'
        | 'acknowledged_unverified'
        | 'partial'
        | 'failed'
      /** Failed Count */
      failed_count: number
      /** Id */
      id: string
      /** Pending Count */
      pending_count: number
      /** Policy Id */
      policy_id: string
      /** Policy Revision */
      policy_revision: number
      /** Space Id */
      space_id: string
      /** Unverified Count */
      unverified_count: number
      /** Verified Count */
      verified_count: number
    }
    /** EvaluationTarget */
    EvaluationTarget: {
      /** Aggregate Power W */
      aggregate_power_w?: number | null
      /** Blocked By */
      blocked_by: string[]
      /** Channel Id */
      channel_id: string
      /** Device Id */
      device_id: string | null
      /** Eligible */
      eligible: boolean
      /** Observed Power W */
      observed_power_w: number | null
    }
    /** FactorIn */
    FactorIn: {
      /** Id */
      id: string
      /** Kg Co2E Per Kwh */
      kg_co2e_per_kwh: number
      /** Name */
      name: string
      /** Region */
      region: string
      /**
       * Source Mode
       * @enum {string}
       */
      source_mode: 'SIMULATED' | 'REPLAYED' | 'REAL'
      /** Source Url */
      source_url: string
      /**
       * Valid From
       * Format: date-time
       */
      valid_from: string
      /**
       * Valid To
       * Format: date-time
       */
      valid_to: string
      /** Version */
      version: number
      /** Year */
      year: number
    }
    /** FactorResponse */
    FactorResponse: {
      /**
       * Created At
       * Format: date-time
       */
      created_at: string
      /** Id */
      id: string
      /** Kg Co2E Per Kwh */
      kg_co2e_per_kwh: number
      /** Name */
      name: string
      /** Region */
      region: string
      /**
       * Source Mode
       * @enum {string}
       */
      source_mode: 'SIMULATED' | 'REPLAYED' | 'REAL'
      /** Source Url */
      source_url: string
      /**
       * Valid From
       * Format: date-time
       */
      valid_from: string
      /**
       * Valid To
       * Format: date-time
       */
      valid_to: string
      /** Version */
      version: number
      /** Year */
      year: number
    }
    /** ForecastBacktestResponse */
    ForecastBacktestResponse: {
      /** Coverage Ratio */
      coverage_ratio: number | null
      /**
       * End
       * Format: date-time
       */
      end: string
      /** Expected Hours */
      expected_hours: number
      /** Folds */
      folds: components['schemas']['ForecastFoldResponse'][]
      models: components['schemas']['ForecastModelsResponse']
      /** Sample Count */
      sample_count: number
      /**
       * Start
       * Format: date-time
       */
      start: string
    }
    /** ForecastBandResponse */
    ForecastBandResponse: {
      /**
       * Guaranteed
       * @constant
       */
      guaranteed: false
      /**
       * Method
       * @constant
       */
      method: 'empirical_absolute_holdout_residual'
      /** Quantile */
      quantile: number
      /** Radius Kw */
      radius_kw: number | null
    }
    /** ForecastCoverageResponse */
    ForecastCoverageResponse: {
      /** Aggregated Rows */
      aggregated_rows?: number | null
      /** Complete Hours */
      complete_hours: number
      /** Device Ratio */
      device_ratio: number | null
      /** Eligible Device Count */
      eligible_device_count: number
      /** Eligible Device Ids */
      eligible_device_ids: string[]
      /** Excluded Devices */
      excluded_devices: components['schemas']['ForecastExcludedDeviceResponse'][]
      /** Excluded Records And Intervals */
      excluded_records_and_intervals: {
        [key: string]: number
      }
      /** Expected Hours */
      expected_hours: number
      /** Hour Ratio */
      hour_ratio: number | null
      /** Scope Complete */
      scope_complete: boolean
      /** Selected Device Count */
      selected_device_count: number
      /** Selected Device Ids */
      selected_device_ids: string[]
      /** Source Records */
      source_records: number | null
      /**
       * Window End
       * Format: date-time
       */
      window_end: string
      /**
       * Window Start
       * Format: date-time
       */
      window_start: string
    }
    /** ForecastEvaluationResponse */
    ForecastEvaluationResponse: {
      /** Cached */
      cached: boolean
      /** Completed At */
      completed_at: string | null
      /** Error Code */
      error_code: string | null
      /** Id */
      id: string | null
      /** Input Revision */
      input_revision: string | null
      /** Projection Pending Hours */
      projection_pending_hours: number
      /** Requested At */
      requested_at: string | null
      /** Result Input Revision */
      result_input_revision: string | null
      /** Retry After Seconds */
      retry_after_seconds: number
      /** Started At */
      started_at: string | null
      /**
       * Status
       * @enum {string}
       */
      status: 'queued' | 'running' | 'ready' | 'failed' | 'stale'
      /**
       * Worker Status
       * @enum {string}
       */
      worker_status: 'queued' | 'running' | 'ready' | 'failed'
    }
    /** ForecastExcludedDeviceResponse */
    ForecastExcludedDeviceResponse: {
      /** Device Id */
      device_id: string
      /** Reasons */
      reasons: string[]
    }
    /** ForecastFoldResponse */
    ForecastFoldResponse: {
      /**
       * Issued At
       * Format: date-time
       */
      issued_at: string
      /** Sample Count */
      sample_count: number
      /**
       * Target End
       * Format: date-time
       */
      target_end: string
      /**
       * Target Start
       * Format: date-time
       */
      target_start: string
      /** Training End */
      training_end: string | null
    }
    /** ForecastFreshnessResponse */
    ForecastFreshnessResponse: {
      /** Age Basis */
      age_basis: string
      /** Age Seconds */
      age_seconds: number | null
      /** Latest Complete Hour */
      latest_complete_hour: string | null
      /** Latest Sample At */
      latest_sample_at: string | null
      /** Oldest Cohort Sample At */
      oldest_cohort_sample_at: string | null
      /**
       * Status
       * @enum {string}
       */
      status: 'unknown' | 'fresh' | 'stale'
    }
    /** ForecastHoldoutResponse */
    ForecastHoldoutResponse: {
      band: components['schemas']['ForecastBandResponse']
      /** Baseline Improvement Pct */
      baseline_improvement_pct: number | null
      /** Coverage Ratio */
      coverage_ratio: number | null
      /**
       * End
       * Format: date-time
       */
      end: string
      /** Expected Hours */
      expected_hours: number
      /** Folds */
      folds: components['schemas']['ForecastFoldResponse'][]
      models: components['schemas']['ForecastModelsResponse']
      /** Protocol */
      protocol: string
      /** Sample Count */
      sample_count: number
      /**
       * Selected Method
       * @enum {string}
       */
      selected_method: 'seasonal_naive' | 'ridge_regression'
      /**
       * Selection Used Holdout
       * @constant
       */
      selection_used_holdout: false
      /**
       * Start
       * Format: date-time
       */
      start: string
    }
    /** ForecastMetricsResponse */
    ForecastMetricsResponse: {
      /** Mae Kw */
      mae_kw: number | null
      /** Rmse Kw */
      rmse_kw: number | null
    }
    /** ForecastModelResponse */
    ForecastModelResponse: {
      /**
       * Algorithm
       * @constant
       */
      algorithm: 'standardized_ridge_regression'
      /** Bridge Hours */
      bridge_hours?: number | null
      /** Calendar Timezone */
      calendar_timezone?: string | null
      /** Feature Centers */
      feature_centers?: number[] | null
      /** Feature Names */
      feature_names: string[]
      /** Feature Scales */
      feature_scales?: number[] | null
      /** Id */
      id?: string | null
      /** Intercept Kw */
      intercept_kw?: number | null
      /** Minimum History Hours */
      minimum_history_hours: number
      /** Outlier Policy */
      outlier_policy?: string | null
      /** Prediction Origin */
      prediction_origin?: string | null
      /** Prediction Upper Cap Kw */
      prediction_upper_cap_kw?: number | null
      /** Ridge Alpha */
      ridge_alpha: number
      /**
       * Selected Method
       * @enum {string}
       */
      selected_method: 'seasonal_naive' | 'ridge_regression'
      /** Selection Reason */
      selection_reason: string
      /** Standardized Coefficients */
      standardized_coefficients?: {
        [key: string]: number
      } | null
      /** Trained */
      trained: boolean
      /** Training Sample Count */
      training_sample_count: number
      /** Training Start */
      training_start?: string | null
      validation: components['schemas']['ForecastBacktestResponse'] | null
      /** Version */
      version: string
    }
    /** ForecastModelsResponse */
    ForecastModelsResponse: {
      ridge_regression: components['schemas']['ForecastMetricsResponse']
      seasonal_naive: components['schemas']['ForecastMetricsResponse']
    }
    /** ForecastPointResponse */
    ForecastPointResponse: {
      /** Lower Kw */
      lower_kw: number | null
      /** Predicted Kw */
      predicted_kw: number | null
      /**
       * Timestamp
       * Format: date-time
       */
      timestamp: string
      /** Upper Kw */
      upper_kw: number | null
    }
    /** ForecastProvenanceResponse */
    ForecastProvenanceResponse: {
      /** Aggregation */
      aggregation: string
      /** As Of Filters */
      as_of_filters: string[]
      /** Cache */
      cache: string
      /** Cohort Selection */
      cohort_selection?: string | null
      /**
       * Dispatch Performed
       * @constant
       */
      dispatch_performed: false
      /** External Features */
      external_features: string[]
      /** Hour Coverage Required */
      hour_coverage_required: number
      /** Maximum Gap Seconds */
      maximum_gap_seconds: {
        [key: string]: number
      }
      /** Maximum Trailing Forecast Bridge Hours */
      maximum_trailing_forecast_bridge_hours: number
      /**
       * Measured Savings Claim
       * @constant
       */
      measured_savings_claim: false
      /** Measurement */
      measurement: string
      /** Missing Values */
      missing_values: string
      /** Query Row Budget */
      query_row_budget: number
      /** Query Row Budget Unit */
      query_row_budget_unit: string
      /** Reader */
      reader?: string | null
      /**
       * Real Campus Accuracy Claim
       * @constant
       */
      real_campus_accuracy_claim: false
      /** Reverse Power */
      reverse_power: string
      /** Reverse Power Samples */
      reverse_power_samples?: number | null
      /** Source Modes */
      source_modes: ('SIMULATED' | 'REPLAYED' | 'REAL')[]
      /** Source Versions */
      source_versions: string[]
      /** Sql Dialect */
      sql_dialect?: string | null
      /**
       * Training Data
       * @enum {string}
       */
      training_data: 'SIMULATED' | 'REPLAYED' | 'REAL' | 'UNKNOWN' | 'MIXED'
    }
    /** ForecastRefreshIn */
    ForecastRefreshIn: {
      /** Building Id */
      building_id?: string | null
      /** Campus Id */
      campus_id?: string | null
      /**
       * Horizon Hours
       * @default 24
       */
      horizon_hours: number
    }
    /** ForecastResponse */
    ForecastResponse: {
      coverage: components['schemas']['ForecastCoverageResponse']
      evaluation?: components['schemas']['ForecastEvaluationResponse'] | null
      freshness: components['schemas']['ForecastFreshnessResponse']
      /**
       * Generated At
       * Format: date-time
       */
      generated_at: string
      holdout: components['schemas']['ForecastHoldoutResponse'] | null
      /** Mae Kw */
      mae_kw: number | null
      /**
       * Method
       * @enum {string}
       */
      method: 'seasonal_naive' | 'ridge_regression'
      model: components['schemas']['ForecastModelResponse']
      /** Points */
      points: components['schemas']['ForecastPointResponse'][]
      provenance: components['schemas']['ForecastProvenanceResponse']
      /**
       * Quality
       * @enum {string}
       */
      quality: 'insufficient_data' | 'model_estimate' | 'baseline_estimate' | 'partial_estimate'
      /** Rmse Kw */
      rmse_kw: number | null
      scope: components['schemas']['ForecastScopeResponse']
      /**
       * Source Mode
       * @enum {string}
       */
      source_mode: 'SIMULATED' | 'REPLAYED' | 'REAL' | 'UNKNOWN' | 'MIXED'
      /** Trained Until */
      trained_until: string | null
      /** Warnings */
      warnings: string[]
    }
    /** ForecastScopeResponse */
    ForecastScopeResponse: {
      /** Building Id */
      building_id: string | null
      /** Campus Id */
      campus_id: string | null
    }
    /** IngestIn */
    IngestIn: {
      /** Samples */
      samples: components['schemas']['TelemetryIn'][]
    }
    /** IoTAckReceipt */
    IoTAckReceipt: {
      /** Channel */
      channel: number
      /** Device Id */
      device_id: string
      /**
       * Durable
       * @constant
       */
      durable: true
      /** Id */
      id: string
      /**
       * Physical Verification
       * @constant
       */
      physical_verification: false
      /** Seq */
      seq: string
      /**
       * Status
       * @enum {string}
       */
      status: 'stored' | 'duplicate'
    }
    /** IoTEventReceipt */
    IoTEventReceipt: {
      /** Boot Id */
      boot_id: string
      /** Device Id */
      device_id: string
      /**
       * Durable
       * @constant
       */
      durable: true
      /** Event Id */
      event_id: string
      /** Sequence */
      sequence: string
      /**
       * Server Received At
       * Format: date-time
       */
      server_received_at: string
      /**
       * Status
       * @enum {string}
       */
      status: 'stored' | 'duplicate'
    }
    JsonValue: unknown
    /** LoginIn */
    LoginIn: {
      /** Password */
      password: string
      /** Username */
      username: string
    }
    /** LogoutResponse */
    LogoutResponse: {
      /**
       * Logged Out
       * @constant
       */
      logged_out: true
    }
    /** ModeIn */
    ModeIn: {
      /** Duration Seconds */
      duration_seconds?: number | null
      /**
       * Mode
       * @enum {string}
       */
      mode: 'manual' | 'automatic' | 'maintenance' | 'fault'
      /** Reason */
      reason: string
    }
    /** ModeResponse */
    ModeResponse: {
      /** Campus Id */
      campus_id: string
      /**
       * Created At
       * Format: date-time
       */
      created_at: string
      /** Created By */
      created_by: string
      /** Ends At */
      ends_at: string | null
      /** Id */
      id: string
      /**
       * Mode
       * @enum {string}
       */
      mode: 'manual' | 'automatic' | 'maintenance' | 'fault'
      /** Reason */
      reason: string
      /** Space Id */
      space_id: string
      /**
       * Starts At
       * Format: date-time
       */
      starts_at: string
    }
    /** NoteIn */
    NoteIn: {
      /**
       * Note
       * @default
       */
      note: string
    }
    /** PasswordIn */
    PasswordIn: {
      /** Password */
      password: string
    }
    /** PhysicalConfirmation */
    PhysicalConfirmation: {
      /**
       * Action
       * @enum {string}
       */
      action: 'hold' | 'shed' | 'restore'
      /** Device Id */
      device_id: string
      /** Load Id */
      load_id: string
      /** Profile Revision */
      profile_revision: number
      /** Release Id */
      release_id: string
      /** Understands Mains Consequence */
      understands_mains_consequence: boolean
    }
    /** PolicyConfig */
    PolicyConfig: {
      /**
       * Action
       * @constant
       */
      action: 'shed'
      /** Channel Ids */
      channel_ids: string[]
      /** Max Commands */
      max_commands: number
      /** Minimum Power W */
      minimum_power_w: number
      /** Reason */
      reason: string
      /** Vacant For Seconds */
      vacant_for_seconds: number
    }
    /** PolicyIn */
    PolicyIn: {
      /**
       * Action
       * @default shed
       * @constant
       */
      action: 'shed'
      /** Channel Ids */
      channel_ids: string[]
      /**
       * Enabled
       * @default true
       */
      enabled: boolean
      /**
       * Ends At
       * Format: date-time
       */
      ends_at: string
      /**
       * Max Commands
       * @default 5
       */
      max_commands: number
      /**
       * Minimum Power W
       * @default 5
       */
      minimum_power_w: number
      /**
       * Mode
       * @default SHADOW
       * @enum {string}
       */
      mode: 'SHADOW' | 'SIMULATED'
      /** Name */
      name: string
      /** Reason */
      reason: string
      /**
       * Starts At
       * Format: date-time
       */
      starts_at: string
      /**
       * Vacant For Seconds
       * @default 300
       */
      vacant_for_seconds: number
    }
    /** PolicyPatch */
    PolicyPatch: {
      /** Enabled */
      enabled: boolean
      /** Reason */
      reason: string
    }
    /** PolicyResponse */
    PolicyResponse: {
      /** Campus Id */
      campus_id: string
      config: components['schemas']['PolicyConfig']
      /**
       * Created At
       * Format: date-time
       */
      created_at: string
      /** Created By */
      created_by: string
      /** Enabled */
      enabled: boolean
      /**
       * Ends At
       * Format: date-time
       */
      ends_at: string
      /** Id */
      id: string
      /**
       * Mode
       * @enum {string}
       */
      mode: 'SHADOW' | 'SIMULATED'
      /** Name */
      name: string
      /** Revision */
      revision: number
      /** Space Id */
      space_id: string
      /**
       * Starts At
       * Format: date-time
       */
      starts_at: string
    }
    /** PricingError */
    PricingError: {
      /** Code */
      code: string
      details: components['schemas']['JsonValue']
      /** Message */
      message: string
    }
    /** RateBand */
    RateBand: {
      /** End Minute */
      end_minute: number
      /**
       * Label
       * @default
       */
      label: string
      /** Rate Per Kwh */
      rate_per_kwh: number
      /** Start Minute */
      start_minute: number
    }
    /** ReleaseIn */
    ReleaseIn: {
      /** Noncritical Load Attested */
      noncritical_load_attested: boolean
      /** Note */
      note: string
      /** Operator Attested */
      operator_attested: boolean
      /** Release Id */
      release_id: string
    }
    /** ReportIn */
    ReportIn: {
      /** Building Id */
      building_id?: string | null
      /** Campus Id */
      campus_id?: string | null
      /**
       * Cost Allocation Mode
       * @default strict
       * @enum {string}
       */
      cost_allocation_mode: 'strict' | 'proportional_estimate'
      /** End */
      end?: string | null
      /** Name */
      name: string
      /** Start */
      start?: string | null
      /**
       * Type
       * @enum {string}
       */
      type: 'energy' | 'carbon' | 'cost' | 'operations'
    }
    /** RequiredNote */
    RequiredNote: {
      /** Note */
      note: string
    }
    /** RoomInterval */
    RoomInterval: {
      /** Duration Seconds */
      duration_seconds: number
      /**
       * End
       * Format: date-time
       */
      end: string
      /**
       * Lighting
       * @enum {string}
       */
      lighting: 'on' | 'off' | 'mixed' | 'unknown'
      /**
       * Lighting Verification Kind
       * @enum {string}
       */
      lighting_verification_kind:
        | 'independent_feedback'
        | 'actuator_reported_only'
        | 'mixed'
        | 'unknown'
      /**
       * Mode
       * @enum {string}
       */
      mode: 'manual' | 'automatic' | 'maintenance' | 'fault'
      /** Observation Ids */
      observation_ids: number[]
      /** Observed Power W */
      observed_power_w: number | null
      /**
       * Occupancy
       * @enum {string}
       */
      occupancy: 'occupied' | 'vacant' | 'unknown'
      /** Power Coverage */
      power_coverage: number
      /**
       * Quality
       * @enum {string}
       */
      quality: 'good' | 'partial' | 'unknown'
      /**
       * Sockets
       * @enum {string}
       */
      sockets: 'on' | 'off' | 'mixed' | 'unknown'
      /**
       * Source Mode
       * @enum {string}
       */
      source_mode: 'SIMULATED' | 'REPLAYED' | 'REAL' | 'UNKNOWN' | 'MIXED'
      /**
       * Start
       * Format: date-time
       */
      start: string
    }
    /** RoomSnapshot */
    RoomSnapshot: {
      /** Active Anomaly Ids */
      active_anomaly_ids: string[]
      /**
       * At
       * Format: date-time
       */
      at: string
      /** Building Id */
      building_id: string
      /** Campus Id */
      campus_id: string
      /** Channels */
      channels: components['schemas']['ChannelSnapshot'][]
      /**
       * Control Authorization
       * @default false
       * @constant
       */
      control_authorization: false
      /** Floor Id */
      floor_id: string | null
      /** Id */
      id: string
      /** Kind */
      kind: string
      /**
       * Lighting
       * @enum {string}
       */
      lighting: 'on' | 'off' | 'mixed' | 'unknown'
      /**
       * Lighting Verification Kind
       * @enum {string}
       */
      lighting_verification_kind:
        | 'independent_feedback'
        | 'actuator_reported_only'
        | 'mixed'
        | 'unknown'
      /**
       * Mode
       * @enum {string}
       */
      mode: 'manual' | 'automatic' | 'maintenance' | 'fault'
      /** Mode Expires At */
      mode_expires_at: string | null
      /** Mode Reason */
      mode_reason: string | null
      /** Name */
      name: string
      /** Observed Power W */
      observed_power_w: number | null
      /**
       * Occupancy
       * @enum {string}
       */
      occupancy: 'occupied' | 'vacant' | 'unknown'
      /** Planned Occupancy */
      planned_occupancy: number | null
      /** Power Coverage */
      power_coverage: number
      /**
       * Quality
       * @enum {string}
       */
      quality: 'good' | 'partial' | 'unknown'
      /** Scheduled Titles */
      scheduled_titles: string[]
      /**
       * Sockets
       * @enum {string}
       */
      sockets: 'on' | 'off' | 'mixed' | 'unknown'
      /**
       * Source Mode
       * @enum {string}
       */
      source_mode: 'SIMULATED' | 'REPLAYED' | 'REAL' | 'UNKNOWN' | 'MIXED'
    }
    /** ScheduleImport */
    ScheduleImport: {
      /** Events */
      events: components['schemas']['ScheduleIn'][]
    }
    /** ScheduleIn */
    ScheduleIn: {
      /** Building Id */
      building_id?: string | null
      /** Campus Id */
      campus_id: string
      /**
       * Ends At
       * Format: date-time
       */
      ends_at: string
      /**
       * Kind
       * @enum {string}
       */
      kind: 'teaching' | 'holiday' | 'event' | 'maintenance'
      /** Planned Occupancy */
      planned_occupancy?: number | null
      /** Source */
      source: string
      /**
       * Source Mode
       * @enum {string}
       */
      source_mode: 'SIMULATED' | 'REFERENCE'
      /** Space Id */
      space_id?: string | null
      /**
       * Starts At
       * Format: date-time
       */
      starts_at: string
      /** Title */
      title: string
    }
    /** SettingsPatch */
    SettingsPatch: {
      /** Offline After Seconds */
      offline_after_seconds?: number | null
      /** Stale After Seconds */
      stale_after_seconds?: number | null
    }
    /** StateDurations */
    StateDurations: {
      /** Lighting */
      lighting: {
        [key: string]: number
      }
      /** Mode */
      mode: {
        [key: string]: number
      }
      /** Observed Power Seconds */
      observed_power_seconds: number
      /** Occupancy */
      occupancy: {
        [key: string]: number
      }
      /** Sockets */
      sockets: {
        [key: string]: number
      }
      /** Unknown Power Seconds */
      unknown_power_seconds: number
    }
    /** StrategyIn */
    StrategyIn: {
      /** Building Id */
      building_id?: string | null
      /** Campus Id */
      campus_id: string
      /**
       * Description
       * @default
       */
      description: string
      /**
       * Max Devices
       * @default 20
       */
      max_devices: number
      /** Name */
      name: string
      /** Target Reduction Pct */
      target_reduction_pct: number
    }
    /** TariffIn */
    TariffIn: {
      /** Bands */
      bands?: components['schemas']['RateBand'][]
      /**
       * Currency
       * @default CNY
       */
      currency: string
      /** Id */
      id: string
      /** Name */
      name: string
      /** Rate Per Kwh */
      rate_per_kwh: number
      /**
       * Source Mode
       * @enum {string}
       */
      source_mode: 'SIMULATED' | 'REPLAYED' | 'REAL'
      /** Source Url */
      source_url: string
      /**
       * Timezone
       * @default Asia/Shanghai
       */
      timezone: string
      /**
       * Valid From
       * Format: date-time
       */
      valid_from: string
      /**
       * Valid To
       * Format: date-time
       */
      valid_to: string
      /** Version */
      version: number
    }
    /** TariffResponse */
    TariffResponse: {
      /** Bands */
      bands: components['schemas']['RateBand'][]
      /**
       * Created At
       * Format: date-time
       */
      created_at: string
      /** Currency */
      currency: string
      /** Id */
      id: string
      /** Name */
      name: string
      /** Rate Per Kwh */
      rate_per_kwh: number
      /**
       * Source Mode
       * @enum {string}
       */
      source_mode: 'SIMULATED' | 'REPLAYED' | 'REAL'
      /** Source Url */
      source_url: string
      /** Timezone */
      timezone: string
      /**
       * Valid From
       * Format: date-time
       */
      valid_from: string
      /**
       * Valid To
       * Format: date-time
       */
      valid_to: string
      /** Version */
      version: number
    }
    /** TelemetryIn */
    TelemetryIn: {
      /** Active Power W */
      active_power_w?: number | null
      /** Board Temperature C */
      board_temperature_c?: number | null
      /** Boot Epoch */
      boot_epoch: string
      /** Calibrated */
      calibrated: boolean
      /** Correlation Command Id */
      correlation_command_id?: string | null
      /**
       * Counter Scope
       * @default bidirectional
       * @enum {string}
       */
      counter_scope: 'bidirectional' | 'import_only'
      /** Current A */
      current_a?: number | null
      /** Desired On */
      desired_on?: boolean | null
      /** Device Id */
      device_id: string
      /** Energy Export Wh */
      energy_export_wh?: number | null
      /** Energy Import Wh */
      energy_import_wh?: number | null
      /**
       * Energy Status
       * @default unknown
       * @enum {string}
       */
      energy_status: 'known' | 'uncertain' | 'unknown'
      /**
       * Energy Uncertain Intervals
       * @default 0
       */
      energy_uncertain_intervals: number
      /** Fault Latched */
      fault_latched?: boolean | null
      /** Observed At */
      observed_at: string | null
      /** Output Present */
      output_present?: boolean | null
      /** Sample Seq */
      sample_seq: string
      /**
       * Source Mode
       * @enum {string}
       */
      source_mode: 'SIMULATED' | 'REPLAYED' | 'REAL'
      /** Source Version */
      source_version: string
      /**
       * Time Source
       * @enum {string}
       */
      time_source: 'authenticated' | 'simulated' | 'received_only' | 'reconstructed'
      /** Time Uncertainty Ms */
      time_uncertainty_ms?: number | null
      /** Valid */
      valid: boolean
      /** Voltage V */
      voltage_v?: number | null
    }
    /** TelemetryResponse */
    TelemetryResponse: {
      /** Active Power W */
      active_power_w: number | null
      /** Binding Id */
      binding_id: number | null
      /** Board Temperature C */
      board_temperature_c: number | null
      /** Boot Epoch */
      boot_epoch: string
      /** Building Id */
      building_id: string | null
      /** Campus Id */
      campus_id: string
      /** Circuit Id */
      circuit_id: string | null
      /** Correlation Command Id */
      correlation_command_id: string | null
      /** Current A */
      current_a: number | null
      /** Desired On */
      desired_on: boolean | null
      /** Device Id */
      device_id: string
      /** Energy Export Wh */
      energy_export_wh: number | null
      /** Energy Import Wh */
      energy_import_wh: number | null
      /** Fault Latched */
      fault_latched: boolean | null
      /** Id */
      id: number
      /**
       * Observed At
       * Format: date-time
       */
      observed_at: string
      /** Output Present */
      output_present: boolean | null
      /** Quality */
      quality: string
      /** Quality Flags */
      quality_flags: string[]
      /**
       * Received At
       * Format: date-time
       */
      received_at: string
      /**
       * Sample Seq
       * @description Exact unsigned 64-bit counter encoded as a canonical decimal string, never a JSON number
       */
      sample_seq: string
      /**
       * Source Mode
       * @enum {string}
       */
      source_mode: 'SIMULATED' | 'REPLAYED' | 'REAL'
      /** Source Version */
      source_version: string
      /** Space Id */
      space_id: string | null
      /**
       * Time Source
       * @enum {string}
       */
      time_source: 'authenticated' | 'simulated' | 'received_only' | 'reconstructed'
      /** Time Uncertainty Ms */
      time_uncertainty_ms: number | null
      /** Voltage V */
      voltage_v: number | null
    }
    /** TimelineEvent */
    TimelineEvent: {
      /** Actuator Reported On */
      actuator_reported_on?: boolean | null
      /**
       * At
       * Format: date-time
       */
      at: string
      /** Channel Id */
      channel_id: string | null
      /** Command Id */
      command_id: string | null
      /** Description */
      description: string
      /** Device Id */
      device_id: string | null
      /** Id */
      id: string
      /** Output Present */
      output_present: boolean | null
      /** Requested On */
      requested_on: boolean | null
      /**
       * Source Mode
       * @enum {string}
       */
      source_mode: 'SIMULATED' | 'REPLAYED' | 'REAL' | 'UNKNOWN' | 'MIXED'
      /** Status */
      status: string | null
      /** Type */
      type: string
      /** Verification Kind */
      verification_kind?: string | null
    }
    /** TimelineResponse */
    TimelineResponse: {
      durations: components['schemas']['StateDurations']
      /**
       * End
       * Format: date-time
       */
      end: string
      /** Events */
      events?: components['schemas']['TimelineEvent'][]
      /** Intervals */
      intervals: components['schemas']['RoomInterval'][]
      /** Room Id */
      room_id: string
      /** Semantics */
      semantics: string
      /** Source Modes */
      source_modes: string[]
      /**
       * Start
       * Format: date-time
       */
      start: string
    }
    /** UserIn */
    UserIn: {
      /** Campus Ids */
      campus_ids?: string[] | null
      /** Display Name */
      display_name: string
      /** Password */
      password: string
      /**
       * Role
       * @enum {string}
       */
      role: 'admin' | 'operator' | 'analyst' | 'viewer'
      /** Username */
      username: string
    }
    /** UserPatch */
    UserPatch: {
      /** Campus Ids */
      campus_ids?: string[] | null
      /** Display Name */
      display_name?: string | null
      /** Enabled */
      enabled?: boolean | null
      /** Role */
      role?: ('admin' | 'operator' | 'analyst' | 'viewer') | null
    }
    /** UserResponse */
    UserResponse: {
      /** Campus Ids */
      campus_ids: string[] | null
      /** Display Name */
      display_name: string
      /** Id */
      id: string
      /**
       * Role
       * @enum {string}
       */
      role: 'admin' | 'operator' | 'analyst' | 'viewer'
      /** Username */
      username: string
    }
  }
  responses: never
  parameters: never
  requestBodies: never
  headers: never
  pathItems: never
}
export type $defs = Record<string, never>
export interface operations {
  adapter_commands_api_v1_adapter_commands_get: {
    parameters: {
      query?: {
        limit?: number
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  adapter_delivery_api_v1_adapter_commands__command_id__delivery_post: {
    parameters: {
      query?: never
      header?: never
      path: {
        command_id: string
      }
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['DeliveryIn']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  alarms_api_v1_alarms_get: {
    parameters: {
      query?: {
        campus_id?: string | null
        building_id?: string | null
        status?: ('open' | 'acknowledged' | 'resolved') | null
        severity?: ('info' | 'warning' | 'critical') | null
        limit?: number
        offset?: number
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  alarm_detail_api_v1_alarms__alarm_id__get: {
    parameters: {
      query?: never
      header?: never
      path: {
        alarm_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  alarm_ack_api_v1_alarms__alarm_id__acknowledge_post: {
    parameters: {
      query?: never
      header: {
        /** @description CSRF token from the authenticated session */
        'X-CSRF-Token': string
      }
      path: {
        alarm_id: string
      }
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['NoteIn']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  alarm_note_api_v1_alarms__alarm_id__notes_post: {
    parameters: {
      query?: never
      header: {
        /** @description CSRF token from the authenticated session */
        'X-CSRF-Token': string
      }
      path: {
        alarm_id: string
      }
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['RequiredNote']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  alarm_resolve_api_v1_alarms__alarm_id__resolve_post: {
    parameters: {
      query?: never
      header: {
        /** @description CSRF token from the authenticated session */
        'X-CSRF-Token': string
      }
      path: {
        alarm_id: string
      }
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['RequiredNote']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  assets_manifest_api_v1_assets_manifest_get: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  product_hero_api_v1_assets_product_hero_get: {
    parameters: {
      query: {
        family: 'PLUG' | 'SWITCH' | 'PRESENCE'
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  product_manifest_api_v1_assets_product_manifest_get: {
    parameters: {
      query: {
        family: 'PLUG' | 'SWITCH' | 'PRESENCE'
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  product_model_api_v1_assets_product_model_get: {
    parameters: {
      query: {
        family: 'PLUG' | 'SWITCH' | 'PRESENCE'
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  audit_log_api_v1_audit_get: {
    parameters: {
      query?: {
        entity_type?: string | null
        entity_id?: string | null
        campus_id?: string | null
        limit?: number
        offset?: number
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  auth_login_api_v1_auth_login_post: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['LoginIn']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_AuthResponse_']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  auth_logout_api_v1_auth_logout_post: {
    parameters: {
      query?: never
      header: {
        /** @description CSRF token from the authenticated session */
        'X-CSRF-Token': string
      }
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_LogoutResponse_']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  auth_me_api_v1_auth_me_get: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_AuthResponse_']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  buildings_api_v1_buildings_get: {
    parameters: {
      query?: {
        campus_id?: string | null
        q?: string | null
        limit?: number
        offset?: number
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  building_detail_api_v1_buildings__building_id__get: {
    parameters: {
      query?: never
      header?: never
      path: {
        building_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  campuses_api_v1_campuses_get: {
    parameters: {
      query?: {
        limit?: number
        offset?: number
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  factors_api_v1_carbon_factors_get: {
    parameters: {
      query?: {
        limit?: number
        offset?: number
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_list_FactorResponse__']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  factor_create_api_v1_carbon_factors_post: {
    parameters: {
      query?: never
      header: {
        /** @description CSRF token from the authenticated session */
        'X-CSRF-Token': string
      }
      path?: never
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['FactorIn']
      }
    }
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_FactorResponse_']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  carbon_summary_api_v1_carbon_summary_get: {
    parameters: {
      query?: {
        campus_id?: string | null
        building_id?: string | null
        start?: string | null
        end?: string | null
        device_ids?: string | null
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_CarbonSummaryResponse_']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  new_channel_api_v1_channels_post: {
    parameters: {
      query?: never
      header: {
        /** @description CSRF token from the authenticated session */
        'X-CSRF-Token': string
      }
      path?: never
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['ChannelIn']
      }
    }
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_ChannelDefinition_']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  circuit_create_api_v1_circuits_post: {
    parameters: {
      query?: never
      header: {
        /** @description CSRF token from the authenticated session */
        'X-CSRF-Token': string
      }
      path?: never
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['CircuitIn']
      }
    }
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  circuit_update_api_v1_circuits__circuit_id__patch: {
    parameters: {
      query?: never
      header: {
        /** @description CSRF token from the authenticated session */
        'X-CSRF-Token': string
      }
      path: {
        circuit_id: string
      }
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['CircuitPatch']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  rooms_api_v1_classrooms_get: {
    parameters: {
      query?: {
        campus_id?: string | null
        building_id?: string | null
        floor_id?: string | null
        at?: string | null
        limit?: number
        offset?: number
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_list_RoomSnapshot__']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  anomalies_api_v1_classrooms_anomalies_get: {
    parameters: {
      query?: {
        campus_id?: string | null
        building_id?: string | null
        space_id?: string | null
        status?: ('open' | 'acknowledged' | 'resolved') | null
        limit?: number
        offset?: number
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_list_AnomalyResponse__']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  evaluate_anomalies_api_v1_classrooms_anomalies_evaluate_post: {
    parameters: {
      query?: never
      header: {
        /** @description CSRF token from the authenticated session */
        'X-CSRF-Token': string
      }
      path?: never
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['EvaluateAnomaliesIn']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_list_AnomalyResponse__']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  acknowledge_api_v1_classrooms_anomalies__anomaly_id__acknowledge_post: {
    parameters: {
      query?: never
      header: {
        /** @description CSRF token from the authenticated session */
        'X-CSRF-Token': string
      }
      path: {
        anomaly_id: string
      }
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['RequiredNote']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_AnomalyResponse_']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  resolve_api_v1_classrooms_anomalies__anomaly_id__resolve_post: {
    parameters: {
      query?: never
      header: {
        /** @description CSRF token from the authenticated session */
        'X-CSRF-Token': string
      }
      path: {
        anomaly_id: string
      }
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['RequiredNote']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_AnomalyResponse_']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  change_anomaly_rules_api_v1_classrooms_anomaly_rules_batch_patch: {
    parameters: {
      query?: never
      header: {
        /** @description CSRF token from the authenticated session */
        'X-CSRF-Token': string
      }
      path?: never
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['AnomalyRuleBatchPatch']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_list_AnomalyRuleResponse__']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  distribution_api_v1_classrooms_distribution_get: {
    parameters: {
      query?: {
        campus_id?: string | null
        building_id?: string | null
        floor_id?: string | null
        at?: string | null
        start?: string | null
        end?: string | null
        group_by?: 'campus' | 'building' | 'floor'
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_DistributionResponse_']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  evaluation_api_v1_classrooms_evaluations__evaluation_id__get: {
    parameters: {
      query?: never
      header?: never
      path: {
        evaluation_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_EvaluationResponse_']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  dispatch_api_v1_classrooms_evaluations__evaluation_id__dispatch_post: {
    parameters: {
      query?: never
      header: {
        /** @description CSRF token from the authenticated session */
        'X-CSRF-Token': string
      }
      path: {
        evaluation_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_EvaluationResponse_']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  change_policy_api_v1_classrooms_policies__policy_id__patch: {
    parameters: {
      query?: never
      header: {
        /** @description CSRF token from the authenticated session */
        'X-CSRF-Token': string
      }
      path: {
        policy_id: string
      }
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['PolicyPatch']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_PolicyResponse_']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  evaluate_policy_api_v1_classrooms_policies__policy_id__evaluate_post: {
    parameters: {
      query?: never
      header: {
        /** @description CSRF token from the authenticated session */
        'X-CSRF-Token': string
      }
      path: {
        policy_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_EvaluationResponse_']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  room_api_v1_classrooms__room_id__get: {
    parameters: {
      query?: {
        at?: string | null
      }
      header?: never
      path: {
        room_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_RoomSnapshot_']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  anomaly_rule_api_v1_classrooms__room_id__anomaly_rule_get: {
    parameters: {
      query?: never
      header?: never
      path: {
        room_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_AnomalyRuleResponse_']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  change_anomaly_rule_api_v1_classrooms__room_id__anomaly_rule_patch: {
    parameters: {
      query?: never
      header: {
        /** @description CSRF token from the authenticated session */
        'X-CSRF-Token': string
      }
      path: {
        room_id: string
      }
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['AnomalyRulePatch']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_AnomalyRuleResponse_']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  room_channels_api_v1_classrooms__room_id__channels_get: {
    parameters: {
      query?: {
        at?: string | null
      }
      header?: never
      path: {
        room_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_list_ChannelSnapshot__']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  room_evaluations_api_v1_classrooms__room_id__evaluations_get: {
    parameters: {
      query?: {
        limit?: number
        offset?: number
      }
      header?: never
      path: {
        room_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_list_EvaluationResponse__']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  modes_api_v1_classrooms__room_id__mode_get: {
    parameters: {
      query?: never
      header?: never
      path: {
        room_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_list_ModeResponse__']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  change_mode_api_v1_classrooms__room_id__mode_patch: {
    parameters: {
      query?: never
      header: {
        /** @description CSRF token from the authenticated session */
        'X-CSRF-Token': string
      }
      path: {
        room_id: string
      }
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['ModeIn']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_ModeResponse_']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  policies_api_v1_classrooms__room_id__policies_get: {
    parameters: {
      query?: never
      header?: never
      path: {
        room_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_list_PolicyResponse__']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  new_policy_api_v1_classrooms__room_id__policies_post: {
    parameters: {
      query?: never
      header: {
        /** @description CSRF token from the authenticated session */
        'X-CSRF-Token': string
      }
      path: {
        room_id: string
      }
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['PolicyIn']
      }
    }
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_PolicyResponse_']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  room_timeline_api_v1_classrooms__room_id__timeline_get: {
    parameters: {
      query: {
        start: string
        end: string
      }
      header?: never
      path: {
        room_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_TimelineResponse_']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  commands_api_v1_commands_get: {
    parameters: {
      query?: {
        device_id?: string | null
        status?: string | null
        campus_id?: string | null
        building_id?: string | null
        limit?: number
        offset?: number
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_list_CommandResponse__']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  command_create_api_v1_commands_post: {
    parameters: {
      query?: never
      header: {
        'idempotency-key'?: string | null
        /** @description CSRF token from the authenticated session */
        'X-CSRF-Token': string
      }
      path?: never
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['CommandIn']
      }
    }
    responses: {
      /** @description Existing idempotent command */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_CommandResponse_']
        }
      }
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_CommandResponse_']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  command_detail_api_v1_commands__command_id__get: {
    parameters: {
      query?: never
      header?: never
      path: {
        command_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_CommandResponse_']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  cost_summary_api_v1_cost_summary_get: {
    parameters: {
      query?: {
        campus_id?: string | null
        building_id?: string | null
        start?: string | null
        end?: string | null
        device_ids?: string | null
        allocation_mode?: 'strict' | 'proportional_estimate'
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_CostSummaryResponse_']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  devices_api_v1_devices_get: {
    parameters: {
      query?: {
        campus_id?: string | null
        building_id?: string | null
        space_id?: string | null
        q?: string | null
        status?: ('online' | 'stale' | 'offline' | 'unknown') | null
        source_mode?: ('SIMULATED' | 'REAL' | 'REPLAYED') | null
        limit?: number
        offset?: number
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_list_DeviceResponse__']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  device_create_api_v1_devices_post: {
    parameters: {
      query?: never
      header: {
        /** @description CSRF token from the authenticated session */
        'X-CSRF-Token': string
      }
      path?: never
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['DeviceIn']
      }
    }
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_DeviceResponse_']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  device_detail_api_v1_devices__device_id__get: {
    parameters: {
      query?: never
      header?: never
      path: {
        device_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_DeviceDetailResponse_']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  device_update_api_v1_devices__device_id__patch: {
    parameters: {
      query?: never
      header: {
        /** @description CSRF token from the authenticated session */
        'X-CSRF-Token': string
      }
      path: {
        device_id: string
      }
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['DevicePatch']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_DeviceResponse_']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  device_binding_api_v1_devices__device_id__binding_put: {
    parameters: {
      query?: never
      header: {
        /** @description CSRF token from the authenticated session */
        'X-CSRF-Token': string
      }
      path: {
        device_id: string
      }
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['BindingIn']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_DeviceResponse_']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  commissioning_list_api_v1_devices__device_id__commissioning_get: {
    parameters: {
      query?: never
      header?: never
      path: {
        device_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  commissioning_create_api_v1_devices__device_id__commissioning_post: {
    parameters: {
      query?: never
      header: {
        /** @description CSRF token from the authenticated session */
        'X-CSRF-Token': string
      }
      path: {
        device_id: string
      }
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['CommissioningIn']
      }
    }
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  commissioning_release_api_v1_devices__device_id__commissioning_release_post: {
    parameters: {
      query?: never
      header: {
        /** @description CSRF token from the authenticated session */
        'X-CSRF-Token': string
      }
      path: {
        device_id: string
      }
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['ReleaseIn']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  commissioning_revoke_api_v1_devices__device_id__commissioning__release_id__revoke_post: {
    parameters: {
      query?: never
      header: {
        /** @description CSRF token from the authenticated session */
        'X-CSRF-Token': string
      }
      path: {
        device_id: string
        release_id: string
      }
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['RequiredNote']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  control_eligibility_api_v1_devices__device_id__control_eligibility_get: {
    parameters: {
      query?: {
        channel_id?: string | null
      }
      header?: never
      path: {
        device_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_ControlEligibilityResponse_']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  device_telemetry_api_v1_devices__device_id__telemetry_get: {
    parameters: {
      query?: {
        start?: string | null
        end?: string | null
        limit?: number
        offset?: number
      }
      header?: never
      path: {
        device_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_list_TelemetryResponse__']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  energy_balance_api_v1_energy_balance_get: {
    parameters: {
      query?: {
        campus_id?: string | null
        building_id?: string | null
        start?: string | null
        end?: string | null
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_EnergyBalanceResponse_']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  energy_breakdown_api_v1_energy_breakdown_get: {
    parameters: {
      query?: {
        group_by?: 'building' | 'device' | 'circuit'
        campus_id?: string | null
        building_id?: string | null
        start?: string | null
        end?: string | null
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_list_EnergyBreakdownResponse__']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  energy_summary_api_v1_energy_summary_get: {
    parameters: {
      query?: {
        campus_id?: string | null
        building_id?: string | null
        start?: string | null
        end?: string | null
        device_ids?: string | null
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_EnergySummaryResponse_']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  events_api_v1_events_get: {
    parameters: {
      query?: {
        after_id?: number
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  floors_api_v1_floors_get: {
    parameters: {
      query?: {
        building_id?: string | null
        limit?: number
        offset?: number
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  forecasts_api_v1_forecasts_get: {
    parameters: {
      query?: {
        campus_id?: string | null
        building_id?: string | null
        horizon_hours?: number
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_ForecastResponse_']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  forecast_refresh_api_v1_forecasts_refresh_post: {
    parameters: {
      query?: never
      header: {
        /** @description CSRF token from the authenticated session */
        'X-CSRF-Token': string
      }
      path?: never
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['ForecastRefreshIn']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_ForecastResponse_']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  adapter_ack_api_v1_ingest_ack_post: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': {
          [key: string]: unknown
        }
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  channel_ack_api_v1_ingest_channel_acks_post: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': {
          boot_id: string
          channel: number
          device_id: string
          id: string
          /** @constant */
          physical_verification: false
          /** @enum {unknown} */
          result:
            | 'commanded'
            | 'duplicate'
            | 'invalid_command'
            | 'wrong_boot'
            | 'expired'
            | 'stale_sequence'
            | 'id_conflict'
            | 'manual_hold'
            | 'maintenance'
            | 'protected'
            | 'not_commissioned'
            | 'fault_latched'
          seq: string
          uptime_ms: string
        }
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_IoTAckReceipt_']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  channel_samples_api_v1_ingest_channels_post: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['ChannelBatch']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_ChannelBatchReceipt_']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  canonical_event_api_v1_ingest_events_post: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': {
          boot_id: string
          device_id: string
          event_id: string
          monotonic_ms: number | null
          observed_at: string | null
          /** @enum {unknown} */
          product_family: 'PLUG' | 'SWITCH' | 'PRESENCE'
          /** @enum {unknown} */
          quality:
            | 'valid'
            | 'partial'
            | 'invalid'
            | 'stale'
            | 'unknown'
            | 'unavailable'
            | 'uncalibrated'
          raw: Record<string, never>
          readings: ({
            /** @enum {unknown} */
            capability:
              | 'power.active'
              | 'voltage.rms'
              | 'current.rms'
              | 'energy.import'
              | 'energy.export'
              | 'relay.commanded'
              | 'relay.feedback'
              | 'presence.pir'
              | 'presence.radar'
              | 'illuminance.raw'
              | 'button.local'
              | 'buffer.voltage'
              | 'device.health'
              | 'control.mode'
              | 'control.manual_hold_until'
            channel_id: string
            details?: Record<string, never>
            /** @enum {unknown} */
            quality:
              | 'valid'
              | 'partial'
              | 'invalid'
              | 'stale'
              | 'unknown'
              | 'unavailable'
              | 'uncalibrated'
            /** @enum {unknown} */
            unit:
              | 'W'
              | 'V'
              | 'A'
              | 'Wh'
              | 'boolean'
              | 'raw_count'
              | 'mV'
              | 'status'
              | 'mode'
              | 'monotonic_ms'
            value: number | boolean | string | null
          } & (unknown &
            unknown &
            unknown &
            unknown &
            unknown &
            unknown &
            unknown &
            unknown &
            unknown &
            unknown &
            unknown &
            unknown &
            unknown &
            unknown &
            unknown))[]
          /** Format: date-time */
          received_at: string
          /** @constant */
          schema_version: 1
          sequence: string
          /** @enum {unknown} */
          source_mode: 'REAL' | 'SIMULATED' | 'REPLAYED'
          /** @enum {unknown} */
          source_protocol:
            | 'plug-wire-v2'
            | 'switch-mqtt-v1'
            | 'presence-ble-v2'
            | 'virtual-v1'
            | 'presence-gatt-v1'
          /** @enum {unknown} */
          time_quality: 'authenticated' | 'device_clock' | 'gateway_received' | 'unknown'
        }
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_IoTEventReceipt_']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  ingest_firmware_api_v1_ingest_firmware_post: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': {
          [key: string]: unknown
        }
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  ingest_api_v1_ingest_telemetry_post: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['IngestIn']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  overview_route_api_v1_overview_get: {
    parameters: {
      query?: {
        campus_id?: string | null
        building_id?: string | null
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  reports_api_v1_reports_get: {
    parameters: {
      query?: {
        campus_id?: string | null
        building_id?: string | null
        limit?: number
        offset?: number
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  report_create_api_v1_reports_post: {
    parameters: {
      query?: never
      header: {
        /** @description CSRF token from the authenticated session */
        'X-CSRF-Token': string
      }
      path?: never
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['ReportIn']
      }
    }
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  report_detail_api_v1_reports__report_id__get: {
    parameters: {
      query?: never
      header?: never
      path: {
        report_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  report_export_api_v1_reports__report_id__export_get: {
    parameters: {
      query?: {
        format?: 'json' | 'csv'
      }
      header?: never
      path: {
        report_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  schedules_api_v1_schedules_get: {
    parameters: {
      query?: {
        campus_id?: string | null
        building_id?: string | null
        space_id?: string | null
        start?: string | null
        end?: string | null
        limit?: number
        offset?: number
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  schedule_create_api_v1_schedules_post: {
    parameters: {
      query?: never
      header: {
        /** @description CSRF token from the authenticated session */
        'X-CSRF-Token': string
      }
      path?: never
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['ScheduleIn']
      }
    }
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  schedule_import_api_v1_schedules_import_post: {
    parameters: {
      query?: never
      header: {
        /** @description CSRF token from the authenticated session */
        'X-CSRF-Token': string
      }
      path?: never
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['ScheduleImport']
      }
    }
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  schedule_update_api_v1_schedules__schedule_id__put: {
    parameters: {
      query?: never
      header: {
        /** @description CSRF token from the authenticated session */
        'X-CSRF-Token': string
      }
      path: {
        schedule_id: string
      }
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['ScheduleIn']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  schedule_cancel_api_v1_schedules__schedule_id__cancel_post: {
    parameters: {
      query?: never
      header: {
        /** @description CSRF token from the authenticated session */
        'X-CSRF-Token': string
      }
      path: {
        schedule_id: string
      }
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['RequiredNote']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  settings_read_api_v1_settings_get: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  settings_update_api_v1_settings_patch: {
    parameters: {
      query?: never
      header: {
        /** @description CSRF token from the authenticated session */
        'X-CSRF-Token': string
      }
      path?: never
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['SettingsPatch']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  spaces_api_v1_spaces_get: {
    parameters: {
      query?: {
        campus_id?: string | null
        building_id?: string | null
        floor_id?: string | null
        q?: string | null
        limit?: number
        offset?: number
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  strategies_api_v1_strategies_get: {
    parameters: {
      query?: {
        campus_id?: string | null
        building_id?: string | null
        limit?: number
        offset?: number
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  strategy_create_api_v1_strategies_post: {
    parameters: {
      query?: never
      header: {
        /** @description CSRF token from the authenticated session */
        'X-CSRF-Token': string
      }
      path?: never
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['StrategyIn']
      }
    }
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  strategy_approve_api_v1_strategies__strategy_id__approve_post: {
    parameters: {
      query?: never
      header: {
        /** @description CSRF token from the authenticated session */
        'X-CSRF-Token': string
      }
      path: {
        strategy_id: string
      }
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['RequiredNote']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  strategy_dispatch_api_v1_strategies__strategy_id__dispatch_post: {
    parameters: {
      query?: never
      header: {
        'idempotency-key'?: string | null
        /** @description CSRF token from the authenticated session */
        'X-CSRF-Token': string
      }
      path: {
        strategy_id: string
      }
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['DispatchIn']
      }
    }
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  strategy_evaluate_api_v1_strategies__strategy_id__evaluate_post: {
    parameters: {
      query?: never
      header: {
        /** @description CSRF token from the authenticated session */
        'X-CSRF-Token': string
      }
      path: {
        strategy_id: string
      }
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  system_status_api_v1_system_status_get: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  tariffs_api_v1_tariffs_get: {
    parameters: {
      query?: {
        limit?: number
        offset?: number
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_list_TariffResponse__']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  tariff_create_api_v1_tariffs_post: {
    parameters: {
      query?: never
      header: {
        /** @description CSRF token from the authenticated session */
        'X-CSRF-Token': string
      }
      path?: never
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['TariffIn']
      }
    }
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_TariffResponse_']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  telemetry_api_v1_telemetry_get: {
    parameters: {
      query?: {
        device_id?: string | null
        campus_id?: string | null
        building_id?: string | null
        circuit_id?: string | null
        start?: string | null
        end?: string | null
        limit?: number
        offset?: number
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['Envelope_list_TelemetryResponse__']
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  topology_api_v1_topology_get: {
    parameters: {
      query?: {
        campus_id?: string | null
        building_id?: string | null
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  users_list_api_v1_users_get: {
    parameters: {
      query?: {
        limit?: number
        offset?: number
      }
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  user_create_api_v1_users_post: {
    parameters: {
      query?: never
      header: {
        /** @description CSRF token from the authenticated session */
        'X-CSRF-Token': string
      }
      path?: never
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['UserIn']
      }
    }
    responses: {
      /** @description Successful Response */
      201: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  user_update_api_v1_users__user_id__patch: {
    parameters: {
      query?: never
      header: {
        /** @description CSRF token from the authenticated session */
        'X-CSRF-Token': string
      }
      path: {
        user_id: string
      }
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['UserPatch']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  user_password_api_v1_users__user_id__password_post: {
    parameters: {
      query?: never
      header: {
        /** @description CSRF token from the authenticated session */
        'X-CSRF-Token': string
      }
      path: {
        user_id: string
      }
      cookie?: never
    }
    requestBody: {
      content: {
        'application/json': components['schemas']['PasswordIn']
      }
    }
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
      /** @description Bad Request */
      400: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unauthorized */
      401: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Forbidden */
      403: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Not Found */
      404: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Conflict */
      409: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Request Entity Too Large */
      413: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Too Many Requests */
      429: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Internal Server Error */
      500: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': components['schemas']['ErrorEnvelope']
        }
      }
    }
  }
  live_health_live_get: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
    }
  }
  ready_health_ready_get: {
    parameters: {
      query?: never
      header?: never
      path?: never
      cookie?: never
    }
    requestBody?: never
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown
        }
        content: {
          'application/json': unknown
        }
      }
    }
  }
}
