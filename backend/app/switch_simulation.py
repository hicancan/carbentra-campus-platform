"""Three-channel software Switch. Device reports are never independent load feedback."""
from datetime import datetime
from sqlalchemy import select
from .models import DeviceChannel, ChannelObservation, SimulatedChannelOutput
from .db import utcnow
from .classroom_schemas import ChannelSample, ChannelValue
from .classrooms import ingest_channel
from .seed import stable_number


def channel_state(db, device, channel):
    state = db.get(SimulatedChannelOutput, channel.id)
    if state is None:
        prior=db.scalar(select(ChannelObservation).where(ChannelObservation.channel_id==channel.id).order_by(ChannelObservation.observed_at.desc()).limit(1))
        state=SimulatedChannelOutput(channel_id=channel.id,device_id=device.id,campus_id=device.campus_id,
            actuator_reported_on=bool(prior.value.get('actuator_reported_on')) if prior else False)
        db.add(state);db.flush()
    return state


def aggregate_power(db, device, at, channels=None):
    channels=channels or list(db.scalars(select(DeviceChannel).where(DeviceChannel.device_id==device.id)))
    states={c.channel_key:channel_state(db,device,c) for c in channels if c.kind=='lighting'}
    base=(180.+stable_number(device.space_id or device.id)%260)*.65
    if device.provenance.get("scenario")=="high_load":
        base*=7
    return round(sum(s.actuator_reported_on for s in states.values())*base/3,3),states


def emit_switch(db, device, at):
    channels=list(db.scalars(select(DeviceChannel).where(DeviceChannel.device_id==device.id)))
    total,states=aggregate_power(db,device,at,channels)
    count=0
    for channel in channels:
        previous=db.scalar(select(ChannelObservation).where(ChannelObservation.channel_id==channel.id).order_by(ChannelObservation.observed_at.desc(),ChannelObservation.id.desc()).limit(1))
        if not previous or at<previous.observed_at:continue
        value=ChannelValue(active_power_w=round(total,3)) if channel.kind=='power' else ChannelValue(
            desired_on=states[channel.channel_key].actuator_reported_on,actuator_reported_on=states[channel.channel_key].actuator_reported_on,
            output_present=None,fault_latched=device.provenance.get('scenario')=='local_fault')
        row,_=ingest_channel(db,ChannelSample(channel_id=channel.id,boot_epoch=previous.boot_epoch,sample_seq=str(int(previous.sample_seq)+1),observed_at=at,
            time_source='simulated',time_uncertainty_ms=0.,source_mode='SIMULATED',source_version='classroom-switch-software-v2',valid=not (device.provenance.get("scenario")=="feedback_unknown" and channel.kind=="lighting"),value=value),received_at=at)
        count+=1
    if count:
        from .schemas import TelemetryIn
        from .telemetry import ingest_sample
        from .models import Telemetry
        meter=next((c for c in channels if c.kind=="power"),None)
        reading=db.scalar(select(ChannelObservation).where(ChannelObservation.channel_id==meter.id).order_by(ChannelObservation.observed_at.desc(),ChannelObservation.id.desc()).limit(1)) if meter else None
        if reading:
            prior=db.get(Telemetry,device.latest_telemetry_id) if device.latest_telemetry_id else None
            elapsed=max(0.,(at-prior.observed_at).total_seconds()) if prior else 0.
            uncertain=(prior.raw_payload.get("energy_uncertain_intervals",0) if prior else 0)+int(elapsed>1800)
            energy=(prior.energy_import_wh or 0.) if prior else 0.
            if elapsed<=1800:energy+=total*elapsed/3600
            ingest_sample(db,TelemetryIn(device_id=device.id,boot_epoch=reading.boot_epoch,sample_seq=reading.sample_seq,
                observed_at=at,time_source="simulated",time_uncertainty_ms=0.,active_power_w=total,voltage_v=230.,current_a=total/230,
                energy_import_wh=energy,energy_export_wh=None,valid=True,calibrated=True,energy_status="uncertain",counter_scope="import_only",
                energy_uncertain_intervals=uncertain,source_mode="SIMULATED",source_version="classroom-switch-aggregate-v2"),received_at=at)
    return count


def dispatch_switch(db, command, device, now):
    # Intent is persisted in Command; actuator state changes only in observe_switch.
    channel_state(db,device,db.get(DeviceChannel,command.channel_id))


def observe_switch(db, command, device, now):
    from .iot_ingestion import ingest_switch_ack
    if command.simulation_scenario=='timeout':return
    channel=db.get(DeviceChannel,command.channel_id)
    state=channel_state(db,device,channel)
    if command.simulation_scenario!='fail':
        state.actuator_reported_on=command.history[0]['evidence']['desired_on']
        state.last_command_id=command.id;state.updated_at=now
        db.flush();emit_switch(db,device,now)
    ingest_switch_ack(db,{'device_id':device.id,'boot_id':command.expected_boot_epoch,'id':command.id,'seq':str(command.sequence),
        'channel':int(command.channel_key.split('.')[-1]),'result':'fault_latched' if command.simulation_scenario=='fail' else 'commanded',
        'physical_verification':False,'uptime_ms':str(int(now.timestamp()*1000))},now)
