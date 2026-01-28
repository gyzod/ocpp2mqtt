# OCPP server with ability to send commands by mqtt
# for home automation projects
# based on : https://github.com/rzylius/ocpp-mqtt


import asyncio
import logging
import sys
import os
import urllib.parse
from dotenv import load_dotenv
import signal

# Version information
from version import __version__, get_banner

# Configure logging before other imports
from logging_config import configure_root_logging
configure_root_logging()

# check dependancies
try:
    import websockets
except ModuleNotFoundError:
    logging.error("This example relies on the 'websockets' package.")
    logging.error("Please install it by running: ")
    logging.error(" $ pip install websockets")
    sys.exit(1)

from charge_point import ChargePoint
from websockets.typing import Subprotocol

load_dotenv(verbose=True)

LISTEN_ADDR=os.getenv('LISTEN_ADDR', '0.0.0.0') 
LISTEN_PORT=int(os.getenv('LISTEN_PORT', 3000)) 


async def on_connect(websocket: websockets.ServerConnection):

    request_path = getattr(websocket, "path", "") or ""
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
        charge_point_id = f"cp_{host}_{port}"
        logging.warning("No charge point station provided, fallback id %s", charge_point_id)

    logging.info("Charge Point ID: %s", charge_point_id)

    cpSession = ChargePoint(charge_point_id, websocket)
    
    await asyncio.gather(cpSession.mqtt_listen(), cpSession.start())

    logging.info("Chargepoint session instance successfully created")

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


async def main():
    # Display startup banner
    print(get_banner())
    logging.info("Starting ocpp2mqtt version %s", __version__)
    
    server = await websockets.serve(
        on_connect,
        LISTEN_ADDR,
        LISTEN_PORT,
        subprotocols=[Subprotocol("ocpp1.6")],
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
