import asyncio
import pytest

import central_system


class DummyWebSocket:
    def __init__(self, path, headers=None, subprotocol="ocpp1.6", remote_address=("127.0.0.1", 1234)):
        self.path = path
        self.request_headers = headers or {}
        self.subprotocol = subprotocol
        self.available_subprotocols = ["ocpp1.6"]
        self.remote_address = remote_address
        self._closed = False

    async def close(self):
        self._closed = True


class FakeChargePoint:
    instances = []

    def __init__(self, charge_point_id, websocket):
        self.id = charge_point_id
        self.websocket = websocket
        self.started = False
        self.listened = False
        FakeChargePoint.instances.append(self)

    async def start(self):
        self.started = True

    async def mqtt_listen(self):
        self.listened = True


@pytest.mark.asyncio
async def test_on_connect_missing_station(monkeypatch):
    FakeChargePoint.instances = []
    monkeypatch.setattr(central_system, "ChargePoint", FakeChargePoint)

    ws = DummyWebSocket(path="/")

    await central_system.on_connect(ws)

    assert FakeChargePoint.instances
    cp_instance = FakeChargePoint.instances[0]
    assert cp_instance.started and cp_instance.listened
    assert cp_instance.id.startswith("cp_")
    assert not ws._closed


@pytest.mark.asyncio
async def test_on_connect_without_subprotocol_header(monkeypatch):
    FakeChargePoint.instances = []
    monkeypatch.setattr(central_system, "ChargePoint", FakeChargePoint)

    ws = DummyWebSocket(path="/ocpp?station=demo", headers={}, subprotocol=None)

    await central_system.on_connect(ws)

    assert FakeChargePoint.instances
    cp_instance = FakeChargePoint.instances[0]
    assert cp_instance.id == "demo"
    assert not ws._closed
