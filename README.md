# OCPP2MQTT

OCPP2MQTT is a gateway software that converts OCPP (Open Charge Point Protocol) requests to MQTT (Message Queuing Telemetry Transport) and vice versa. This allows the integration of charging stations with any automation system.

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

3. The application will start listening for OCPP requests and convert them to MQTT messages.

## Configuration

Edit the `.env` file to set your OCPP and MQTT parameters:

```bash
MQTT_PORT=1883
MQTT_HOSTNAME=xxx.xxx.xxx.xxx
MQTT_BASEPATH='ocpp/chargerX'

LISTEN_PORT=3000
LISTEN_ADDR=0.0.0.0

AUTHORIZED_TAG_ID_LIST='["johnny-car","other-car"]'

```

ContributingContributions are welcome! Please fork the repository and submit a pull request.
LicenseThis project is licensed under the MIT License - see the LICENSE file for details.
Acknowledgements- Thanks to the open-source community for their contributions.
- Special thanks to the developers of OCPP and MQTT libraries.
