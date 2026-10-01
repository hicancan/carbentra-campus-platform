"""Three-family multiroom MQTT simulator. All records are explicitly SIMULATED.

This is a software endpoint, not a physical driver or a measured energy claim.
It drives the same gateway topics and canonical outbox as supported devices.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict, replace
import json
from pathlib import Path
import ssl
import struct
import threading
import time
import uuid
from adapters import Enrollment, PresenceAdapter, iso
from contract import canonical, event_identity, validate_event
from service import strict_json

EXAMPLES=Path(__file__).resolve().parents[1]/'packages/iot-contract/examples'


class VirtualRoom:
    def __init__(self, room):
        if not room or not all(c.isalnum() or c in '_-' for c in room):
            raise ValueError('simple room identity required')
        self.room=room
        self.plug=Enrollment('virtual-plug-'+room,'PLUG','plug-wire-v2','SIMULATED',profile_id='lab-load')
        self.switch=Enrollment('virtual-switch-'+room,'SWITCH','switch-mqtt-v1','SIMULATED')
        # Address/identity have simulation scope only, never transmitted on a radio.
        index=int.from_bytes(room.encode()[:4].ljust(4,b'0'),'little') or 1
        self.sense=Enrollment('virtual-sense-'+room,'PRESENCE','presence-ble-v2','SIMULATED','AA:BB:CC:DD:EE:01',index)
        self.boot=uuid.uuid4().hex;self.started=time.monotonic();self.seq=0
        self.plug_on=True;self.channels=[False,False,False];self.last_command=0
        self.manual_hold_until=0;self.local_event=0;self.lock=threading.RLock()

    @property
    def enrollments(self):return [self.plug,self.switch,self.sense]

    def messages(self,now=None,present=True):
        now=time.time() if now is None else now
        with self.lock:
            self.seq+=1;seq=self.seq;uptime=max(1000,int((time.monotonic()-self.started)*1000))
            raw=json.loads((EXAMPLES/'plug-event.json').read_text(encoding="utf-8"))['raw']
            raw.update(device_id=self.plug.device_id,boot_epoch=self.boot,sample_seq=str(seq),monotonic_ms=uptime,
                measurement_monotonic_ms=uptime,desired_on=self.plug_on,feedback_valid=True,output_present=self.plug_on,
                output_sensing='AC_PRESENT' if self.plug_on else 'NO_AC_PULSES_DETECTED',calibrated=True,valid=True,
                voltage_v=230.0,current_a=0.5 if self.plug_on else 0.0,active_w=100.0 if self.plug_on else 0.0,
                reactive_var=0.0,apparent_va=115.0 if self.plug_on else 0.0,pf=.87,frequency_hz=50.0,
                energy_status='calibrated_counts_known_intervals_since_boot_not_billing_certified',known_forward_wh_since_boot=seq*.01,
                unix_s=int(now),unix_lower_s=int(now),unix_upper_s=int(now),time_quality='authenticated')
            switch=json.loads((EXAMPLES/'switch-event.json').read_text(encoding="utf-8"))['raw']
            switch.update(device_id=self.switch.device_id,boot_id=self.boot,sample_seq=str(seq),uptime_ms=str(uptime),last_seq=str(self.last_command),actuation_enabled=True)
            switch['aggregate_meter'].update(observed_uptime_ms=str(uptime),active_power_w=sum(self.channels)*20.0,
                current_a=sum(self.channels)*.1,known_energy_wh=f'{seq*.002:.3f}')
            for i,ch in enumerate(switch['channels']):
                ch.update(commanded_on=self.channels[i],control_mode='manual' if i==0 and uptime<self.manual_hold_until else 'auto',manual_hold_until_uptime_ms=str(self.manual_hold_until if i==0 else 0))
            if self.local_event:
                switch['last_local_input']={'channel':1,'event_seq':str(self.local_event),'uptime_ms':str(max(0,self.manual_hold_until-900000)),'pressed':True,'result':'commanded'}
            frame=struct.pack('<BBBBIIIHHI',2,208,2 if present else 1,0,self.sense.ble_identity,int(self.boot[:8],16) or 1,seq,1200,3300,uptime//1000)
            sensor=PresenceAdapter.telemetry(self.sense,frame,now)
            sensor['source_protocol']='virtual-v1'
            for r in sensor['readings']:
                r.setdefault('details',{})['authenticity']='simulation'
                if r['capability']=='presence.radar':
                    r['quality']='valid';r['details'].update(continuous_occupancy=True,sample_only=False,measurement_age_ms=0)
            sensor['raw']['simulation_scenario']='continuous_virtual_presence'
            validate_event(sensor)
            return [(f'carbentra/v1/{self.plug.device_id}/telemetry',raw),
                (f'carbentra/switch/{self.switch.device_id}/state',switch),
                (f'carbentra/virtual/{self.sense.device_id}/event',sensor)]

    def press_local(self):
        with self.lock:
            uptime=max(1000,int((time.monotonic()-self.started)*1000))
            self.channels[0]=not self.channels[0];self.manual_hold_until=uptime+900000;self.local_event+=1

    def command(self,topic,raw,now=None):
        now=time.time() if now is None else now
        with self.lock:
            uptime=max(1000,int((time.monotonic()-self.started)*1000))
            if topic==f'carbentra/switch/{self.switch.device_id}/command':
                required={'id','boot_id','seq','channel','on','expires_uptime_ms'}
                if set(raw)!=required or type(raw['channel']) is not int or raw['channel'] not in (1,2,3) or type(raw['on']) is not bool:
                    raise ValueError('invalid simulated Switch command')
                index=raw['channel']-1
                result='commanded'
                if raw['boot_id']!=self.boot:result='wrong_boot'
                elif int(raw['expires_uptime_ms'])<=uptime:result='expired'
                elif int(raw['seq'])<=self.last_command:result='stale_sequence'
                elif index==0 and uptime<self.manual_hold_until:result='manual_hold'
                else:self.channels[index]=raw['on'];self.last_command=int(raw['seq'])
                return f'carbentra/switch/{self.switch.device_id}/ack',{'device_id':self.switch.device_id,'boot_id':self.boot,'id':raw['id'],'seq':raw['seq'],'channel':raw['channel'],'result':result,'physical_verification':False,'uptime_ms':str(uptime)}
            if topic==f'carbentra/v1/{self.plug.device_id}/cmd':
                from command_transport import wire_command
                wire_command(raw,self.plug.device_id)
                if not raw['issued_s']<=now<raw['expires_s']:return None
                self.plug_on=raw['action']=='restore' if raw['action']!='hold' else self.plug_on
                return f'carbentra/v1/{self.plug.device_id}/ack',{'schema_version':2,'device_id':self.plug.device_id,'boot_epoch':self.boot,
                    'id':raw['id'],'seq':raw['seq'],'status':'OBSERVED_VERIFIED','terminal':True,'desired_on':self.plug_on,
                    'fault_latched':False,'voltage_absence_proven':False,'requested_monotonic_ms':uptime,'deadline_monotonic_ms':uptime+5000,
                    'observed_monotonic_ms':uptime+100,'feedback_valid':True,'output_present':self.plug_on,
                    'output_sensing':'AC_PRESENT' if self.plug_on else 'NO_AC_PULSES_DETECTED'}
            return None


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rooms',default='a101,a102');p.add_argument('--write-enrollment')
    p.add_argument('--broker');p.add_argument('--port',type=int,default=8883)
    for name in ('ca','certificate','key'):p.add_argument('--'+name)
    p.add_argument('--interval',type=float,default=2);p.add_argument('--ticks',type=int,default=0);p.add_argument('--scenario',choices=['normal','manual-hold','sensor-outage'],default='normal')
    args=p.parse_args();rooms=[VirtualRoom(room) for room in args.rooms.split(',')]
    if args.write_enrollment:
        # Distinct stable diagnostic addresses per virtual room, not any physical identity.
        records=[]
        for i,room in enumerate(rooms):
            for e in room.enrollments:
                item={k:v for k,v in asdict(e).items() if v is not None}
                if e.product_family=='PRESENCE':item['ble_address']=f'AA:BB:CC:DD:EE:{i+1:02X}'
                records.append(item)
        Path(args.write_enrollment).write_text(json.dumps({'enrollments':records},indent=2)+'\n', encoding="utf-8");return
    if not all([args.broker,args.ca,args.certificate,args.key]) or args.interval<.1:p.error('explicit MQTT TLS endpoint/certificate/key and interval>=0.1 required')
    import paho.mqtt.client as mqtt
    client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id='carbentra-virtual-three-device-bridge')
    client.tls_set(args.ca,certfile=args.certificate,keyfile=args.key,tls_version=ssl.PROTOCOL_TLS_CLIENT);client.tls_insecure_set(False)
    def connect(c,*_):
        for room in rooms:
            c.subscribe(f'carbentra/v1/{room.plug.device_id}/cmd',qos=1);c.subscribe(f'carbentra/switch/{room.switch.device_id}/command',qos=1)
    def message(c,u,msg):
        if msg.retain:return
        try:
            raw=strict_json(msg.payload)
            for room in rooms:
                answer=room.command(msg.topic,raw)
                if answer:c.publish(answer[0],canonical(answer[1]),qos=1,retain=False)
        except (ValueError,TypeError,KeyError):pass
    client.on_connect=connect;client.on_message=message;client.connect(args.broker,args.port);client.loop_start()
    try:
        tick=0
        while args.ticks==0 or tick<args.ticks:
            for room in rooms:
                if args.scenario=='manual-hold' and tick==2:room.press_local()
                for topic,payload in room.messages(present=(tick//30)%2==0):
                    if args.scenario=='sensor-outage' and tick>=3 and '/virtual/' in topic:continue
                    client.publish(topic,canonical(payload),qos=1,retain=False)
            tick+=1;time.sleep(args.interval)
    finally:client.disconnect();client.loop_stop()

if __name__=='__main__':main()
