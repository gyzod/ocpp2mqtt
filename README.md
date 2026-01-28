# ocpp2mqtt

[![Version](https://img.shields.io/badge/version-1.0b-blue.svg)](https://github.com/gyzod/ocpp2mqtt/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

**ocpp2mqtt** is a gateway software that converts OCPP (Open Charge Point Protocol) requests to MQTT (Message Queuing Telemetry Transport) and vice versa. This enables seamless integration of EV charging stations with any home automation system.

## ✨ Features

- 🔌 Converts OCPP 1.6 requests to MQTT and vice versa
- 🏠 Easy integration with home automation systems (Home Assistant, OpenHAB, etc.)
- 🐳 Docker and Kubernetes support for flexible deployment
- 📝 Configurable logging with file rotation support
- 🔄 Automatic MQTT reconnection with exponential backoff
- 🔐 MQTT authentication support
- 🌐 WebSocket transport support for MQTT

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [MQTT Topics](#mqtt-topics)
- [Logging](#logging)
- [Integration Guides](#integration-guides)
- [Contributing](#contributing)
- [License](#license)

## 📦 Prerequisites

- Python 3.8 or higher
- MQTT Broker (Mosquitto, HiveMQ, etc.)
- Docker/Kubernetes (optional)

## 🚀 Installation

### Option 1: Python (Direct)

```bash
# Clone the repository
git clone https://github.com/gyzod/ocpp2mqtt.git
cd ocpp2mqtt

# Install dependencies
pip install -r requirements.txt

# Run the application
python central_system.py
```

### Option 2: Docker

```bash
# Build the image
docker build -t ocpp2mqtt .

# Run the container
docker run -d \
  --name ocpp2mqtt \
  -p 3000:3000 \
  -e MQTT_HOSTNAME=your-mqtt-broker \
  -e MQTT_BASEPATH=ocpp/ \
  -e MQTT_USESTATIONNAME=true \
  ocpp2mqtt
```

### Option 3: Docker Compose

```yaml
version: '3.8'
services:
  ocpp2mqtt:
    build: .
    ports:
      - "3000:3000"
    environment:
      - MQTT_HOSTNAME=mqtt-broker
      - MQTT_BASEPATH=ocpp/
      - MQTT_USESTATIONNAME=true
      - AUTHORIZED_TAG_ID_LIST=["tag1","tag2"]
    restart: unless-stopped
```

### Option 4: Kubernetes

See [Kubernetes Deployment Guide](docs/kubernetes/README.md) for detailed instructions.

## ⚙️ Configuration

Create a `.env` file or set environment variables:

### MQTT Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `MQTT_HOSTNAME` | `localhost` | MQTT broker IP address or hostname |
| `MQTT_PORT` | `1883` | MQTT broker port |
| `MQTT_BASEPATH` | `ocpp/test` | Base path for MQTT topics |
| `MQTT_USERNAME` | *(empty)* | MQTT username (if authentication required) |
| `MQTT_PASSWORD` | *(empty)* | MQTT password |
| `MQTT_TRANSPORT` | `tcp` | Transport protocol: `tcp`, `websockets`, or `unix` |
| `MQTT_KEEPALIVE` | `60` | MQTT keepalive interval in seconds |
| `MQTT_TIMEOUT` | `30` | MQTT connection timeout in seconds |
| `MQTT_RECONNECT_BASE_DELAY` | `5` | Initial reconnection delay in seconds |
| `MQTT_RECONNECT_MAX_DELAY` | `60` | Maximum reconnection delay in seconds |
| `MQTT_CLIENT_ID` | *(auto)* | Custom MQTT client ID (auto-generated if not set) |
| `MQTT_USESTATIONNAME` | *(empty)* | Set to `true` to append station name to base path |
| `MQTT_WEBSOCKET_PATH` | *(empty)* | WebSocket path (for WebSocket transport) |
| `MQTT_WEBSOCKET_HEADERS` | *(empty)* | JSON string with WebSocket headers |

### Server Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LISTEN_ADDR` | `0.0.0.0` | Address to bind the OCPP WebSocket server |
| `LISTEN_PORT` | `3000` | Port to listen for OCPP connections |
| `AUTHORIZED_TAG_ID_LIST` | `[]` | JSON array of authorized RFID tags |

### OCPP Command Retry Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OCPP_COMMAND_RETRY_ATTEMPTS` | `5` | Number of retry attempts when WebSocket is temporarily disconnected |
| `OCPP_COMMAND_RETRY_BASE_DELAY` | `0.3` | Base delay in seconds between retries (exponential backoff) |

### Logging Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `LOG_FILE` | *(empty)* | Path to log file (logs only to console if not set) |
| `LOG_MAX_SIZE` | `10485760` | Maximum log file size in bytes (10MB default) |
| `LOG_BACKUP_COUNT` | `5` | Number of backup log files to keep |
| `LOG_FORMAT` | *(default)* | Custom log format string |
| `LOG_DATE_FORMAT` | `%Y-%m-%d %H:%M:%S` | Log date format |

### Example `.env` file

```bash
# MQTT Configuration
MQTT_HOSTNAME=192.168.1.100
MQTT_PORT=1883
MQTT_BASEPATH=ocpp/
MQTT_USESTATIONNAME=true
MQTT_USERNAME=
MQTT_PASSWORD=

# Server Configuration
LISTEN_PORT=3000
LISTEN_ADDR=0.0.0.0
AUTHORIZED_TAG_ID_LIST=["johnny-car","other-car"]

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=/var/log/ocpp2mqtt/app.log
LOG_MAX_SIZE=10485760
LOG_BACKUP_COUNT=5
```

## 🔧 Usage

### Starting the Server

```bash
python central_system.py
```

The server will start listening for OCPP connections on the configured address and port. When a charge point connects, it will automatically bridge communications to MQTT.

### Charge Point Connection

Configure your OCPP charge point to connect to:

```
ws://<server-ip>:<port>/<station-id>
```

Example: `ws://192.168.1.10:3000/charger1`

## 📡 MQTT Topics

### State Topics (Charger → MQTT)

All charger data is published to: `<MQTT_BASEPATH>/<station-id>/state/<parameter>`

| Topic | Description |
|-------|-------------|
| `.../state/heartbeat` | Connection heartbeat |
| `.../state/last_seen` | Last communication timestamp |
| `.../state/status` | Current charger status |
| `.../state/error_code` | Current error code |
| `.../state/charge_point_vendor` | Charger vendor |
| `.../state/charge_point_model` | Charger model |
| `.../state/firmware_version` | Firmware version |
| `.../state/current_import` | Current (Amperes) |
| `.../state/voltage` | Voltage (Volts) |
| `.../state/power_active_import` | Active power (Watts) |
| `.../state/energy_active_import_register` | Total energy (Wh) |
| `.../state/meter_start` | Transaction start meter |
| `.../state/meter_stop` | Transaction stop meter |

### Command Topics (MQTT → Charger)

Send commands to: `<MQTT_BASEPATH>/<station-id>/cmd`

#### Message Schema

```json
{
    "action": "<operation_name>",
    "args": { <ocpp_payload> }
}
```

#### Available Commands

**Change Availability**
```json
{
    "action": "change_availability",
    "args": {
        "connector_id": 1,
        "type": "Operative"
    }
}
```

**Remote Start Transaction**
```json
{
    "action": "remote_start_transaction",
    "args": {
        "connector_id": 1,
        "id_tag": "your-rfid-tag"
    }
}
```

**Remote Stop Transaction**
```json
{
    "action": "remote_stop_transaction",
    "args": {
        "transaction_id": 1
    }
}
```

**Reset**
```json
{
    "action": "reset",
    "args": {
        "type": "Soft"
    }
}
```

**Unlock Connector**
```json
{
    "action": "unlock_connector",
    "args": {
        "connector_id": 1
    }
}
```

### Command Result

Command results are published to: `<MQTT_BASEPATH>/<station-id>/cmd_result/status`

## 📝 Logging

ocpp2mqtt supports flexible logging configuration with both console and file output.

### Console Only (Default)

By default, logs are only output to the console:

```bash
LOG_LEVEL=INFO python central_system.py
```

### File Logging

Enable file logging by setting `LOG_FILE`:

```bash
LOG_FILE=/var/log/ocpp2mqtt/app.log python central_system.py
```

### Log Rotation

When file logging is enabled, logs are automatically rotated:
- Maximum file size: `LOG_MAX_SIZE` (default: 10MB)
- Backup files kept: `LOG_BACKUP_COUNT` (default: 5)

### Docker with File Logging

```bash
docker run -d \
  --name ocpp2mqtt \
  -p 3000:3000 \
  -e MQTT_HOSTNAME=broker \
  -e LOG_FILE=/var/log/ocpp2mqtt/app.log \
  -v /path/to/logs:/var/log/ocpp2mqtt \
  ocpp2mqtt
```

## 📚 Integration Guides

Detailed integration guides are available for popular home automation platforms:

- **[Home Assistant](docs/homeassistant/README.md)** - MQTT sensors, automations, and energy dashboard integration
- **[OpenHAB](docs/openhab/README.md)** - Things, Items, Rules, and Sitemap configuration
- **[Kubernetes](docs/kubernetes/README.md)** - Deployment, ConfigMaps, Secrets, and Ingress setup

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Running Tests

```bash
pytest tests/ -v
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgements

- Thanks to the open-source community for their contributions
- Special thanks to the developers of the [OCPP](https://github.com/mobilityhouse/ocpp) and [aiomqtt](https://github.com/sbtinstruments/aiomqtt) libraries
- Based on initial work from [ocpp-mqtt](https://github.com/rzylius/ocpp-mqtt)
