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
            
        self.push_state_value_mqtt(self, f"authorize_{id_tag}", authorization)
        return call_result.Authorize(id_tag_info={'status': authorization})
    

    @on(Action.BootNotification)
    def on_boot_notification(self, charge_point_vendor: str, charge_point_model: str, **kwargs):
        print('--- Boot Notification')
        self.push_state_value_mqtt(self, "charge_point_vendor", charge_point_vendor)
        self.push_state_value_mqtt(self, "charge_point_model", charge_point_model)
        self.push_state_values_mqtt(self,**kwargs)

        return call_result.BootNotification(
            current_time=datetime.utcnow().isoformat(),
            interval=10,
            status=RegistrationStatus.accepted,
        )
    
    @on(Action.DataTransfer)
    async def on_data_transfer(self, **kwargs):
        print("--- Got Data Transfer")
        self.push_state_values_mqtt(self, **kwargs)
        #return not implemented

    @on(Action.DiagnosticsStatusNotification)
    async def on_diagnostics_status_notification(self, **kwargs):
        print("--- Got DiagnosticsStatusNotification")
        self.push_state_values_mqtt(self, **kwargs)
        return call_result.DiagnosticsStatusNotification()

    @on(Action.FirmwareStatusNotification)
    async def on_firmware_status_notification(self, **kwargs):
        print("--- Got FirmwareStatusNotification")
        self.push_state_values_mqtt(self, **kwargs)
        return call_result.FirmwareStatusNotification()

    @on(Action.Heartbeat)
    async def on_heartbeat(self):
        print("--- Got a Heartbeat! ")
        await self.push_state_value_mqtt('heartbeat', 'ON')
        await self.push_state_value_mqtt('last_seen', datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S") + "Z")
        return call_result.Heartbeat(
            current_time=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S") + "Z"
        )
    
    @on(Action.MeterValues)
    async def on_meter_values(self, **kwargs):
        print('--- Meter values CP')
        self.push_state_values_mqtt(self,**kwargs)
        for k,v in kwargs.items():
            print(k, v)
        return call_result.MeterValues()
    
    @on(Action.StartTransaction)
    async def on_start_transaction(self, connector_id: int, id_tag: str, meter_start: int, timestamp: str, **kwargs):
        print('--- Started transaction in CP')

        self.push_state_value_mqtt(self,"ev_connected", "ON")
        self.push_state_values_mqtt(self,**kwargs)
        
        for k,v in kwargs.items():
            print(k, v)
        
        return call_result.StartTransaction(
            transaction_id=self.get_transaction_id(),         
            id_tag_info={'status': AuthorizationStatus.accepted}
        )

    @on(Action.StatusNotification)
    async def on_status_notification(
        self, connector_id: int, error_code: str, status: str, **kwargs):
        print("--- Got Status Notification")
        self.push_state_value_mqtt('error_code', error_code)
        self.push_state_value_mqtt('status', status)
        self.push_state_values_mqtt(self,**kwargs)
        return call_result.StatusNotification()
    
    @on(Action.StopTransaction)
    async def on_stop_transaction(self,  **kwargs):
        print('--- Stopped transaction in CP')

        self.push_state_value_mqtt(self,"ev_connected", "OFF")
        self.push_state_values_mqtt(self,**kwargs)

        for k,v in kwargs.items():
            print(k, v)

        return call_result.StopTransaction(
            id_tag_info={'status': AuthorizationStatus.accepted}
        )
   
    # MQTT implementation
    ## mqtt calls

    async def push_state_values_mqtt(self,**kwargs):
        for k,v in kwargs.items():
            await self.client.publish(f"{MQTT_BASEPATH}/state/{k}", payload=v)

    async def push_state_value_mqtt(self, key, value):
        await self.client.publish(f"{MQTT_BASEPATH}/state/{key}", payload=value)

    async def mqtt_listen(self):
        print("start mqtt")

        try:
            async with Client(hostname=MQTT_HOSTNAME,port=MQTT_PORT) as client:
                self.client=client
                await client.subscribe(f"{MQTT_BASEPATH}/cmd/#")
                async for message in client.messages:
                    #msg = str(message.payload.decode("utf-8")).split()
                    msg = JSON.loads(message.payload.decode("utf-8"))
                    print("MQTT msg: ")
                    print(msg)
                    f=getattr(mqtt_2_charge_point, msg['op'])
                    f(self, msg['message'])
                    
        except MqttError as e:
            print("MQTT error: " + str(e))
            raise e
        except Exception as e:
            print("Error: " + str(e))
            raise e
