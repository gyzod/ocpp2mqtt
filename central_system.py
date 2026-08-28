# OCPP server with ability to send commands by mqtt
# for home automation projects
# based on : https://github.com/rzylius/ocpp-mqtt


import asyncio
import logging
import sys
import os
import urllib.parse
import json
import ssl
from dotenv import load_dotenv
import signal
from datetime import datetime, timezone

# Version information
from version import __version__, get_banner

# Configure logging before other imports
from logging_config import configure_root_logging
configure_root_logging()

# check dependancies
try:
    import websockets
    import websockets.exceptions
except ModuleNotFoundError:
    logging.error("This example relies on the 'websockets' package.")
    logging.error("Please install it by running: ")
    logging.error(" $ pip install websockets")
    sys.exit(1)

from charge_point import ChargePoint
from websockets.asyncio.server import basic_auth
from websockets.typing import Subprotocol

load_dotenv(verbose=True)

LISTEN_ADDR=os.getenv('LISTEN_ADDR', '0.0.0.0') 
LISTEN_PORT=int(os.getenv('LISTEN_PORT', 3000))
WEBSOCKET_AUTH_USERNAME = os.getenv('WEBSOCKET_AUTH_USERNAME', '')
WEBSOCKET_AUTH_PASSWORD = os.getenv('WEBSOCKET_AUTH_PASSWORD', '')
WEBSOCKET_SSL_CERTFILE = os.getenv('WEBSOCKET_SSL_CERTFILE', '')
WEBSOCKET_SSL_KEYFILE = os.getenv('WEBSOCKET_SSL_KEYFILE', '')

if bool(WEBSOCKET_AUTH_USERNAME) != bool(WEBSOCKET_AUTH_PASSWORD):
    raise ValueError(
        "WEBSOCKET_AUTH_USERNAME and WEBSOCKET_AUTH_PASSWORD must be set together"
    )

if bool(WEBSOCKET_SSL_CERTFILE) != bool(WEBSOCKET_SSL_KEYFILE):
    raise ValueError(
        "WEBSOCKET_SSL_CERTFILE and WEBSOCKET_SSL_KEYFILE must be set together"
    )

# Expected charge points - publish DISCONNECTED state on startup
_raw_expected_cps = os.getenv('EXPECTED_CHARGE_POINTS', '[]')
try:
    EXPECTED_CHARGE_POINTS = json.loads(_raw_expected_cps)
    if not isinstance(EXPECTED_CHARGE_POINTS, list):
        logging.warning("EXPECTED_CHARGE_POINTS should be a JSON array, ignoring")
        EXPECTED_CHARGE_POINTS = []
except json.JSONDecodeError:
    logging.warning("Invalid EXPECTED_CHARGE_POINTS JSON, ignoring")
    EXPECTED_CHARGE_POINTS = [] 

# Registry of active charge point sessions to handle reconnections
_active_sessions: dict[str, asyncio.Task] = {}
_sessions_lock = asyncio.Lock()


async def _cleanup_old_session(charge_point_id: str):
    """Cancel any existing session for this charge point ID."""
    async with _sessions_lock:
        if charge_point_id in _active_sessions:
            old_task = _active_sessions[charge_point_id]
            if not old_task.done():
                logging.info("Cancelling old session for %s (reconnection detected)", charge_point_id)
                old_task.cancel()
                try:
                    await asyncio.wait_for(asyncio.shield(old_task), timeout=2.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
            del _active_sessions[charge_point_id]


async def _process_websocket_request(connection, request):
    """Log safe handshake details before enforcing optional Basic Auth."""
    authorization = request.headers.get("Authorization", "")
    auth_scheme = authorization.split(" ", 1)[0] if authorization else "missing"
    logging.info(
        "WebSocket handshake from %s, path=%s, auth_scheme=%s, subprotocol=%s",
        connection.remote_address,
        request.path,
        auth_scheme,
        request.headers.get("Sec-WebSocket-Protocol", "missing"),
    )

    if _basic_auth is None:
        return None

    response = await _basic_auth(connection, request)
    if response is not None:
        logging.warning(
            "WebSocket handshake rejected with 401 for %s, path=%s, auth_scheme=%s",
            connection.remote_address,
            request.path,
            auth_scheme,
        )
    return response


async def on_connect(websocket: websockets.ServerConnection):

    request = getattr(websocket, "request", None)
    request_path = (
        getattr(request, "path", None)
        or getattr(request, "target", None)
        or getattr(websocket, "path", "")
        or ""
    )
    logging.info("Received new connection from %s, path=%s", websocket.remote_address, request_path)

    charge_point_id = None
    query = {}

    if "?" in request_path:
        query_string = request_path.split("?", 1)[1]
        query = urllib.parse.parse_qs(query_string)
        charge_point_id = query.get("station", [None])[0]
    
    if not charge_point_id:
        # Try to extract from path if it looks like a station ID
        if request_path.startswith("/"):
             potential_id = request_path[1:]
             if potential_id and "?" not in potential_id:
                 charge_point_id = potential_id

    """For every new charge point that connects, create a ChargePoint
    instance and start listening for messages.
    """
    request_headers = getattr(websocket, "request_headers", {}) or {}
    requested_protocols = request_headers.get("Sec-WebSocket-Protocol")
    if not requested_protocols:
        logging.warning("Client hasn't requested any Subprotocol. Continuing without it.")
    if websocket.subprotocol:
        logging.info("Protocols Matched: %s", websocket.subprotocol)
    else:
        msg = (
            "Protocols mismatched | Expected Subprotocols: %s,"
            " but client supports %s. Connection will stay open; ensure the"
            " charge point is configured for ocpp1.6."
        )
        logging.warning(
            msg,
            getattr(websocket, "available_subprotocols", []),
            requested_protocols,
        )


    if not charge_point_id:
        host, port = (websocket.remote_address or ("unknown", "0"))
        # Use only host IP as fallback ID (not port) to handle reconnections gracefully
        # The port changes on each reconnection, causing duplicate ChargePoint instances
        charge_point_id = f"cp_{host}"
        logging.warning("No charge point station provided, fallback id %s (from %s:%s)", charge_point_id, host, port)

    logging.info("Charge Point ID: %s", charge_point_id)

    # Clean up any existing session for this charge point (handles reconnections)
    await _cleanup_old_session(charge_point_id)

    cpSession = ChargePoint(charge_point_id, websocket)
    
    # Create and register the session task
    async def run_session():
        disconnect_reason = "normal_closure"
        try:
            # Announce connection established
            await cpSession.on_websocket_connected()
            await asyncio.gather(cpSession.mqtt_listen(), cpSession.start())
        except asyncio.CancelledError:
            logging.info("Session cancelled for %s", charge_point_id)
            disconnect_reason = "session_cancelled"
            cpSession.shutdown()
        except websockets.exceptions.ConnectionClosed as e:
            disconnect_reason = f"connection_closed_{e.code}"
            logging.warning("WebSocket connection closed for %s: %s", charge_point_id, e)
        except websockets.exceptions.ConnectionClosedError as e:
            disconnect_reason = f"connection_error_{e.code}"
            logging.warning("WebSocket connection error for %s: %s", charge_point_id, e)
        except Exception as e:
            disconnect_reason = f"unexpected_error"
            logging.error("Unexpected error in session for %s: %s", charge_point_id, e)
        finally:
            # Announce disconnection before cleanup
            try:
                await cpSession.on_websocket_disconnected(disconnect_reason)
            except Exception as e:
                logging.warning("Failed to announce disconnection for %s: %s", charge_point_id, e)
            # Ensure shutdown is called to stop MQTT loop
            cpSession.shutdown()
            async with _sessions_lock:
                if charge_point_id in _active_sessions:
                    del _active_sessions[charge_point_id]
            logging.info("Session ended for %s (reason: %s)", charge_point_id, disconnect_reason)
    
    session_task = asyncio.create_task(run_session())
    async with _sessions_lock:
        _active_sessions[charge_point_id] = session_task
    
    # Wait for the session to complete
    await session_task

    logging.info("Chargepoint session completed for %s", charge_point_id)

class SignalHandler:
    shutdown_requested = False

    def __init__(self):
        signal.signal(signal.SIGINT, self.request_shutdown)
        signal.signal(signal.SIGTERM, self.request_shutdown)

    def request_shutdown(self, *args):
        logging.info('Request to shutdown received, stopping')
        self.shutdown_requested = True
        sys.exit(0)

    def can_run(self):
        return not self.shutdown_requested


async def _publish_initial_disconnected_state():
    """Publish DISCONNECTED state for all expected charge points on startup."""
    if not EXPECTED_CHARGE_POINTS:
        logging.debug("No expected charge points configured, skipping initial state publication")
        return
    
    # Import here to avoid circular imports and get MQTT config
    from charge_point import (
        MQTT_HOSTNAME, MQTT_PORT, MQTT_USERNAME, MQTT_PASSWORD, 
        MQTT_BASEPATH, MQTT_USESTATIONNAME, MQTT_TRANSPORT,
        MQTT_KEEPALIVE, MQTT_TIMEOUT
    )
    from aiomqtt import Client, MqttError
    
    try:
        async with Client(
            hostname=MQTT_HOSTNAME,
            port=MQTT_PORT,
            username=MQTT_USERNAME,
            password=MQTT_PASSWORD,
            identifier="ocpp2mqtt-startup",
            transport=MQTT_TRANSPORT,
            keepalive=MQTT_KEEPALIVE,
            timeout=MQTT_TIMEOUT,
        ) as client:
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + "Z"
            
            for cp_id in EXPECTED_CHARGE_POINTS:
                mqtt_path = MQTT_BASEPATH
                if MQTT_USESTATIONNAME == "true":
                    mqtt_path += cp_id
                
                await client.publish(f"{mqtt_path}/state/connection_state", payload="DISCONNECTED", retain=True)
                await client.publish(f"{mqtt_path}/state/service_started", payload=timestamp, retain=True)
                logging.info("Published initial DISCONNECTED state for %s", cp_id)
                
    except MqttError as e:
        logging.warning("Failed to publish initial disconnected states: %s", e)
    except Exception as e:
        logging.error("Unexpected error publishing initial states: %s", e)


async def main():
    # Display startup banner
    print(get_banner())
    logging.info("Starting ocpp2mqtt version %s", __version__)
    
    # Publish initial DISCONNECTED state for expected charge points
    await _publish_initial_disconnected_state()
    
    global _basic_auth
    _basic_auth = None
    if WEBSOCKET_AUTH_USERNAME and WEBSOCKET_AUTH_PASSWORD:
        _basic_auth = basic_auth(
            realm="ocpp2mqtt",
            credentials=(WEBSOCKET_AUTH_USERNAME, WEBSOCKET_AUTH_PASSWORD),
        )
        logging.info("WebSocket Basic Authentication enabled")

    ssl_context = None
    if WEBSOCKET_SSL_CERTFILE and WEBSOCKET_SSL_KEYFILE:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(
            certfile=WEBSOCKET_SSL_CERTFILE,
            keyfile=WEBSOCKET_SSL_KEYFILE,
        )
        logging.info("WebSocket TLS enabled")

    server = await websockets.serve(
        on_connect,
        LISTEN_ADDR,
        LISTEN_PORT,
        subprotocols=[Subprotocol("ocpp1.6")],
        process_request=_process_websocket_request,
        ssl=ssl_context,
        ping_timeout=None,
    )
    logging.info("Server listening on %s:%s for OCPP connections...", LISTEN_ADDR, LISTEN_PORT)
    await server.wait_closed()

signal_handler = SignalHandler()   

if sys.platform.lower() == "win32" or os.name.lower() == "nt":
    try:
        from asyncio.windows_events import WindowsSelectorEventLoopPolicy  # type: ignore[attr-defined]
    except ImportError:  # pragma: no cover - non-Windows environment
        logging.warning("WindowsSelectorEventLoopPolicy unavailable on this platform")
    else:
        asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())


if __name__ == "__main__":
    # asyncio.run() is used when running this example with Python >= 3.7v
    asyncio.run(main())
