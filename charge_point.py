# OCPP server with ability to send commands by mqtt
# for home automation projects
# based on : https://github.com/rzylius/ocpp-mqtt

import logging
from datetime import datetime
from aiomqtt import Client
from aiomqtt import MqttError
import sys
import os
from dotenv import load_dotenv
import json as JSON
import mqtt_2_charge_point 

from ocpp.routing import on
from ocpp.v16 import ChargePoint as cp
from ocpp.v16.enums import AuthorizationStatus, Action, RegistrationStatus, RemoteStartStopStatus, MessageTrigger, AvailabilityType
from ocpp.v16.enums import AvailabilityStatus, ResetStatus
from ocpp.v16 import call_result, call

logging.basicConfig(level=logging.INFO)

load_dotenv(verbose=True)
MQTT_HOSTNAME=os.getenv('MQTT_HOSTNAME')
MQTT_PORT=int(os.getenv('MQTT_PORT'))

MQTT_BASEPATH=os.getenv('MQTT_BASEPATH')

# specify the tag_ID which is authorized in the charge station. 
# Remote server has to send to CP authorised ID in order to start charging
AUTHORIZED_TAG_ID_LIST=JSON.loads(os.getenv('AUTHORIZED_TAG_ID_LIST'))

class ChargePoint(cp):

    transaction_id = 0
    authorized_tag_id = ""

    def get_transaction_id(self):
        self.transaction_id += 1
        return self.transaction_id

    #Received events from the charge point
    @on(Action.Authorize)
    async def on_authorize(self, id_tag: str):
        print('--- Authorize CP')
        
        if id_tag in AUTHORIZED_TAG_ID_LIST:
            print('--- Authorized')
            authorization=AuthorizationStatus.accepted
            self.authorized_tag_id=id_tag
        else:
            print('--- Not Authorized')
            authorization=AuthorizationStatus.blocked
            
        await self.push_state_value_mqtt(f"authorize_{id_tag}", authorization)
        return call_result.Authorize(id_tag_info={'status': authorization})
    

    @on(Action.BootNotification)
    async def on_boot_notification(self, charge_point_vendor: str, charge_point_model: str, **kwargs):
        print('--- Boot Notification')
        await self.push_state_value_mqtt("charge_point_vendor", charge_point_vendor)
        await self.push_state_value_mqtt("charge_point_model", charge_point_model)
        await self.push_state_values_mqtt(**kwargs)

        return call_result.BootNotification(
            current_time=datetime.utcnow().isoformat(),
            interval=10,
            status=RegistrationStatus.accepted,
        )
    
    @on(Action.DataTransfer)
    async def on_data_transfer(self, **kwargs):
        print("--- Got Data Transfer")
        await self.push_state_values_mqtt(self, **kwargs)
        #return not implemented

    @on(Action.DiagnosticsStatusNotification)
    async def on_diagnostics_status_notification(self, **kwargs):
        print("--- Got DiagnosticsStatusNotification")
        await self.push_state_values_mqtt(**kwargs)
        return call_result.DiagnosticsStatusNotification()

    @on(Action.FirmwareStatusNotification)
    async def on_firmware_status_notification(self, **kwargs):
        print("--- Got FirmwareStatusNotification")
        await self.push_state_values_mqtt(**kwargs)
        return call_result.FirmwareStatusNotification()

    @on(Action.Heartbeat)
    async def on_heartbeat(self):
        print("--- Got a Heartbeat! ")
        await self.push_state_value_mqtt('heartbeat', 'ON')
        await self.push_state_value_mqtt('last_seen', datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S") + "Z")
        return call_result.Heartbeat(current_time=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S") + "Z")
    
    @on(Action.MeterValues)
    async def on_meter_values(self, **kwargs):
        print('--- Meter values CP')
        
        for i in kwargs['meter_value'][0]['sampled_value']:
            measure = (i['measurand']).replace('.','_').lower()
            value = i['value']
            await self.push_state_value_mqtt(measure, value)

        for k,v in kwargs.items():
            print(k, v)
        
        return call_result.MeterValues()
    
    @on(Action.StartTransaction)
    async def on_start_transaction(self, connector_id: int, id_tag: str, meter_start: int, timestamp: str, **kwargs):
        print('--- Started transaction in CP')

        await self.push_state_value_mqtt("ev_connected", "ON")
        await self.push_state_values_mqtt(**kwargs)
        
        for k,v in kwargs.items():
            print(k, v)
        
        return call_result.StartTransaction(
            transaction_id=self.get_transaction_id(),         
            id_tag_info={'status': AuthorizationStatus.accepted}
        )

    @on(Action.StatusNotification)
    async def on_status_notification(self, connector_id: int, error_code: str, status: str, **kwargs):
        print("--- Got Status Notification")
        await self.push_state_value_mqtt('error_code', error_code)
        await self.push_state_value_mqtt('status', status)
        await self.push_state_values_mqtt(**kwargs)
        return call_result.StatusNotification()
    
    @on(Action.StopTransaction)
    async def on_stop_transaction(self,  **kwargs):
        print('--- Stopped transaction in CP')

        await self.push_state_value_mqtt("ev_connected", "OFF")
        await self.push_state_values_mqtt(**kwargs)

        for k,v in kwargs.items():
            print(k, v)

        return call_result.StopTransaction(
            id_tag_info={'status': AuthorizationStatus.accepted}
        )
   
    # MQTT implementation

    ## MQTT publish

    async def push_state_values_mqtt(self,**kwargs):
        for k,v in kwargs.items():
            await self.client.publish(f"{MQTT_BASEPATH}/state/{k}", payload=v)

    async def push_state_value_mqtt(self, key, value):
        await self.client.publish(f"{MQTT_BASEPATH}/state/{key}", payload=value)

    ## received events from MQTT
    async def mqtt_listen(self):
        print("start mqtt")

        try:
            async with Client(hostname=MQTT_HOSTNAME,port=MQTT_PORT) as client:
                self.client=client
                await client.subscribe(f"{MQTT_BASEPATH}/cmd/#")
                async for message in client.messages:
                    msg = JSON.loads(message.payload.decode("utf-8"))
                    print("MQTT msg: ")
                    print(msg)
                    match msg['op']:
                        case 'cancel_reservation':
                            await mqtt_2_charge_point.cancel_reservation(self, msg['message'])
                        case 'change_availability':
                            await mqtt_2_charge_point.change_availability(self, msg['message'])
                        case 'change_configuration':
                            await mqtt_2_charge_point.change_configuration(self, msg['message'])
                        case 'clear_cache':
                            await mqtt_2_charge_point.clear_cache(self, msg['message'])
                        case 'clear_charging_profile':
                            await mqtt_2_charge_point.clear_charging_profile(self, msg['message'])
                        case 'data_transfer':
                            await mqtt_2_charge_point.data_transfer(self, msg['message'])
                        case 'get_composite_schedule':
                            await mqtt_2_charge_point.get_composite_schedule(self, msg['message'])
                        case 'get_configuration':
                            await mqtt_2_charge_point.get_configuration(self, msg['message'])
                        case 'get_diagnostics':
                            await mqtt_2_charge_point.get_diagnostics(self, msg['message'])
                        case 'get_local_version':
                            await mqtt_2_charge_point.get_local_version(self, msg['message'])
                        case 'remote_start_transaction':
                            await mqtt_2_charge_point.remote_start_transaction(self, msg['message'])
                        case 'remote_stop_transaction':
                            await mqtt_2_charge_point.remote_stop_transaction(self, msg['message'])
                        case 'reserve_now':
                            await mqtt_2_charge_point.reserve_now(self, msg['message'])
                        case 'reset':
                            await mqtt_2_charge_point.reset(self, msg['message'])
                        case 'send_local_list':
                            await mqtt_2_charge_point.send_local_list(self, msg['message'])
                        case 'set_charging_profile':
                            await mqtt_2_charge_point.set_charging_profile(self, msg['message'])
                        case 'trigger_message':
                            await mqtt_2_charge_point.trigger_message(self, msg['message'])
                        case 'unlock_connector':
                            await mqtt_2_charge_point.unlock_connector(self, msg['message'])
                        case 'update_firmware':
                            await mqtt_2_charge_point.update_firmware(self, msg['message'])
                        case _:
                            print("Operation not found")                    
        except MqttError as e:
            print("MQTT error: " + str(e))
            raise e
        except Exception as e:
            print("Error: " + str(e))
            raise e
