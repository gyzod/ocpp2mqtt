import types

import pytest

import charge_point as cp_module
from charge_point import ChargePoint
import mqtt_2_charge_point


class DummyConnection:
    def __init__(self, closed=False):
        self.closed = closed


@pytest.mark.asyncio
async def test_mqtt_identifier_truncation(monkeypatch):
    cp = ChargePoint("station-1234567890-abcdef", DummyConnection())

    # Force environment defaults.
    monkeypatch.delenv("MQTT_CLIENT_ID", raising=False)

    identifier = cp._mqtt_identifier()
    assert len(identifier) <= 23
    assert identifier.startswith("ocpp2mqtt-")


@pytest.mark.asyncio
async def test_handle_mqtt_action_no_connection(monkeypatch):
    cp = ChargePoint("station-x", DummyConnection())
    cp._connection.closed = True

    msg = {"action": "remote_start_transaction", "args": {}}
    with pytest.raises(RuntimeError):
        await cp._handle_mqtt_action(msg)


@pytest.mark.asyncio
async def test_handle_mqtt_action_updates_charging_enabled(monkeypatch):
    cp = ChargePoint("station-y", DummyConnection())
    
    await cp._handle_mqtt_action({"action": "charging_enabled", "args": "ON"})

    assert cp.charging_enabled == "ON"


@pytest.mark.asyncio
async def test_handle_mqtt_action_dispatch(monkeypatch):
    cp = ChargePoint("station-z", DummyConnection())

    async def fake_remote_start(self_obj, payload):
        assert self_obj is cp
        assert payload == {"foo": "bar"}
        return types.SimpleNamespace(status="Accepted")

    monkeypatch.setattr(mqtt_2_charge_point, "remote_start_transaction", fake_remote_start)

    result = await cp._handle_mqtt_action({"action": "remote_start_transaction", "args": {"foo": "bar"}})

    assert result is not None
    assert result.status == "Accepted"


@pytest.mark.asyncio
async def test_handle_mqtt_action_unknown(monkeypatch):
    cp = ChargePoint("station-q", DummyConnection())
    response = await cp._handle_mqtt_action({"action": "does_not_exist"})
    assert response is None


def test_get_args_default_none():
    cp = ChargePoint("station", DummyConnection())
    assert cp.get_args({}) is None


def test_mqtt_client_options_websocket(monkeypatch):
    cp = ChargePoint("station", DummyConnection())
    monkeypatch.setattr(cp_module, "MQTT_TRANSPORT", "websockets")
    monkeypatch.setattr(cp_module, "MQTT_KEEPALIVE", 15)
    monkeypatch.setattr(cp_module, "MQTT_TIMEOUT", 5.0)
    monkeypatch.setattr(cp_module, "MQTT_WEBSOCKET_PATH", "/mqtt")
    monkeypatch.setattr(cp_module, "MQTT_WEBSOCKET_HEADERS", {"Sec-WebSocket-Protocol": "mqtt"})

    options = cp._mqtt_client_options()

    assert options["transport"] == "websockets"
    assert options["keepalive"] == 15
    assert options["timeout"] == 5.0
    assert options["websocket_path"] == "/mqtt"
    assert options["websocket_headers"] == {"Sec-WebSocket-Protocol": "mqtt"}


@pytest.mark.asyncio
async def test_mqtt_publish_with_client():
    cp = ChargePoint("station", DummyConnection())

    class FakeClient:
        def __init__(self):
            self.calls = []

        async def publish(self, topic, payload, retain=False):
            self.calls.append((topic, payload, retain))

    fake_client = FakeClient()
    setattr(cp, "client", fake_client)

    await cp._mqtt_publish("topic", "value")

    assert fake_client.calls == [("topic", "value", True)]


@pytest.mark.asyncio
async def test_push_state_value_mqtt(monkeypatch):
    cp = ChargePoint("station", DummyConnection())
    published = []

    async def fake_publish(self, topic, payload):
        published.append((topic, payload))

    monkeypatch.setattr(cp, "_mqtt_publish", types.MethodType(fake_publish, cp))

    await cp.push_state_value_mqtt("key", "val")

    assert published == [(f"{cp_module.MQTT_BASEPATH}/state/key", "val")]
