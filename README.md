# ocpp2mqtt

ocpp2mqtt is a gateway software that converts OCPP (Open Charge Point Protocol) requests to MQTT (Message Queuing Telemetry Transport) and vice versa. This allows the integration of charging stations with any automation system.

## Features

- Converts OCPP requests to MQTT and vice versa
- Easy integration with automation systems
- Docker support for easy deployment
- Written in Python for flexibility and ease of use

## Prerequisites

This can operate in containerized mode or in normal mode.

- Python 3.8 or higher
- Docker or Kubernetes or any container orchestrater (optional)

## Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/gyzod/ocpp2mqtt.git
    cd ocpp2mqtt
    ```

2. Build 

    ```bash
    pip install -r requirements.txt
    ```
    OR
    
    ```bash
    docker build .
    ```

## Usage

1. Configure your OCPP and MQTT settings in the `.env` file.

2. Start the application:

    ```bash
    docker run
    ```
    or
   
    ```bash
    python central_system.py
    ```

4. The application will start listening for OCPP and MQTT requests and convert them to MQTT or OCPP messages.

## Configuration

Edit or create the `.env` file to set your OCPP and MQTT parameters:

```bash
MQTT_PORT=1883
MQTT_HOSTNAME=xxx.xxx.xxx.xxx
MQTT_BASEPATH='ocpp/chargerX'

LISTEN_PORT=3000
LISTEN_ADDR=0.0.0.0

AUTHORIZED_TAG_ID_LIST='["johnny-car","other-car"]'

```

## MQTT topics and messages

state topics : /ocpp/[your charger]/state is where all the data sent from charge_point to the central_system is sent.

Here is and example of state topics : 

![image](https://github.com/user-attachments/assets/cd1a1360-07e4-46e7-babe-63a899677c3a)


To send message from the central_system to the charge_point, the following command topic must be used : /ocpp/[your charger]/cmd

where the schema for MQTT messages is : 

```
{
    "action": "the operation from the central_system to the charge_point",
    "args" : "the standard operation payload according to OCPP"
}
```



as an exemple, here is a change_availability command to change the charger's availability:

```
{
    "action": "change_availability",
    "args" :
        {
            "connector_id": 1,
            "type": "Operative"
        }
}

```
## Openhab integration

Obviously, as this allows OCPP to be exposed via MQTT, it becomes easy to integrate it into any home automation system. Here is an example of integration with Openhab using the following .thing file:

```
Thing mqtt:topic:ocpp:grizzle "Grizzl-e charger" (mqtt:broker:myUnsecureBroker) [ availabilityTopic="ocpp/charger1/state/heartbeat" ] {
    Channels:
        Type switch : heartbeat                     "heartbeat"                     [ stateTopic = "ocpp/charger1/state/heartbeat" ]
        Type datetime : last_seen                   "last_seen"                     [ stateTopic = "ocpp/charger1/state/last_seen" ]
        Type string : charge_point_vendor           "charge_point_vendor"           [ stateTopic = "ocpp/charger1/state/charge_point_vendor" ]
        Type string : charge_point_model            "charge_point_model"            [ stateTopic = "ocpp/charger1/state/charge_point_model" ]
        Type string : charge_point_serial_number    "charge_point_serial_number"    [ stateTopic = "ocpp/charger1/state/charge_point_serial_number" ]
        Type string : firmware_version              "firmware_version"              [ stateTopic = "ocpp/charger1/state/firmware_version" ]
        Type string : error_code                    "error_code"                    [ stateTopic = "ocpp/charger1/state/error_code" ]
        Type string : status                        "status"                        [ stateTopic = "ocpp/charger1/state/status" ]
        Type string : meter_type                    "meter_type"                    [ stateTopic = "ocpp/charger1/state/meter_type" ]
        Type number : current_import                "current_import"                [ stateTopic = "ocpp/charger1/state/current_import" ]
        Type number : voltage                       "voltage"                       [ stateTopic = "ocpp/charger1/state/voltage" ]
        Type number : power_active_import           "power_active_import"           [ stateTopic = "ocpp/charger1/state/power_active_import" ]
        Type number : energy_active_import_register "energy_active_import_register" [ stateTopic = "ocpp/charger1/state/energy_active_import_register" ]
        Type string : reason                        "reason"                        [ stateTopic = "ocpp/charger1/state/reason" ]

        Type number : meter_start                   "meter_start"                   [ stateTopic = "ocpp/charger1/state/meter_start" ]
        Type datetime : meter_start_timestamp       "meter_start_timestamp"         [ stateTopic = "ocpp/charger1/state/meter_start_timestamp" ]	
        Type number : meter_stop                    "meter_stop"                    [ stateTopic = "ocpp/charger1/state/meter_stop" ]
        Type datetime : meter_stop_timestamp        "meter_stop_timestamp"          [ stateTopic = "ocpp/charger1/state/meter_stop_timestamp" ]
        Type string : meter_stop_reason             "meter_stop_reason"             [ stateTopic = "ocpp/charger1/state/meter_stop_reason" ]
        
        Type number : meter_diff                    "meter_diff"    
        Type number : meter_cost                    "meter_cost"    

        Type string : action                        "action"                         //True command channel
        Type string : cmd                           "cmd"                           [ stateTopic = "ocpp/charger1/cmd" ]
        Type string : cmd_result                    "cmd_result"                    [ stateTopic = "ocpp/charger1/cmd_result/status" ]   
        
}
```

## Notes

Please note that this has only been tested with a Grizzl-e Smart Chargepoint.

For this specific chargepoint to work, I had to change 2 configuration items using the change_configuration mqtt action with the following args :   
- {"action": "change_configuration", "args": {"key": "StartChargingAfterConnect", "value" : "false"}}
- {"action": "change_configuration", "args": {"key": "StopTransactionOnInvalid", "value" : "true"}}


All payload message must follow the OCPP 1.6 protocol documentation : https://groups.oasis-open.org/higherlogic/ws/public/document?document_id=58944

ContributingContributions are welcome! Please fork the repository and submit a pull request.
LicenseThis project is licensed under the MIT License - see the LICENSE file for details.
Acknowledgements- Thanks to the open-source community for their contributions.
- Special thanks to the developers of OCPP and MQTT libraries.
