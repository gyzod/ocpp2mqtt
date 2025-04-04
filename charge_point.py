import logging
import os
import json as JSON
import mqtt_2_charge_point 

from dotenv import load_dotenv
from datetime import datetime
from aiomqtt import Client
from aiomqtt import MqttError

from ocpp.routing import on
from ocpp.v16 import ChargePoint as cp
from ocpp.v16.enums import AuthorizationStatus, Action, RegistrationStatus
from ocpp.v16 import call_result

logging.basicConfig(level=logging.INFO)

load_dotenv(verbose=True)
MQTT_HOSTNAME=os.getenv('MQTT_HOSTNAME')
MQTT_PORT=int(os.getenv('MQTT_PORT'))
MQTT_BASEPATH=os.getenv('MQTT_BASEPATH')
MQTT_USERNAME=os.getenv('MQTT_USERNAME', None)
MQTT_PASSWORD=os.getenv('MQTT_PASSWORD', None)

# specify the tag_ID which is authorized in the charge station. 
# Remote server has to send to CP authorised ID in order to start charging
AUTHORIZED_TAG_ID_LIST=JSON.loads(os.getenv('AUTHORIZED_TAG_ID_LIST'))
# global variable for all charge points
charging_enabled = "OFF"

class ChargePoint(cp):

    transaction_id = 1
    authorized_tag_id = ""
    status = "Unknown"
        
    def is_charging_enabled(self):
        global charging_enabled
        return (charging_enabled == "ON")

    def get_transaction_id(self):
        #self.transaction_id += 1
        return self.transaction_id

    #Received events from the charge point

    @on(Action.Authorize)
    async def on_authorize(self, id_tag: str):
        print('---> Starting authorize process')
        
        acceptedTag = (id_tag in AUTHORIZED_TAG_ID_LIST)

        if acceptedTag and self.is_charging_enabled():
            authorization=AuthorizationStatus.accepted
            self.authorized_tag_id=id_tag
        else:
            authorization=AuthorizationStatus.blocked

        print('---> Charging enabled : ', self.is_charging_enabled())
        print('---> Authorize tag accepted : ', acceptedTag)
        print('---> Authorize result : ', authorization)
            
        await self.push_state_value_mqtt("authorize", authorization)
        return call_result.Authorize(id_tag_info={'status': authorization})
    

    @on(Action.BootNotification)
    async def on_boot_notification(self, charge_point_vendor: str, charge_point_model: str, **kwargs):
        print('---> Boot Notification')
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
        print("---> Data Transfer")
        await self.push_state_values_mqtt(self, **kwargs)
        #return not implemented

    @on(Action.DiagnosticsStatusNotification)
    async def on_diagnostics_status_notification(self, **kwargs):
        print("---> DiagnosticsStatusNotification")
        await self.push_state_values_mqtt(**kwargs)
        return call_result.DiagnosticsStatusNotification()

    @on(Action.FirmwareStatusNotification)
    async def on_firmware_status_notification(self, **kwargs):
        print("---> FirmwareStatusNotification")
        await self.push_state_values_mqtt(**kwargs)
        return call_result.FirmwareStatusNotification()

    @on(Action.Heartbeat)
    async def on_heartbeat(self):
        print("---> Heartbeat ")
        await self.push_state_value_mqtt('heartbeat', 'ON')
        await self.push_state_value_mqtt('last_seen', datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S") + "Z")
            
        return call_result.Heartbeat(current_time=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S") + "Z")
    
    @on(Action.MeterValues)
    async def on_meter_values(self, **kwargs):
        print('---> Meter values')
        
        for i in kwargs['meter_value'][0]['sampled_value']:
            measure = (i['measurand']).replace('.','_').lower()
            value = i['value']
            await self.push_state_value_mqtt(measure, value)

        for k,v in kwargs.items():
            print(k, v)
        
        return call_result.MeterValues()
    
    @on(Action.StartTransaction)
    async def on_start_transaction(self, connector_id: int, id_tag: str, meter_start: int, timestamp: str, **kwargs):
        print('---> Start transaction')

        await self.push_state_value_mqtt("meter_start_timestamp", timestamp)
        await self.push_state_value_mqtt("meter_start", meter_start)
        await self.push_state_values_mqtt(**kwargs)
        
        for k,v in kwargs.items():
            print(k, v)

        if self.is_charging_enabled():
            authStatus = AuthorizationStatus.accepted
        else:
            authStatus = AuthorizationStatus.blocked

        print('---> Charging enabled : ', self.is_charging_enabled())
        print('---> Start transaction result : ', authStatus)
               
        return call_result.StartTransaction(
            id_tag_info={'status': authStatus},
            transaction_id=self.get_transaction_id()
        )

    @on(Action.StatusNotification)
    async def on_status_notification(self, connector_id: int, error_code: str, status: str, **kwargs):
        print("---> Status Notification")
        await self.push_state_value_mqtt('error_code', error_code)
        await self.push_state_value_mqtt('status', status)
        await self.push_state_value_mqtt('connector_id', connector_id)
        await self.push_state_values_mqtt(**kwargs)

        # local persistence of the status
        self.status = status

        return call_result.StatusNotification()
    
    @on(Action.StopTransaction)
    async def on_stop_transaction(self,  **kwargs):
        print('---> Stopped transaction')

        await self.push_state_value_mqtt("meter_stop_timestamp", kwargs['timestamp'])
        await self.push_state_value_mqtt("meter_stop", kwargs['meter_stop'])
        await self.push_state_value_mqtt("meter_stop_reason", kwargs['reason'])
        
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

    async def push_call_return_mqtt(self, result):
        for k,v in result.items():
            await self.client.publish(f"{MQTT_BASEPATH}/cmd_result/{k}", payload=v)

    ## received events from MQTT
    async def mqtt_listen(self):
        print("Starting MQTT loop...")
        try:
            async with Client(hostname=MQTT_HOSTNAME,port=MQTT_PORT, user=MQTT_USERNAME, password=MQTT_PASSWORD) as client:
                self.client=client
                await client.subscribe(f"{MQTT_BASEPATH}/cmd/#")
                async for message in client.messages:
                    print("<-- MQTT msg received : ", message.payload)
                    msg = JSON.loads(message.payload.decode("utf-8"))
                    match msg['action']:
                        case 'charging_enabled':  #logical master switch
                            global charging_enabled
                            charging_enabled = self.get_args(msg)
                            print("<-- Charging enabled : ", charging_enabled)
                            result = None
                        case 'cancel_reservation':
                            result = await mqtt_2_charge_point.cancel_reservation(self, self.get_args(msg))
                        case 'change_availability':
                            result = await mqtt_2_charge_point.change_availability(self, self.get_args(msg))
                        case 'change_configuration':
                            result = await mqtt_2_charge_point.change_configuration(self, self.get_args(msg))
                        case 'clear_cache':
                            result = await mqtt_2_charge_point.clear_cache(self, self.get_args(msg))
                        case 'clear_charging_profile':
                            result = await mqtt_2_charge_point.clear_charging_profile(self, self.get_args(msg))
                        case 'data_transfer':
                            result = await mqtt_2_charge_point.data_transfer(self, self.get_args(msg))
                        case 'get_composite_schedule':
                            result = await mqtt_2_charge_point.get_composite_schedule(self, self.get_args(msg))
                        case 'get_configuration':
                            result = await mqtt_2_charge_point.get_configuration(self, self.get_args(msg))
                        case 'get_diagnostics':
                            result = await mqtt_2_charge_point.get_diagnostics(self, self.get_args(msg))
                        case 'get_local_version':
                            result = await mqtt_2_charge_point.get_local_version(self, self.get_args(msg))
                        case 'remote_start_transaction':
                            result = await mqtt_2_charge_point.remote_start_transaction(self, self.get_args(msg))
                        case 'remote_stop_transaction':
                            result = await mqtt_2_charge_point.remote_stop_transaction(self, self.get_args(msg))
                        case 'reserve_now':
                            result = await mqtt_2_charge_point.reserve_now(self, self.get_args(msg))
                        case 'reset':
                            result = await mqtt_2_charge_point.reset(self, self.get_args(msg))
                        case 'send_local_list':
                            result = await mqtt_2_charge_point.send_local_list(self, self.get_args(msg))
                        case 'set_charging_profile':
                            result = await mqtt_2_charge_point.set_charging_profile(self, self.get_args(msg))
                        case 'trigger_message':
                            result = await mqtt_2_charge_point.trigger_message(self, self.get_args(msg))
                        case 'unlock_connector':
                            result = await mqtt_2_charge_point.unlock_connector(self, self.get_args(msg))
                        case 'update_firmware':
                            result = await mqtt_2_charge_point.update_firmware(self, self.get_args(msg))
                        case _:
                            print("Action not found")  
                            result = None
                    if result:
                        print("--> MQTT result : ", result)
                        try:
                            await self.push_call_return_mqtt(vars(result))
                        except Exception as e:
                            print("Error publishing call result to MQTT : " + str(e))
                                          
        except MqttError as e:
            print("MQTT error: " + str(e))
            raise e
        except Exception as e:
            print("Error: " + str(e))
            raise e
        
    def get_args(self,msg):
        if 'args' in msg:
            return msg['args']
        else: 
            return None