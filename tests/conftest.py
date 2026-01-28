import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_websocket():
    """Mock WebSocket connection with configurable state."""
    ws = MagicMock()
    ws.closed = False
    ws.open = True
    ws.state = 1  # State.OPEN
    return ws


@pytest.fixture
def mock_websocket_closed():
    """Mock WebSocket connection in closed state."""
    ws = MagicMock()
    ws.closed = True
    ws.open = False
    ws.state = 3  # State.CLOSED
    return ws


@pytest.fixture
def mock_mqtt_client():
    """Mock MQTT client for testing publish/subscribe."""
    client = AsyncMock()
    client.publish = AsyncMock()
    client.subscribe = AsyncMock()
    return client


@pytest.fixture
def charge_point(mock_websocket):
    """ChargePoint instance with mocked WebSocket."""
    from charge_point import ChargePoint
    cp = ChargePoint("test-station", mock_websocket)
    return cp


@pytest.fixture
def charge_point_with_mqtt(charge_point, mock_mqtt_client):
    """ChargePoint with both WebSocket and MQTT mocked."""
    charge_point.client = mock_mqtt_client
    return charge_point


@pytest.fixture
def sample_meter_values():
    """Sample meter values payload."""
    return {
        'connector_id': 1,
        'transaction_id': 123,
        'meter_value': [{
            'timestamp': '2026-01-27T10:00:00Z',
            'sampled_value': [
                {'measurand': 'Energy.Active.Import.Register', 'value': '1000'},
                {'measurand': 'Power.Active.Import', 'value': '3500'},
            ]
        }]
    }


@pytest.fixture
def sample_boot_notification():
    """Sample boot notification payload."""
    return {
        'charge_point_vendor': 'TestVendor',
        'charge_point_model': 'TestModel',
        'firmware_version': '1.0.0',
        'charge_point_serial_number': 'SN12345',
    }


@pytest.fixture
def sample_status_notification():
    """Sample status notification payload."""
    return {
        'connector_id': 1,
        'error_code': 'NoError',
        'status': 'Available',
    }


@pytest.fixture
def sample_start_transaction():
    """Sample start transaction payload."""
    return {
        'connector_id': 1,
        'id_tag': 'test-tag',
        'meter_start': 0,
        'timestamp': '2026-01-27T10:00:00Z',
    }


@pytest.fixture
def sample_stop_transaction():
    """Sample stop transaction payload."""
    return {
        'transaction_id': 1,
        'meter_stop': 1000,
        'timestamp': '2026-01-27T11:00:00Z',
        'reason': 'Local',
    }
