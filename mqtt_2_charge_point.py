import logging

from ocpp.v16 import call

# Use logger from logging_config (configured by central_system.py)
logger = logging.getLogger(__name__)

def cancel_reservation(cp, payload):  
    return cp.call(call.CancelReservation(**payload))

def change_availability(cp, payload):
    return cp.call(call.ChangeAvailability(**payload))

def change_configuration(cp, payload):
    return cp.call(call.ChangeConfiguration(**payload))

def clear_cache(cp, payload):
    return cp.call(call.ClearCache())

def clear_charging_profile(cp,payload):
    return cp.call(call.ClearChargingProfile(**payload))

def data_transfer(cp,payload):
    return cp.call(call.DataTransfer(**payload))

def get_composite_schedule(cp,payload):
    return cp.call(call.GetCompositeSchedule(**payload))

def get_configuration(cp, payload):
    return cp.call(call.GetConfiguration(**payload))

def get_diagnostics(cp, payload):
    return cp.call(call.GetDiagnostics(**payload))

def get_local_version(cp, payload):
    return cp.call(call.GetLocalListVersion(**payload))

def remote_start_transaction(cp, payload):
    return cp.call(call.RemoteStartTransaction(**payload))

def remote_stop_transaction(cp, payload):
    return cp.call(call.RemoteStopTransaction(**payload))

def reserve_now(cp, payload):
    return cp.call(call.ReserveNow(**payload))

def reset(cp, payload):
    return cp.call(call.Reset(**payload))

def send_local_list(cp, payload):
    return cp.call(call.SendLocalList(**payload))

def set_charging_profile(cp,payload):
    return cp.call(call.SetChargingProfile(**payload))

def trigger_message(cp,payload):
    return cp.call(call.TriggerMessage(**payload))

def unlock_connector(cp, payload):
    return cp.call(call.UnlockConnector(**payload))

def update_firmware(cp, payload):
    return cp.call(call.UpdateFirmware(**payload))


    