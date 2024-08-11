# OCPP server with ability to send commands by mqtt
# for home automation projects
# based on : https://github.com/rzylius/ocpp-mqtt


import asyncio
import logging
import sys
import os
from dotenv import load_dotenv
import signal

# check dependancies
try:
    import websockets
except ModuleNotFoundError:
    print("This example relies on the 'websockets' package.")
    print("Please install it by running: ")
    print()
    print(" $ pip install websockets")
    import sys

    sys.exit(1)

from charge_point import ChargePoint

logging.basicConfig(level=logging.INFO)

load_dotenv(verbose=True)

LISTEN_ADDR=os.getenv('LISTEN_ADDR') # 0.0.0.0 for localhost
LISTEN_PORT=int(os.getenv('LISTEN_PORT')) # 9000


async def on_connect(websocket, path):
    """For every new charge point that connects, create a ChargePoint
    instance and start listening for messages.
    """
    try:
        requested_protocols = websocket.request_headers["Sec-WebSocket-Protocol"]
    except KeyError:
        logging.error("Client hasn't requested any Subprotocol. Closing Connection")
        return await websocket.close()
    if websocket.subprotocol:
        logging.info("Protocols Matched: %s", websocket.subprotocol)
    else:
        # In the websockets lib if no subprotocols are supported by the
        # client and the server, it proceeds without a subprotocol,
        # so we have to manually close the connection.
        logging.warning(
            "Protocols Mismatched | Expected Subprotocols: %s,"
            " but client supports  %s | Closing connection",
            websocket.available_subprotocols,
            requested_protocols,
        )
        return await websocket.close()

    charge_point_id = path.strip("/")
    cpSession = ChargePoint(charge_point_id, websocket)
    cpSession.heartbeat = 0
    
    await asyncio.gather(cpSession.mqtt_listen(), cpSession.start())

    print("Chargepoint session instance successfully created")

class SignalHandler:
    shutdown_requested = False

    def __init__(self):
        signal.signal(signal.SIGINT, self.request_shutdown)
        signal.signal(signal.SIGTERM, self.request_shutdown)

    def request_shutdown(self, *args):
        print('Request to shutdown received, stopping')
        self.shutdown_requested = True
        sys.exit(0)

    def can_run(self):
        return not self.shutdown_requested


async def main():
    server = await websockets.serve(on_connect, LISTEN_ADDR, LISTEN_PORT, subprotocols=["ocpp1.6"], ping_timeout = None)
    logging.info("Server Started listening to new ocpp connections...")
    await server.wait_closed()

signal_handler = SignalHandler()   

if sys.platform.lower() == "win32" or os.name.lower() == "nt":
    from asyncio import set_event_loop_policy, WindowsSelectorEventLoopPolicy
    set_event_loop_policy(WindowsSelectorEventLoopPolicy())


if __name__ == "__main__":
    # asyncio.run() is used when running this example with Python >= 3.7v
    asyncio.run(main())