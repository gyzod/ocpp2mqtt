# Home Assistant Integration

This guide explains how to integrate ocpp2mqtt with Home Assistant using MQTT and automations that mirror the OpenHAB functionality.

## Prerequisites

- Home Assistant 2023.x or newer
- MQTT integration installed and configured
- MQTT Broker configured (same one used by ocpp2mqtt)
- Mail integration (for notifications)

## Installation

### 1. Configure MQTT

Ensure MQTT integration is configured in Home Assistant:

```yaml
mqtt:
  broker: 192.168.1.100
  port: 1883
  username: your-username
  password: your-password
```

### 2. Create MQTT Sensors

Add the following to your `configuration.yaml`:

```yaml
mqtt:
  sensor:
    # Connection Status
    - name: "EV Charger Heartbeat"
      state_topic: "ocpp/charger1/heartbeat"
      payload_on: "true"
      payload_off: "false"
      device_class: connectivity
      
    - name: "EV Charger Last Seen"
      state_topic: "ocpp/charger1/last_seen"
      device_class: timestamp
      
    # Charger Information
    - name: "Charger Vendor"
      state_topic: "ocpp/charger1/charge_point_vendor"
      
    - name: "Charger Model"
      state_topic: "ocpp/charger1/charge_point_model"
      
    - name: "Charger Serial Number"
      state_topic: "ocpp/charger1/charge_point_serial_number"
      
    - name: "Charger Firmware Version"
      state_topic: "ocpp/charger1/firmware_version"
      
    # Status
    - name: "EV Charger Status"
      state_topic: "ocpp/charger1/status"
      icon: mdi:ev-station
      
    - name: "EV Charger Error"
      state_topic: "ocpp/charger1/error_code"
      
    # Metering Data
    - name: "EV Charger Current"
      state_topic: "ocpp/charger1/current_import"
      unit_of_measurement: "A"
      device_class: current
      state_class: measurement
      
    - name: "EV Charger Voltage"
      state_topic: "ocpp/charger1/voltage"
      unit_of_measurement: "V"
      device_class: voltage
      state_class: measurement
      
    - name: "EV Charger Power"
      state_topic: "ocpp/charger1/power_active_import"
      unit_of_measurement: "W"
      device_class: power
      state_class: measurement
      
    - name: "EV Charger Energy"
      state_topic: "ocpp/charger1/energy_active_import_register"
      unit_of_measurement: "kWh"
      device_class: energy
      state_class: total_increasing
      
    # Transaction Data
    - name: "EV Charger Meter Start"
      state_topic: "ocpp/charger1/meter_start"
      unit_of_measurement: "Wh"
      device_class: energy
      
    - name: "EV Charger Meter Stop"
      state_topic: "ocpp/charger1/meter_stop"
      unit_of_measurement: "Wh"
      device_class: energy
      
    - name: "EV Charger Meter Stop Reason"
      state_topic: "ocpp/charger1/meter_stop_reason"
      
    # Calculated Values
    - name: "EV Charger Session Energy"
      state_topic: "ocpp/charger1/meter_diff"
      unit_of_measurement: "Wh"
      device_class: energy
      
    - name: "EV Charger Session Cost"
      state_topic: "ocpp/charger1/meter_cost"
      unit_of_measurement: "USD"
      icon: mdi:currency-usd
      
    - name: "EV Charger Cumulative Cost"
      state_topic: "ocpp/charger1/meter_cost_cumulative"
      unit_of_measurement: "USD"
      device_class: monetary
      icon: mdi:currency-usd
      
    - name: "EV Charger Battery Percentage"
      state_topic: "ocpp/charger1/battery_percentage"
      unit_of_measurement: "%"
      device_class: battery
      state_class: measurement

  switch:
    # Control Switches
    - name: "EV Charger Charging Enabled"
      command_topic: "ocpp/charger1/cmd"
      payload_on: '{"action":"change_availability", "args": {"type": "Operative", "connector_id": 1}}'
      payload_off: '{"action":"change_availability", "args": {"type": "Inoperative", "connector_id": 1}}'
      optimistic: true
      icon: mdi:power-plug
      
    - name: "EV Charger Notifications Enabled"
      state_topic: "ocpp/charger1/notifications_enabled"
      command_topic: "ocpp/charger1/notifications_enabled/set"
      payload_on: "true"
      payload_off: "false"
      icon: mdi:bell
```

### 3. Create Template Sensors

Add calculated values that aren't directly from MQTT:

```yaml
template:
  - sensor:
      # Session energy in kWh
      - name: "EV Charger Session Energy kWh"
        unique_id: ev_charger_session_energy_kwh
        unit_of_measurement: "kWh"
        device_class: energy
        state: >
          {% set wh = states('sensor.ev_charger_session_energy') | float(0) %}
          {{ (wh / 1000) | round(2) }}
        
      # Battery percentage (backup calculation if needed)
      - name: "EV Charger Battery Calculated"
        unique_id: ev_charger_battery_calculated
        unit_of_measurement: "%"
        device_class: battery
        state: >
          {% set energy = states('sensor.ev_charger_energy') | float(0) %}
          {% set maxkwh = 37.3 %}
          {{ ((energy / maxkwh) * 100) | round(1) }}
```

### 4. Create Automations

Create automations that mirror the OpenHAB rules:

#### Automation 1: Master Charging Switch

```yaml
automation:
  - alias: "EV Charger Master Switch"
    description: "Control charger availability based on charging_enabled switch"
    trigger:
      - platform: state
        entity_id: switch.ev_charger_charging_enabled
    condition: []
    action:
      - choose:
          - conditions:
              - condition: state
                entity_id: switch.ev_charger_charging_enabled
                state: "on"
            sequence:
              # Enable charging: set availability to operative
              - service: mqtt.publish
                data:
                  topic: "ocpp/charger1/cmd"
                  payload: '{"action":"change_configuration", "args": {"key": "StartChargingAfterConnect", "value": "true"}}'
              - service: mqtt.publish
                data:
                  topic: "ocpp/charger1/cmd"
                  payload: '{"action":"change_availability", "args": {"type": "Operative", "connector_id": 1}}'
          - conditions:
              - condition: state
                entity_id: switch.ev_charger_charging_enabled
                state: "off"
            sequence:
              # Disable charging: set availability to inoperative
              - service: mqtt.publish
                data:
                  topic: "ocpp/charger1/cmd"
                  payload: '{"action":"change_configuration", "args": {"key": "StartChargingAfterConnect", "value": "false"}}'
              - service: mqtt.publish
                data:
                  topic: "ocpp/charger1/cmd"
                  payload: '{"action":"change_availability", "args": {"type": "Inoperative", "connector_id": 1}}'
```

#### Automation 2: Energy Calculation and Notifications

```yaml
  - alias: "EV Charger Session End Notification"
    description: "Send notification when charging session ends"
    trigger:
      - platform: state
        entity_id: sensor.ev_charger_meter_stop
    condition:
      - condition: state
        entity_id: switch.ev_charger_notifications_enabled
        state: "on"
    action:
      - service: notify.notify
        data:
          title: "⚡ EV Charging Session Complete"
          message: |
            Energy: {{ states('sensor.ev_charger_session_energy_kwh') }} kWh
            Cost: ${{ states('sensor.ev_charger_session_cost') }}
            Battery: {{ states('sensor.ev_charger_battery_percentage') }}%
            Time: {{ now().strftime('%Y-%m-%d %H:%M') }}
```

#### Automation 3: Battery Full Detection

```yaml
  - alias: "EV Charger Battery Full Detection"
    description: "Detect when vehicle battery is fully charged"
    trigger:
      - platform: state
        entity_id: sensor.ev_charger_status
        to: "SuspendedEV"
    action:
      - condition: numeric_state
        entity_id: sensor.ev_charger_session_energy
        above: 1000
      - service: notify.notify
        data:
          title: "🔋 EV Battery Full"
          message: |
            Your vehicle is fully charged!
            
            Energy: {{ states('sensor.ev_charger_session_energy_kwh') }} kWh
            Battery: {{ states('sensor.ev_charger_battery_percentage') }}%
            Cost: ${{ states('sensor.ev_charger_session_cost') }}
            Timestamp: {{ now().strftime('%Y-%m-%d %H:%M:%S') }}
```

#### Automation 4: Off-Peak Charging

```yaml
  - alias: "EV Charger Off-Peak Automatic Charging"
    description: "Automatically enable charging during off-peak hours"
    trigger:
      - platform: time_pattern
        minutes: 0  # Check every hour
    action:
      - choose:
          - conditions:
              - condition: time
                after: "21:00:00"
                before: "07:00:00"
              - condition: state
                entity_id: sensor.ev_charger_heartbeat
                state: "true"
            sequence:
              - service: switch.turn_on
                target:
                  entity_id: switch.ev_charger_charging_enabled
          - conditions:
              - condition: time
                after: "07:00:00"
                before: "21:00:00"
            sequence:
              - service: switch.turn_off
                target:
                  entity_id: switch.ev_charger_charging_enabled
```

#### Automation 5: Charger Actions (Optional Manual Controls)

```yaml
  - alias: "EV Charger Remote Control Actions"
    description: "Send charger commands via MQTT"
    trigger:
      - platform: state
        entity_id: input_select.ev_charger_action
    action:
      - service: mqtt.publish
        data:
          topic: "ocpp/charger1/cmd"
          payload: >
            {% set action = states('input_select.ev_charger_action') %}
            {% if action == "Start" %}
            {"action":"remote_start_transaction"}
            {% elif action == "Stop" %}
            {"action":"remote_stop_transaction"}
            {% elif action == "Unlock" %}
            {"action":"unlock_connector"}
            {% elif action == "Reset Soft" %}
            {"action":"reset", "args": {"type": "soft"}}
            {% elif action == "Reset Hard" %}
            {"action":"reset", "args": {"type": "hard"}}
            {% elif action == "Enable" %}
            {"action":"change_availability", "args": {"type": "Operative", "connector_id": 1}}
            {% elif action == "Disable" %}
            {"action":"change_availability", "args": {"type": "Inoperative", "connector_id": 1}}
            {% endif %}
      - service: input_select.select_option
        target:
          entity_id: input_select.ev_charger_action
        data:
          option: "None"
```

### 5. Create Helper Entities

```yaml
input_select:
  ev_charger_action:
    name: EV Charger Action
    options:
      - "None"
      - "Start"
      - "Stop"
      - "Unlock"
      - "Reset Soft"
      - "Reset Hard"
      - "Enable"
      - "Disable"
    initial: "None"
    icon: mdi:ev-station

input_number:
  kwh_cost:
    name: Cost per kWh
    unit_of_measurement: "USD/kWh"
    min: 0
    max: 1
    step: 0.00001
    mode: box
    icon: mdi:currency-usd
    initial: 0.10342

  max_battery_capacity:
    name: Max Battery Capacity
    unit_of_measurement: "kWh"
    min: 20
    max: 100
    step: 0.1
    mode: box
    icon: mdi:battery
    initial: 37.3
```

## Dashboard Example

Create a dashboard card to display and control the charger:

```yaml
type: vertical-stack
cards:
  - type: horizontal-stack
    cards:
      - type: custom:mini-graph-card
        entity: sensor.ev_charger_power
        name: Power
        
      - type: gauge
        entity: sensor.ev_charger_battery_percentage
        name: Battery
        
  - type: entities
    title: Charger Status
    entities:
      - sensor.ev_charger_status
      - sensor.ev_charger_error
      - entity: sensor.ev_charger_last_seen
        
  - type: entities
    title: Current Session
    entities:
      - sensor.ev_charger_session_energy_kwh
      - sensor.ev_charger_session_cost
      - sensor.ev_charger_current
      - sensor.ev_charger_voltage
      
  - type: entities
    title: Control
    entities:
      - switch.ev_charger_charging_enabled
      - input_select.ev_charger_action
      - switch.ev_charger_notifications_enabled
      
  - type: history-graph
    title: Energy Usage
    entities:
      - sensor.ev_charger_power
```

## Notifications Setup

### Using Default Notify Service

The automations above use `notify.notify`. Configure your preferred service:

```yaml
notify:
  - platform: smtp
    name: notify
    server: smtp.gmail.com
    port: 587
    timeout: 15
    sender: your-email@gmail.com
    sender_name: Home Assistant
    username: your-email@gmail.com
    password: your-app-password
    recipient:
      - your-email@gmail.com
    tls: true
    starttls: true
```

### Alternative: Telegram

```yaml
notify:
  - platform: telegram
    name: notify
    api_key: YOUR_API_KEY
    chat_id: YOUR_CHAT_ID
```

## Comparison with OpenHAB

| Feature | OpenHAB | Home Assistant |
|---------|---------|----------------|
| **Master Switch** | Rule with MQTT publish | Automation with service call |
| **Energy Calculation** | Rule on meter_stop change | Automation on state change |
| **Notifications** | Mail action in rule | Notify service in automation |
| **Battery Percentage** | Real-time rule calculation | Template sensor |
| **Dashboard** | Sitemap with items | Lovelace cards |
| **Cost Tracking** | Item state storage | History stats |

## Configuration Options

### Adjusting Cost Calculation

Update the `input_number.kwh_cost` helper or template sensor:

```yaml
kwh_cost: 0.10342  # Change to your local electricity rate
```

### Battery Capacity

Update the `max_battery_capacity` input or template:

```yaml
maxkwh: 37.3  # Your vehicle's battery capacity in kWh
```

### MQTT Topics

Update the `state_topic` and `command_topic` values if using different topics:

```yaml
state_topic: "your/custom/topic/status"
command_topic: "your/custom/topic/cmd"
```

## Troubleshooting

1. **Sensors not updating**: Check MQTT integration status and verify broker connection
2. **Automations not triggering**: Enable automations in Developer Tools > Automations
3. **Notifications not sending**: Verify notify service configuration
4. **Template sensors showing unknown**: Check syntax in `configuration.yaml`
5. **MQTT payloads failing**: Validate JSON format in automations
6. **Switch shows "unknown" state**: Use `optimistic: true` if ocpp2mqtt doesn't publish state_topic
7. **ChangeAvailability errors**: Ensure `connector_id` parameter is included in args (usually `1`)
8. **Transaction stop errors**: Use `change_availability` to Inoperative instead of `remote_stop_transaction` (which requires transaction_id)

## Advanced Features

### Energy Integration

Home Assistant has a native Energy integration. Link your charger energy sensor:

Settings → Dashboards → Energy → Add Consumption

Select `sensor.ev_charger_energy` as your EV charging sensor.

### History Statistics

Create a history stats sensor for daily energy tracking:

```yaml
template:
  - sensor:
      - name: "EV Charger Daily Energy"
        unique_id: ev_charger_daily_energy
        unit_of_measurement: "kWh"
        state: >
          {% set energy = states('sensor.ev_charger_energy') | float(0) %}
          {{ (energy / 1000) | round(2) }}
```

### Scripts for Manual Control

Create scripts for frequent actions:

```yaml
script:
  start_charging:
    sequence:
      - service: switch.turn_on
        target:
          entity_id: switch.ev_charger_charging_enabled

  stop_charging:
    sequence:
      - service: switch.turn_off
        target:
          entity_id: switch.ev_charger_charging_enabled

  remote_start:
    sequence:
      - service: mqtt.publish
        data:
          topic: "ocpp/charger1/cmd"
          payload: '{"action":"remote_start_transaction"}'

  remote_stop:
    sequence:
      - service: mqtt.publish
        data:
          topic: "ocpp/charger1/cmd"
          payload: '{"action":"remote_stop_transaction"}'
```

## References

- [Home Assistant MQTT Integration](https://www.home-assistant.io/integrations/mqtt/)
- [Home Assistant Automations](https://www.home-assistant.io/getting-started/automation/)
- [Home Assistant Template Sensors](https://www.home-assistant.io/integrations/template/)
- [OCPP2MQTT Project](https://github.com/you/ocpp2mqtt)
