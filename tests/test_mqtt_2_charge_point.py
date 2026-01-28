"""Tests for mqtt_2_charge_point module - OCPP command functions."""

import pytest
from unittest.mock import AsyncMock, MagicMock

import mqtt_2_charge_point
from ocpp.v16 import call


class MockChargePoint:
    """Mock ChargePoint for testing command functions."""
    
    def __init__(self):
        self.call = AsyncMock()


@pytest.fixture
def mock_cp():
    """Create a mock ChargePoint."""
    return MockChargePoint()


# =============================================================================
# Tests for all OCPP command functions
# =============================================================================

@pytest.mark.asyncio
async def test_cancel_reservation(mock_cp):
    """Test cancel_reservation calls cp.call with correct payload."""
    payload = {"reservation_id": 1}
    
    await mqtt_2_charge_point.cancel_reservation(mock_cp, payload)
    
    mock_cp.call.assert_called_once()
    call_arg = mock_cp.call.call_args[0][0]
    assert isinstance(call_arg, call.CancelReservation)


@pytest.mark.asyncio
async def test_change_availability(mock_cp):
    """Test change_availability calls cp.call with correct payload."""
    payload = {"connector_id": 1, "type": "Operative"}
    
    await mqtt_2_charge_point.change_availability(mock_cp, payload)
    
    mock_cp.call.assert_called_once()
    call_arg = mock_cp.call.call_args[0][0]
    assert isinstance(call_arg, call.ChangeAvailability)


@pytest.mark.asyncio
async def test_change_configuration(mock_cp):
    """Test change_configuration calls cp.call with correct payload."""
    payload = {"key": "HeartbeatInterval", "value": "300"}
    
    await mqtt_2_charge_point.change_configuration(mock_cp, payload)
    
    mock_cp.call.assert_called_once()
    call_arg = mock_cp.call.call_args[0][0]
    assert isinstance(call_arg, call.ChangeConfiguration)


@pytest.mark.asyncio
async def test_clear_cache(mock_cp):
    """Test clear_cache calls cp.call without payload."""
    await mqtt_2_charge_point.clear_cache(mock_cp, None)
    
    mock_cp.call.assert_called_once()
    call_arg = mock_cp.call.call_args[0][0]
    assert isinstance(call_arg, call.ClearCache)


@pytest.mark.asyncio
async def test_clear_charging_profile(mock_cp):
    """Test clear_charging_profile calls cp.call with correct payload."""
    payload = {"id": 1}
    
    await mqtt_2_charge_point.clear_charging_profile(mock_cp, payload)
    
    mock_cp.call.assert_called_once()
    call_arg = mock_cp.call.call_args[0][0]
    assert isinstance(call_arg, call.ClearChargingProfile)


@pytest.mark.asyncio
async def test_data_transfer(mock_cp):
    """Test data_transfer calls cp.call with correct payload."""
    payload = {"vendor_id": "TestVendor", "message_id": "TestMessage"}
    
    await mqtt_2_charge_point.data_transfer(mock_cp, payload)
    
    mock_cp.call.assert_called_once()
    call_arg = mock_cp.call.call_args[0][0]
    assert isinstance(call_arg, call.DataTransfer)


@pytest.mark.asyncio
async def test_get_composite_schedule(mock_cp):
    """Test get_composite_schedule calls cp.call with correct payload."""
    payload = {"connector_id": 1, "duration": 3600}
    
    await mqtt_2_charge_point.get_composite_schedule(mock_cp, payload)
    
    mock_cp.call.assert_called_once()
    call_arg = mock_cp.call.call_args[0][0]
    assert isinstance(call_arg, call.GetCompositeSchedule)


@pytest.mark.asyncio
async def test_get_configuration(mock_cp):
    """Test get_configuration calls cp.call with correct payload."""
    payload = {"key": ["HeartbeatInterval"]}
    
    await mqtt_2_charge_point.get_configuration(mock_cp, payload)
    
    mock_cp.call.assert_called_once()
    call_arg = mock_cp.call.call_args[0][0]
    assert isinstance(call_arg, call.GetConfiguration)


@pytest.mark.asyncio
async def test_get_diagnostics(mock_cp):
    """Test get_diagnostics calls cp.call with correct payload."""
    payload = {"location": "ftp://example.com/diagnostics"}
    
    await mqtt_2_charge_point.get_diagnostics(mock_cp, payload)
    
    mock_cp.call.assert_called_once()
    call_arg = mock_cp.call.call_args[0][0]
    assert isinstance(call_arg, call.GetDiagnostics)


@pytest.mark.asyncio
async def test_get_local_version(mock_cp):
    """Test get_local_version calls cp.call."""
    payload = {}
    
    await mqtt_2_charge_point.get_local_version(mock_cp, payload)
    
    mock_cp.call.assert_called_once()
    call_arg = mock_cp.call.call_args[0][0]
    assert isinstance(call_arg, call.GetLocalListVersion)


@pytest.mark.asyncio
async def test_remote_start_transaction(mock_cp):
    """Test remote_start_transaction calls cp.call with correct payload."""
    payload = {"id_tag": "test-tag", "connector_id": 1}
    
    await mqtt_2_charge_point.remote_start_transaction(mock_cp, payload)
    
    mock_cp.call.assert_called_once()
    call_arg = mock_cp.call.call_args[0][0]
    assert isinstance(call_arg, call.RemoteStartTransaction)


@pytest.mark.asyncio
async def test_remote_stop_transaction(mock_cp):
    """Test remote_stop_transaction calls cp.call with correct payload."""
    payload = {"transaction_id": 1}
    
    await mqtt_2_charge_point.remote_stop_transaction(mock_cp, payload)
    
    mock_cp.call.assert_called_once()
    call_arg = mock_cp.call.call_args[0][0]
    assert isinstance(call_arg, call.RemoteStopTransaction)


@pytest.mark.asyncio
async def test_reserve_now(mock_cp):
    """Test reserve_now calls cp.call with correct payload."""
    payload = {
        "connector_id": 1,
        "expiry_date": "2026-01-28T10:00:00Z",
        "id_tag": "test-tag",
        "reservation_id": 1
    }
    
    await mqtt_2_charge_point.reserve_now(mock_cp, payload)
    
    mock_cp.call.assert_called_once()
    call_arg = mock_cp.call.call_args[0][0]
    assert isinstance(call_arg, call.ReserveNow)


@pytest.mark.asyncio
async def test_reset(mock_cp):
    """Test reset calls cp.call with correct payload."""
    payload = {"type": "Soft"}
    
    await mqtt_2_charge_point.reset(mock_cp, payload)
    
    mock_cp.call.assert_called_once()
    call_arg = mock_cp.call.call_args[0][0]
    assert isinstance(call_arg, call.Reset)


@pytest.mark.asyncio
async def test_send_local_list(mock_cp):
    """Test send_local_list calls cp.call with correct payload."""
    payload = {"list_version": 1, "update_type": "Full"}
    
    await mqtt_2_charge_point.send_local_list(mock_cp, payload)
    
    mock_cp.call.assert_called_once()
    call_arg = mock_cp.call.call_args[0][0]
    assert isinstance(call_arg, call.SendLocalList)


@pytest.mark.asyncio
async def test_set_charging_profile(mock_cp):
    """Test set_charging_profile calls cp.call with correct payload."""
    payload = {
        "connector_id": 1,
        "cs_charging_profiles": {
            "charging_profile_id": 1,
            "stack_level": 0,
            "charging_profile_purpose": "TxDefaultProfile",
            "charging_profile_kind": "Absolute",
            "charging_schedule": {
                "charging_rate_unit": "A",
                "charging_schedule_period": [{"start_period": 0, "limit": 16}]
            }
        }
    }
    
    await mqtt_2_charge_point.set_charging_profile(mock_cp, payload)
    
    mock_cp.call.assert_called_once()
    call_arg = mock_cp.call.call_args[0][0]
    assert isinstance(call_arg, call.SetChargingProfile)


@pytest.mark.asyncio
async def test_trigger_message(mock_cp):
    """Test trigger_message calls cp.call with correct payload."""
    payload = {"requested_message": "BootNotification"}
    
    await mqtt_2_charge_point.trigger_message(mock_cp, payload)
    
    mock_cp.call.assert_called_once()
    call_arg = mock_cp.call.call_args[0][0]
    assert isinstance(call_arg, call.TriggerMessage)


@pytest.mark.asyncio
async def test_unlock_connector(mock_cp):
    """Test unlock_connector calls cp.call with correct payload."""
    payload = {"connector_id": 1}
    
    await mqtt_2_charge_point.unlock_connector(mock_cp, payload)
    
    mock_cp.call.assert_called_once()
    call_arg = mock_cp.call.call_args[0][0]
    assert isinstance(call_arg, call.UnlockConnector)


@pytest.mark.asyncio
async def test_update_firmware(mock_cp):
    """Test update_firmware calls cp.call with correct payload."""
    payload = {"location": "ftp://example.com/firmware.bin", "retrieve_date": "2026-01-28T10:00:00Z"}
    
    await mqtt_2_charge_point.update_firmware(mock_cp, payload)
    
    mock_cp.call.assert_called_once()
    call_arg = mock_cp.call.call_args[0][0]
    assert isinstance(call_arg, call.UpdateFirmware)
