import types
from unittest.mock import AsyncMock, patch

import pytest

import charge_point as cp_module
from charge_point import ChargePoint, OCPP_COMMAND_RETRY_ATTEMPTS, OCPP_COMMAND_RETRY_BASE_DELAY
import mqtt_2_charge_point
from ocpp.v16.enums import AuthorizationStatus, RegistrationStatus


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


# =============================================================================
# Tests for on_authorize
# =============================================================================

@pytest.mark.asyncio
async def test_on_authorize_accepted_tag_charging_enabled(monkeypatch, charge_point_with_mqtt):
    """Test authorization succeeds when tag is in list and charging is enabled."""
    monkeypatch.setattr(cp_module, "AUTHORIZED_TAG_ID_LIST", ["valid-tag", "other-tag"])
    charge_point_with_mqtt.charging_enabled = "ON"
    
    result = await charge_point_with_mqtt.on_authorize("valid-tag")
    
    assert result.id_tag_info['status'] == AuthorizationStatus.accepted
    assert charge_point_with_mqtt.authorized_tag_id == "valid-tag"


@pytest.mark.asyncio
async def test_on_authorize_blocked_tag_not_in_list(monkeypatch, charge_point_with_mqtt):
    """Test authorization blocked when tag is not in authorized list."""
    monkeypatch.setattr(cp_module, "AUTHORIZED_TAG_ID_LIST", ["valid-tag"])
    charge_point_with_mqtt.charging_enabled = "ON"
    
    result = await charge_point_with_mqtt.on_authorize("invalid-tag")
    
    assert result.id_tag_info['status'] == AuthorizationStatus.blocked


@pytest.mark.asyncio
async def test_on_authorize_blocked_charging_disabled(monkeypatch, charge_point_with_mqtt):
    """Test authorization blocked when charging is disabled even with valid tag."""
    monkeypatch.setattr(cp_module, "AUTHORIZED_TAG_ID_LIST", ["valid-tag"])
    charge_point_with_mqtt.charging_enabled = "OFF"
    
    result = await charge_point_with_mqtt.on_authorize("valid-tag")
    
    assert result.id_tag_info['status'] == AuthorizationStatus.blocked


@pytest.mark.asyncio
async def test_on_authorize_empty_tag_list(monkeypatch, charge_point_with_mqtt):
    """Test authorization blocked when tag list is empty."""
    monkeypatch.setattr(cp_module, "AUTHORIZED_TAG_ID_LIST", [])
    charge_point_with_mqtt.charging_enabled = "ON"
    
    result = await charge_point_with_mqtt.on_authorize("any-tag")
    
    assert result.id_tag_info['status'] == AuthorizationStatus.blocked


# =============================================================================
# Tests for on_start_transaction
# =============================================================================

@pytest.mark.asyncio
async def test_on_start_transaction_charging_enabled(charge_point_with_mqtt, sample_start_transaction):
    """Test start transaction accepted when charging is enabled."""
    charge_point_with_mqtt.charging_enabled = "ON"
    
    result = await charge_point_with_mqtt.on_start_transaction(**sample_start_transaction)
    
    assert result.id_tag_info['status'] == AuthorizationStatus.accepted
    assert result.transaction_id == charge_point_with_mqtt.transaction_id


@pytest.mark.asyncio
async def test_on_start_transaction_charging_disabled(charge_point_with_mqtt, sample_start_transaction):
    """Test start transaction blocked when charging is disabled."""
    charge_point_with_mqtt.charging_enabled = "OFF"
    
    result = await charge_point_with_mqtt.on_start_transaction(**sample_start_transaction)
    
    assert result.id_tag_info['status'] == AuthorizationStatus.blocked


@pytest.mark.asyncio
async def test_on_start_transaction_publishes_mqtt(charge_point_with_mqtt, sample_start_transaction):
    """Test start transaction publishes meter start values to MQTT."""
    charge_point_with_mqtt.charging_enabled = "ON"
    
    await charge_point_with_mqtt.on_start_transaction(**sample_start_transaction)
    
    # Verify MQTT publish was called
    assert charge_point_with_mqtt.client.publish.call_count >= 2


# =============================================================================
# Tests for on_stop_transaction
# =============================================================================

@pytest.mark.asyncio
async def test_on_stop_transaction(charge_point_with_mqtt, sample_stop_transaction):
    """Test stop transaction returns accepted status."""
    result = await charge_point_with_mqtt.on_stop_transaction(**sample_stop_transaction)
    
    assert result.id_tag_info['status'] == AuthorizationStatus.accepted


@pytest.mark.asyncio
async def test_on_stop_transaction_publishes_mqtt(charge_point_with_mqtt, sample_stop_transaction):
    """Test stop transaction publishes meter stop values to MQTT."""
    await charge_point_with_mqtt.on_stop_transaction(**sample_stop_transaction)
    
    # Verify MQTT publish was called for stop values
    assert charge_point_with_mqtt.client.publish.call_count >= 3


# =============================================================================
# Tests for on_status_notification
# =============================================================================

@pytest.mark.asyncio
async def test_on_status_notification_charging(charge_point_with_mqtt, sample_status_notification):
    """Test status notification when charging - does not reset power."""
    sample_status_notification['status'] = 'Charging'
    
    result = await charge_point_with_mqtt.on_status_notification(**sample_status_notification)
    
    assert charge_point_with_mqtt.status == 'Charging'
    assert result is not None


@pytest.mark.asyncio
async def test_on_status_notification_not_charging_resets_power(charge_point_with_mqtt, sample_status_notification):
    """Test status notification when not charging - resets power to 0."""
    sample_status_notification['status'] = 'Available'
    published_topics = []
    
    async def track_publish(topic, payload, retain=True):
        published_topics.append((topic, payload))
    
    charge_point_with_mqtt.client.publish = track_publish
    
    await charge_point_with_mqtt.on_status_notification(**sample_status_notification)
    
    assert charge_point_with_mqtt.status == 'Available'
    # Check power_active_import was set to 0
    power_publishes = [p for p in published_topics if 'power_active_import' in p[0]]
    assert any(p[1] == 0 for p in power_publishes)


# =============================================================================
# Tests for on_boot_notification
# =============================================================================

@pytest.mark.asyncio
async def test_on_boot_notification(charge_point_with_mqtt, sample_boot_notification):
    """Test boot notification returns accepted status."""
    result = await charge_point_with_mqtt.on_boot_notification(
        charge_point_vendor=sample_boot_notification['charge_point_vendor'],
        charge_point_model=sample_boot_notification['charge_point_model'],
        firmware_version=sample_boot_notification['firmware_version'],
    )
    
    assert result.status == RegistrationStatus.accepted
    assert result.interval == 10


@pytest.mark.asyncio
async def test_on_boot_notification_publishes_vendor_model(charge_point_with_mqtt, sample_boot_notification):
    """Test boot notification publishes vendor and model to MQTT."""
    await charge_point_with_mqtt.on_boot_notification(
        charge_point_vendor=sample_boot_notification['charge_point_vendor'],
        charge_point_model=sample_boot_notification['charge_point_model'],
    )
    
    assert charge_point_with_mqtt.client.publish.call_count >= 2


# =============================================================================
# Tests for on_heartbeat
# =============================================================================

@pytest.mark.asyncio
async def test_on_heartbeat(charge_point_with_mqtt):
    """Test heartbeat returns current time."""
    result = await charge_point_with_mqtt.on_heartbeat()
    
    assert result.current_time is not None
    assert 'T' in result.current_time  # ISO format


@pytest.mark.asyncio
async def test_on_heartbeat_publishes_mqtt(charge_point_with_mqtt):
    """Test heartbeat publishes heartbeat and last_seen to MQTT."""
    await charge_point_with_mqtt.on_heartbeat()
    
    assert charge_point_with_mqtt.client.publish.call_count >= 2


# =============================================================================
# Tests for on_meter_values
# =============================================================================

@pytest.mark.asyncio
async def test_on_meter_values(charge_point_with_mqtt, sample_meter_values):
    """Test meter values updates transaction_id and publishes values."""
    result = await charge_point_with_mqtt.on_meter_values(**sample_meter_values)
    
    assert charge_point_with_mqtt.transaction_id == 123
    assert result is not None


@pytest.mark.asyncio
async def test_on_meter_values_formats_measurand(charge_point_with_mqtt, sample_meter_values):
    """Test meter values formats measurand names correctly."""
    published_topics = []
    
    async def track_publish(topic, payload, retain=True):
        published_topics.append((topic, payload))
    
    charge_point_with_mqtt.client.publish = track_publish
    
    await charge_point_with_mqtt.on_meter_values(**sample_meter_values)
    
    # Check that measurand was formatted (dots replaced with underscores, lowercase)
    topic_names = [t[0] for t in published_topics]
    assert any('energy_active_import_register' in t for t in topic_names)
    assert any('power_active_import' in t for t in topic_names)


# =============================================================================
# Tests for _has_active_websocket
# =============================================================================

def test_has_active_websocket_state_open(charge_point):
    """Test _has_active_websocket returns True when state is OPEN."""
    charge_point._connection.state = 1  # State.OPEN
    
    assert charge_point._has_active_websocket() is True


def test_has_active_websocket_state_closed(mock_websocket_closed):
    """Test _has_active_websocket returns False when state is CLOSED."""
    cp = ChargePoint("test", mock_websocket_closed)
    cp._connection.state = 3  # State.CLOSED
    
    assert cp._has_active_websocket() is False


def test_has_active_websocket_using_open_attr(charge_point):
    """Test _has_active_websocket uses .open attribute if state not available."""
    del charge_point._connection.state
    charge_point._connection.open = True
    
    assert charge_point._has_active_websocket() is True


def test_has_active_websocket_using_closed_attr(charge_point):
    """Test _has_active_websocket uses .closed attribute if others not available."""
    del charge_point._connection.state
    del charge_point._connection.open
    charge_point._connection.closed = False
    
    assert charge_point._has_active_websocket() is True


def test_has_active_websocket_no_connection():
    """Test _has_active_websocket returns False when no connection."""
    cp = ChargePoint("test", None)
    cp._connection = None
    
    assert cp._has_active_websocket() is False


# =============================================================================
# Tests for _wait_for_websocket_connection
# =============================================================================

@pytest.mark.asyncio
async def test_wait_for_websocket_immediate_success(charge_point):
    """Test _wait_for_websocket_connection returns immediately if connected."""
    charge_point._connection.state = 1  # State.OPEN
    
    result = await charge_point._wait_for_websocket_connection("test_action")
    
    assert result is True


@pytest.mark.asyncio
async def test_wait_for_websocket_success_after_retry(charge_point, monkeypatch):
    """Test _wait_for_websocket_connection succeeds after a retry."""
    call_count = 0
    
    def mock_has_active():
        nonlocal call_count
        call_count += 1
        return call_count >= 2  # Succeed on second call
    
    monkeypatch.setattr(charge_point, "_has_active_websocket", mock_has_active)
    monkeypatch.setattr(cp_module, "OCPP_COMMAND_RETRY_BASE_DELAY", 0.01)  # Fast for tests
    
    result = await charge_point._wait_for_websocket_connection("test_action")
    
    assert result is True
    assert call_count == 2


@pytest.mark.asyncio
async def test_wait_for_websocket_failure_after_max_retries(charge_point, monkeypatch):
    """Test _wait_for_websocket_connection fails after max retries."""
    monkeypatch.setattr(charge_point, "_has_active_websocket", lambda: False)
    monkeypatch.setattr(cp_module, "OCPP_COMMAND_RETRY_ATTEMPTS", 3)
    monkeypatch.setattr(cp_module, "OCPP_COMMAND_RETRY_BASE_DELAY", 0.01)
    
    result = await charge_point._wait_for_websocket_connection("test_action")
    
    assert result is False


# =============================================================================
# Tests for utility methods
# =============================================================================

def test_is_charging_enabled_on(charge_point):
    """Test is_charging_enabled returns True when ON."""
    charge_point.charging_enabled = "ON"
    assert charge_point.is_charging_enabled() is True


def test_is_charging_enabled_off(charge_point):
    """Test is_charging_enabled returns False when OFF."""
    charge_point.charging_enabled = "OFF"
    assert charge_point.is_charging_enabled() is False


def test_get_transaction_id(charge_point):
    """Test get_transaction_id returns current transaction_id."""
    charge_point.transaction_id = 42
    assert charge_point.get_transaction_id() == 42


def test_get_mqttpath_without_station_name(monkeypatch, charge_point):
    """Test get_mqttpath returns base path when MQTT_USESTATIONNAME is not set."""
    monkeypatch.setattr(cp_module, "MQTT_USESTATIONNAME", None)
    monkeypatch.setattr(cp_module, "MQTT_BASEPATH", "ocpp/test")
    
    assert charge_point.get_mqttpath() == "ocpp/test"


def test_get_mqttpath_with_station_name(monkeypatch, charge_point):
    """Test get_mqttpath appends station id when MQTT_USESTATIONNAME is true."""
    monkeypatch.setattr(cp_module, "MQTT_USESTATIONNAME", "true")
    monkeypatch.setattr(cp_module, "MQTT_BASEPATH", "ocpp/")
    
    assert charge_point.get_mqttpath() == "ocpp/test-station"


# =============================================================================
# Tests for MQTT publish methods
# =============================================================================

@pytest.mark.asyncio
async def test_mqtt_publish_no_client(charge_point, caplog):
    """Test _mqtt_publish logs warning when no client."""
    charge_point.client = None
    
    await charge_point._mqtt_publish("topic", "payload")
    
    assert "MQTT publish skipped" in caplog.text


@pytest.mark.asyncio
async def test_push_state_values_mqtt(charge_point_with_mqtt):
    """Test push_state_values_mqtt publishes multiple values."""
    await charge_point_with_mqtt.push_state_values_mqtt(key1="val1", key2="val2")
    
    assert charge_point_with_mqtt.client.publish.call_count == 2


@pytest.mark.asyncio
async def test_push_call_return_mqtt(charge_point_with_mqtt):
    """Test push_call_return_mqtt publishes result values."""
    await charge_point_with_mqtt.push_call_return_mqtt({"status": "Accepted", "info": "OK"})
    
    assert charge_point_with_mqtt.client.publish.call_count == 2


@pytest.mark.asyncio
async def test_publish_command_error(charge_point_with_mqtt):
    """Test _publish_command_error publishes error info."""
    msg = {"action": "test_action"}
    error = Exception("Test error")
    
    await charge_point_with_mqtt._publish_command_error(msg, error)
    
    assert charge_point_with_mqtt.client.publish.call_count >= 1
