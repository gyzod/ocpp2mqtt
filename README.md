# ocpp2mqtt

ocpp2mqtt is a gateway software that converts OCPP (Open Charge Point Protocol) requests to MQTT (Message Queuing Telemetry Transport) and vice versa. This allows the integration of charging stations with any automation system.

## Features

- Converts OCPP requests to MQTT and vice versa
- Easy integration with automation systems
- Docker support for easy deployment
- Written in Python for flexibility and ease of use

## Prerequisites

- Docker
- Python 3.8 or higher

## Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/gyzod/ocpp2mqtt.git
    cd ocpp2mqtt
    ```

2. Build and run the Docker container:

    ```bash
    docker build .
    ```

## Usage

1. Configure your OCPP and MQTT settings in the `.env` file.

2. Start the application:

    ```bash
    docker run
    ```

3. The application will start listening for OCPP and MQTT requests and convert them to MQTT or OCPP messages.

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
    "op": "the operation from the central_system to the charge_point",
    "message" : "the standard operation payload according to OCPP"
}
```



as an exemple, here is a change_availability command to change the charger's availability:

```
{
    "op": "change_availability",
    "message" :
        {
            "connector_id": 1,
            "type": "Operative"
        }
}

```

All payload message must follow the OCPP 1.6 protocol documentation : https://groups.oasis-open.org/higherlogic/ws/public/document?document_id=58944

ContributingContributions are welcome! Please fork the repository and submit a pull request.
LicenseThis project is licensed under the MIT License - see the LICENSE file for details.
Acknowledgements- Thanks to the open-source community for their contributions.
- Special thanks to the developers of OCPP and MQTT libraries.
