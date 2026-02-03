import asyncio
import logging
import os
import re
import json as JSON
import mqtt_2_charge_point 

from dotenv import load_dotenv
from datetime import datetime
from aiomqtt import Client
from aiomqtt import MqttError
from websockets.protocol import State

from ocpp.routing import on
from ocpp.v16 import ChargePoint as cp
from ocpp.v16.enums import AuthorizationStatus, Action, RegistrationStatus
from ocpp.v16 import call_result

# Use logger from logging_config (configured by central_system.py)
logger = logging.getLogger(__name__)

load_dotenv(verbose=True)
MQTT_HOSTNAME=os.getenv('MQTT_HOSTNAME', 'localhost')
MQTT_PORT=int(os.getenv('MQTT_PORT', '1883'))
MQTT_BASEPATH=os.getenv('MQTT_BASEPATH', 'ocpp/test')
MQTT_USERNAME=os.getenv('MQTT_USERNAME', None)
MQTT_PASSWORD=os.getenv('MQTT_PASSWORD', None)
MQTT_RECONNECT_BASE_DELAY=int(os.getenv('MQTT_RECONNECT_BASE_DELAY', 5))
MQTT_RECONNECT_MAX_DELAY=int(os.getenv('MQTT_RECONNECT_MAX_DELAY', 60))
MQTT_KEEPALIVE=int(os.getenv('MQTT_KEEPALIVE', 60))
MQTT_TIMEOUT=float(os.getenv('MQTT_TIMEOUT', 30))
MQTT_TRANSPORT=os.getenv('MQTT_TRANSPORT', 'tcp').lower()
MQTT_CLIENT_ID=os.getenv('MQTT_CLIENT_ID', None)
MQTT_WEBSOCKET_PATH=os.getenv('MQTT_WEBSOCKET_PATH', None)
MQTT_USESTATIONNAME=os.getenv('MQTT_USESTATIONNAME', None)

# OCPP command retry configuration
OCPP_COMMAND_RETRY_ATTEMPTS=int(os.getenv('OCPP_COMMAND_RETRY_ATTEMPTS', '5'))
OCPP_COMMAND_RETRY_BASE_DELAY=float(os.getenv('OCPP_COMMAND_RETRY_BASE_DELAY', '0.3'))

_MQTT_ALLOWED_TRANSPORTS = {'tcp', 'websockets', 'unix'}
if MQTT_TRANSPORT not in _MQTT_ALLOWED_TRANSPORTS:
    logging.warning("Unsupported MQTT_TRANSPORT '%s'. Falling back to 'tcp'", MQTT_TRANSPORT)
    MQTT_TRANSPORT = 'tcp'

_raw_ws_headers = os.getenv('MQTT_WEBSOCKET_HEADERS', None)
if _raw_ws_headers:
    try:
        MQTT_WEBSOCKET_HEADERS = JSON.loads(_raw_ws_headers)
    except JSON.JSONDecodeError:
        logging.warning("Invalid MQTT_WEBSOCKET_HEADERS JSON, ignoring value.")
        MQTT_WEBSOCKET_HEADERS = None
else:
    MQTT_WEBSOCKET_HEADERS = None

# specify the tag_ID which is authorized in the charge station. 
# Remote server has to send to CP authorised ID in order to start charging
AUTHORIZED_TAG_ID_LIST=JSON.loads(os.getenv('AUTHORIZED_TAG_ID_LIST', '[]'))
# global variable for all charge points
# charging_enabled = "OFF"

class ChargePoint(cp):

    transaction_id = 1
    authorized_tag_id = ""
    status = "Unknown"
    client = None
    charging_enabled = "OFF"
    _shutdown = False
    _websocket_connected = False
    _connection_announced = False

    def __init__(self, id, connection, response_timeout=30):
        super().__init__(id, connection, response_timeout)
        self.charging_enabled = "OFF"
        self._shutdown = False
        self._websocket_connected = False
        self._connection_announced = False
        
    def _mqtt_identifier(self):
        base_identifier = MQTT_CLIENT_ID or f"ocpp2mqtt-{self.id}"
        sanitized = re.sub(r"[^A-Za-z0-9_-]", "-", base_identifier)
        # MQTT v3.1 limits client id length to 23 characters. Truncate while
        # keeping most of the unique suffix for multi-CP deployments.
        if len(sanitized) > 23:
            sanitized = sanitized[:11] + sanitized[-12:]
        return sanitized

    def _mqtt_client_options(self):
        options = {
            "identifier": self._mqtt_identifier(),
            "transport": MQTT_TRANSPORT,
            "keepalive": MQTT_KEEPALIVE,
            "timeout": MQTT_TIMEOUT,
        }
        if MQTT_WEBSOCKET_PATH:
            options["websocket_path"] = MQTT_WEBSOCKET_PATH
        if MQTT_WEBSOCKET_HEADERS:
            options["websocket_headers"] = MQTT_WEBSOCKET_HEADERS

        return options

    def _has_active_websocket(self):
        """Check if the OCPP WebSocket connection is active."""
        connection = getattr(self, "_connection", None)
        if connection is None:
            logging.debug("No WebSocket connection object found")
            return False
        
        # Try multiple ways to check connection state for compatibility
        # with different websockets library versions
        
        # Method 1: Check state attribute (websockets 10+)
        if hasattr(connection, 'state'):
            state = connection.state
            # State.OPEN is 1, State.CLOSING is 2, State.CLOSED is 3
            # We consider OPEN and CLOSING as "usable" for sending final messages
            is_open = (state == State.OPEN) or (state == 1)
            logging.debug("WebSocket state check: state=%s, is_open=%s", state, is_open)
            return is_open
        
        # Method 2: Check open property (older websockets)
        if hasattr(connection, 'open'):
            is_open = bool(connection.open)
            logging.debug("WebSocket open property: %s", is_open)
            return is_open

        # Method 3: Check closed property (fallback)
        if hasattr(connection, 'closed'):
            is_open = not connection.closed
            logging.debug("WebSocket closed property: %s, is_open=%s", connection.closed, is_open)
            return is_open
        
        # Method 4: Try to check if connection object is still valid
        # by checking if it has a send method (last resort)
        if hasattr(connection, 'send') and callable(connection.send):
            logging.debug("WebSocket has send method, assuming connected")
            return True
                
        logging.debug("Could not determine WebSocket state")
        return False

    def is_charging_enabled(self):
        return (self.charging_enabled == "ON")

    def _normalize_charging_enabled(self, value):
        """Normalize charging_enabled payloads to 'ON' or 'OFF'."""
        if isinstance(value, bool):
            return "ON" if value else "OFF"

        if isinstance(value, (int, float)):
            return "ON" if value else "OFF"

        if isinstance(value, str):
            normalized = value.strip().upper()
            if normalized in {"ON", "TRUE", "1", "YES", "Y"}:
                return "ON"
            if normalized in {"OFF", "FALSE", "0", "NO", "N"}:
                return "OFF"

        return "OFF"

    def get_transaction_id(self):
        return self.transaction_id

    def get_mqttpath(self):
        mqtt_path = MQTT_BASEPATH
        if MQTT_USESTATIONNAME == "true":
            mqtt_path +=self.id
        return mqtt_path
        
    #Received events from the charge point

    @on(Action.authorize)
    async def on_authorize(self, id_tag: str):
        logging.info('---> Starting authorize process')
        
        acceptedTag = (id_tag in AUTHORIZED_TAG_ID_LIST)

        if acceptedTag and self.is_charging_enabled():
            authorization=AuthorizationStatus.accepted
            self.authorized_tag_id=id_tag
        else:
            authorization=AuthorizationStatus.blocked

        logging.info('---> Charging enabled : %s', self.is_charging_enabled())
        logging.info('---> Authorize tag accepted : %s', acceptedTag)
        logging.info('---> Authorize result : %s', authorization)
            
        await self.push_state_value_mqtt("authorize", authorization)
        return call_result.Authorize(id_tag_info={'status': authorization})
    

    @on(Action.boot_notification)
    async def on_boot_notification(self, charge_point_vendor: str, charge_point_model: str, **kwargs):
        logging.info('---> Boot Notification')
        await self.push_state_value_mqtt("charge_point_vendor", charge_point_vendor)
        await self.push_state_value_mqtt("charge_point_model", charge_point_model)
        await self.push_state_values_mqtt(**kwargs)

               
        return call_result.BootNotification(
            current_time=datetime.utcnow().isoformat(),
            interval=10,
            status=RegistrationStatus.accepted,
        )
    
    @on(Action.data_transfer)
    async def on_data_transfer(self, **kwargs):
        logging.info("---> Data Transfer")
        await self.push_state_values_mqtt(**kwargs)
        #return not implemented

    @on(Action.diagnostics_status_notification)
    async def on_diagnostics_status_notification(self, **kwargs):
        logging.info("---> DiagnosticsStatusNotification")
        await self.push_state_values_mqtt(**kwargs)
        return call_result.DiagnosticsStatusNotification()

    @on(Action.firmware_status_notification)
    async def on_firmware_status_notification(self, **kwargs):
        logging.info("---> FirmwareStatusNotification")
        await self.push_state_values_mqtt(**kwargs)
        return call_result.FirmwareStatusNotification()

    @on(Action.heartbeat)
    async def on_heartbeat(self):
        logging.info("---> Heartbeat ")
        await self.push_state_value_mqtt('heartbeat', 'ON')
        await self.push_state_value_mqtt('last_seen', datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S") + "Z")
            
        return call_result.Heartbeat(current_time=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S") + "Z")
    
    @on(Action.meter_values)
    async def on_meter_values(self, **kwargs):
        logging.info('---> Meter values')

        self.transaction_id = kwargs.get('transaction_id', self.transaction_id)        
        await self.push_state_value_mqtt('transaction_id', self.transaction_id)
        
        for i in kwargs['meter_value'][0]['sampled_value']:
            measure = (i['measurand']).replace('.','_').lower()
            value = i['value']
            await self.push_state_value_mqtt(measure, value)

        for k,v in kwargs.items():
            logging.info("%s: %s", k, v)
        
        return call_result.MeterValues()
    
    @on(Action.start_transaction)
    async def on_start_transaction(self, connector_id: int, id_tag: str, meter_start: int, timestamp: str, **kwargs):
        logging.info('---> Start transaction')

        await self.push_state_value_mqtt("meter_start_timestamp", timestamp)
        await self.push_state_value_mqtt("meter_start", meter_start)
        await self.push_state_values_mqtt(**kwargs)
        
        for k,v in kwargs.items():
            logging.info("%s: %s", k, v)

        if self.is_charging_enabled():
            authStatus = AuthorizationStatus.accepted
        else:
            authStatus = AuthorizationStatus.blocked

        logging.info('---> Charging enabled : %s', self.is_charging_enabled())
        logging.info('---> Start transaction result : %s', authStatus)
               
        return call_result.StartTransaction(
            id_tag_info={'status': authStatus},
            transaction_id=self.get_transaction_id()
        )

    @on(Action.status_notification)
    async def on_status_notification(self, connector_id: int, error_code: str, status: str, **kwargs):
        logging.info("---> Status Notification")
        await self.push_state_value_mqtt('error_code', error_code)
        await self.push_state_value_mqtt('status', status)
        await self.push_state_value_mqtt('connector_id', connector_id)
        await self.push_state_value_mqtt('connection_state', 'CONNECTED')
        await self.push_state_value_mqtt('last_status_change', datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S") + "Z")
        await self.push_state_value_mqtt('last_seen', datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S") + "Z")
        await self.push_state_values_mqtt(**kwargs)

        if status != "Charging":
            await self.push_state_value_mqtt('power_active_import', 0)
            await self.push_state_value_mqtt('current_import', 0)

        # local persistence of the status
        self.status = status

        return call_result.StatusNotification()
    
    @on(Action.stop_transaction)
    async def on_stop_transaction(self,  **kwargs):
        logging.info('---> Stopped transaction')

        await self.push_state_value_mqtt("meter_stop_timestamp", kwargs['timestamp'])
        await self.push_state_value_mqtt("meter_stop", kwargs['meter_stop'])
        await self.push_state_value_mqtt("meter_stop_reason", kwargs['reason'])
        
        for k,v in kwargs.items():
            logging.info("%s: %s", k, v)

        return call_result.StopTransaction(
            id_tag_info={'status': AuthorizationStatus.accepted}
        )
   
    # MQTT implementation
    ## MQTT publish

    async def push_state_values_mqtt(self,**kwargs):
        mqtt_path = self.get_mqttpath()
        for k,v in kwargs.items():
            await self._mqtt_publish(f"{mqtt_path}/state/{k}", payload=v)

    async def push_state_value_mqtt(self, key, value):
        mqtt_path = self.get_mqttpath()
        await self._mqtt_publish(f"{mqtt_path}/state/{key}", payload=value)

    async def push_call_return_mqtt(self, result):
        mqtt_path = self.get_mqttpath()
        for k,v in result.items():
            await self._mqtt_publish(f"{mqtt_path}/cmd_result/{k}", payload=v)

    async def _mqtt_publish(self, topic, payload):
        client = getattr(self, "client", None)
        if client is None:
            logging.warning("MQTT publish skipped, client unavailable for topic %s", topic)
            return
        try:
            await client.publish(topic, payload=payload, retain=True)
        except MqttError as exc:
            logging.warning("MQTT publish to %s failed: %s", topic, exc)

    def shutdown(self):
        """Signal the MQTT loop to stop."""
        self._shutdown = True
        self._websocket_connected = False
        logging.info("Shutdown requested for %s", self.id)

    async def on_websocket_connected(self):
        """Called when WebSocket connection is established."""
        self._websocket_connected = True
        logging.info("WebSocket connected for %s", self.id)
        await self.push_state_value_mqtt('connection_state', 'CONNECTED')
        await self.push_state_value_mqtt('last_connected', datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S") + "Z")
        self._connection_announced = True

    async def on_websocket_disconnected(self, reason: str = "unknown"):
        """Called when WebSocket connection is lost."""
        was_connected = self._websocket_connected
        self._websocket_connected = False
        logging.info("WebSocket disconnected for %s (reason: %s)", self.id, reason)
        
        # Only publish disconnection if we had announced a connection
        if was_connected or self._connection_announced:
            await self.push_state_value_mqtt('connection_state', 'DISCONNECTED')
            await self.push_state_value_mqtt('last_disconnected', datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S") + "Z")
            await self.push_state_value_mqtt('disconnect_reason', reason)
            # Reset power values on disconnect
            await self.push_state_value_mqtt('power_active_import', 0)
            await self.push_state_value_mqtt('current_import', 0)
            self._connection_announced = False

    def is_websocket_connected(self) -> bool:
        """Check if WebSocket is currently connected."""
        return self._websocket_connected and self._has_active_websocket()

    ## received events from MQTT
    async def mqtt_listen(self):
        logging.info("Starting MQTT loop for %s", self.id)
        reconnect_delay = MQTT_RECONNECT_BASE_DELAY
        while not self._shutdown:
            try:
                async with Client(hostname=MQTT_HOSTNAME,
                                  port=MQTT_PORT,
                                  username=MQTT_USERNAME,
                                  password=MQTT_PASSWORD,
                                  **self._mqtt_client_options()) as client:
                    self.client=client
                    reconnect_delay = MQTT_RECONNECT_BASE_DELAY
                    mqtt_path = self.get_mqttpath()
                    await client.subscribe(f"{mqtt_path}/cmd/#")
                    async for message in client.messages:
                        if self._shutdown:
                            logging.info("MQTT loop shutdown requested for %s", self.id)
                            break
                        try:
                            if isinstance(message.payload, bytes):
                                payload = message.payload.decode("utf-8")
                            else:
                                payload = str(message.payload)
                            logging.info("<-- MQTT msg received : %s", payload)
                            msg = JSON.loads(payload)
                        except (UnicodeDecodeError, JSON.JSONDecodeError) as decode_error:
                            logging.warning("Invalid MQTT payload: %s", decode_error)
                            continue

                        try:
                            result = await self._handle_mqtt_action(msg)
                        except asyncio.CancelledError:
                            logging.info("MQTT action cancelled for %s", self.id)
                            self._shutdown = True
                            raise
                        except Exception as action_error:
                            logging.error("MQTT action %s failed: %s", msg.get('action'), action_error)
                            await self._publish_command_error(msg, action_error)
                            continue

                        if result:
                            logging.info("--> MQTT result : %s", result)
                            try:
                                await self.push_call_return_mqtt(vars(result))
                            except Exception as e:
                                logging.error("Error publishing call result to MQTT : %s", e)
            except asyncio.CancelledError:
                logging.info("MQTT loop cancelled for %s", self.id)
                self._shutdown = True
                raise
            except MqttError as e:
                if self._shutdown:
                    logging.info("MQTT disconnected during shutdown for %s", self.id)
                    break
                logging.warning("MQTT error (%s): %s", type(e).__name__, e)
            except Exception as e:
                if self._shutdown:
                    break
                logging.error("Unexpected MQTT loop error (%s): %s", type(e).__name__, e)
            finally:
                self.client = None

            if self._shutdown:
                break

            wait_time = reconnect_delay
            reconnect_delay = min(reconnect_delay * 2, MQTT_RECONNECT_MAX_DELAY)
            logging.info("Reconnecting to MQTT in %s seconds...", wait_time)
            await asyncio.sleep(wait_time)
        
        logging.info("MQTT loop stopped for %s", self.id)

    async def _wait_for_websocket_connection(self, action: str) -> bool:
        """
        Wait for WebSocket connection to become available with exponential backoff.
        Returns True if connection is available, False otherwise.
        """
        for attempt in range(OCPP_COMMAND_RETRY_ATTEMPTS):
            if self._has_active_websocket():
                if attempt > 0:
                    logging.info("WebSocket reconnected after %d attempt(s) for action '%s'", attempt, action)
                return True
            
            # Log connection state for debugging
            connection = getattr(self, "_connection", None)
            state_info = "None"
            if connection:
                if hasattr(connection, 'state'):
                    state_info = f"state={connection.state}"
                elif hasattr(connection, 'open'):
                    state_info = f"open={connection.open}"
                elif hasattr(connection, 'closed'):
                    state_info = f"closed={connection.closed}"
            
            if attempt < OCPP_COMMAND_RETRY_ATTEMPTS - 1:
                delay = OCPP_COMMAND_RETRY_BASE_DELAY * (2 ** attempt)
                logging.info("WebSocket not ready for '%s' (%s), retry %d/%d in %.2fs", 
                            action, state_info, attempt + 1, OCPP_COMMAND_RETRY_ATTEMPTS, delay)
                await asyncio.sleep(delay)
            else:
                logging.warning("WebSocket check failed for '%s' (%s), no more retries", action, state_info)
        
        return False

    async def _handle_mqtt_action(self, msg):
        action = msg.get('action')
        args = self.get_args(msg)

        if action == 'charging_enabled':
            self.charging_enabled = self._normalize_charging_enabled(args)
            logging.info("<-- Charging enabled : %s", self.charging_enabled)
            return None

        # Wait for WebSocket with retry mechanism to handle brief reconnections
        if not await self._wait_for_websocket_connection(action):
            logging.warning("WebSocket not available after %d retries for action '%s'", 
                          OCPP_COMMAND_RETRY_ATTEMPTS, action)
            raise RuntimeError('Charge point websocket is not connected')

        action_map = {
            'cancel_reservation': mqtt_2_charge_point.cancel_reservation,
            'change_availability': mqtt_2_charge_point.change_availability,
            'change_configuration': mqtt_2_charge_point.change_configuration,
            'clear_cache': mqtt_2_charge_point.clear_cache,
            'clear_charging_profile': mqtt_2_charge_point.clear_charging_profile,
            'data_transfer': mqtt_2_charge_point.data_transfer,
            'get_composite_schedule': mqtt_2_charge_point.get_composite_schedule,
            'get_configuration': mqtt_2_charge_point.get_configuration,
            'get_diagnostics': mqtt_2_charge_point.get_diagnostics,
            'get_local_version': mqtt_2_charge_point.get_local_version,
            'remote_start_transaction': mqtt_2_charge_point.remote_start_transaction,
            'remote_stop_transaction': mqtt_2_charge_point.remote_stop_transaction,
            'reserve_now': mqtt_2_charge_point.reserve_now,
            'reset': mqtt_2_charge_point.reset,
            'send_local_list': mqtt_2_charge_point.send_local_list,
            'set_charging_profile': mqtt_2_charge_point.set_charging_profile,
            'trigger_message': mqtt_2_charge_point.trigger_message,
            'unlock_connector': mqtt_2_charge_point.unlock_connector,
            'update_firmware': mqtt_2_charge_point.update_firmware,
        }

        handler = action_map.get(action)
        if not handler:
            logging.warning("Action not found: %s", action)
            return None

        return await handler(self, args)

    async def _publish_command_error(self, msg, error):
        try:
            await self.push_call_return_mqtt({
                'status': 'error',
                'action': msg.get('action'),
                'error': str(error)
            })
        except Exception as publish_error:
            logging.error("Failed to publish command error: %s", publish_error)
        
    def get_args(self,msg):
        if 'args' in msg:
            return msg['args']
        else: 
            return None
