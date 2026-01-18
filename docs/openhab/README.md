# OpenHAB Integration

This guide explains how to integrate ocpp2mqtt with OpenHAB using the provided Thing and Rules files.

## Prerequisites

- OpenHAB 3.x or 4.x
- MQTT Binding installed
- MQTT Broker configured in OpenHAB
- Mail add-on (optional, for notifications)

## Installation

### 1. MQTT Broker Configuration

First, ensure you have an MQTT broker configured. In OpenHAB, create a broker Thing:

```java
Bridge mqtt:broker:myUnsecureBroker "MQTT Broker" [
    host="192.168.1.100",
    port=1883,
    secure=false,
    username="your-username",
    password="your-password"
]
```

### 2. Import the Things File

Copy the provided [ocpp.things](ocpp.things) file to your OpenHAB things directory:

```bash
cp ocpp.things /etc/openhab/things/
```

Or add its contents to your existing things file. The file defines a Thing for the Grizzl-e charger with all necessary channels for state and control.

### 3. Create Items

Create a new items file (e.g., `ocpp.items`) with the items linked to the Thing channels:

```java
// Connection Status
Switch      Grizzle_charger_heartbeat               "Heartbeat"                 {channel="mqtt:topic:ocpp:grizzle:heartbeat"}
DateTime    Grizzle_charger_last_seen               "Last Seen [%1$tY-%1$tm-%1$td %1$tH:%1$tM]"  {channel="mqtt:topic:ocpp:grizzle:last_seen"}

// Charger Information
String      Grizzle_charger_vendor                  "Vendor [%s]"               {channel="mqtt:topic:ocpp:grizzle:charge_point_vendor"}
String      Grizzle_charger_model                   "Model [%s]"                {channel="mqtt:topic:ocpp:grizzle:charge_point_model"}
String      Grizzle_charger_serial                  "Serial [%s]"               {channel="mqtt:topic:ocpp:grizzle:charge_point_serial_number"}
String      Grizzle_charger_firmware                "Firmware [%s]"             {channel="mqtt:topic:ocpp:grizzle:firmware_version"}

// Status
String      Grizzle_charger_status                  "Status [%s]"               {channel="mqtt:topic:ocpp:grizzle:status"}
String      Grizzle_charger_error                   "Error [%s]"                {channel="mqtt:topic:ocpp:grizzle:error_code"}

// Metering
Number:ElectricCurrent  Grizzle_charger_current     "Current [%.1f A]"          {channel="mqtt:topic:ocpp:grizzle:current_import"}
Number:ElectricPotential Grizzle_charger_voltage    "Voltage [%.0f V]"          {channel="mqtt:topic:ocpp:grizzle:voltage"}
Number:Power            Grizzle_charger_power       "Power [%.0f W]"            {channel="mqtt:topic:ocpp:grizzle:power_active_import"}
Number:Energy           Grizzle_charger_energy      "Energy [%.2f kWh]"         {channel="mqtt:topic:ocpp:grizzle:energy_active_import_register"}

// Transaction Data
Number:Energy           Grizzle_charger_meter_start "Meter Start [%.0f Wh]"     {channel="mqtt:topic:ocpp:grizzle:meter_start"}
DateTime                Grizzle_charger_meter_start_timestamp "Charge Started [%1$tY-%1$tm-%1$td %1$tH:%1$tM]"  {channel="mqtt:topic:ocpp:grizzle:meter_start_timestamp"}
Number:Energy           Grizzle_charger_meter_stop  "Meter Stop [%.0f Wh]"      {channel="mqtt:topic:ocpp:grizzle:meter_stop"}
DateTime                Grizzle_charger_meter_stop_timestamp  "Charge Stopped [%1$tY-%1$tm-%1$td %1$tH:%1$tM]"  {channel="mqtt:topic:ocpp:grizzle:meter_stop_timestamp"}
String                  Grizzle_charger_meter_stop_reason "Stop Reason [%s]"    {channel="mqtt:topic:ocpp:grizzle:meter_stop_reason"}

// Calculated Values
Number:Energy           Grizzle_charger_meter_diff              "Session Energy [%.2f kWh]"
Number                  Grizzle_charger_meter_cost              "Session Cost [%.2f $]"
Number                  Grizzle_charger_meter_cost_cumulative   "Cumulative Cost [%.2f $]"
Number                  Grizzle_charger_energy_active_import_register_percentage "Battery % [%.1f %]"

// Commands
String      Grizzle_charger_action                  "Action"                    {channel="mqtt:topic:ocpp:grizzle:action"}
String      Grizzle_charger_cmd                     "Command"                   {channel="mqtt:topic:ocpp:grizzle:cmd"}
String      Grizzle_charger_cmd_result              "Command Result [%s]"       {channel="mqtt:topic:ocpp:grizzle:cmd_result"}

// Control Switches
Switch      Grizzle_charger_charging_enabled        "Charging Enabled"          {channel="mqtt:topic:ocpp:grizzle:charging_enabled"}
Switch      Grizzle_charger_charge_completed        "Charge Completed"
Switch      Grizzle_charger_notifications_enabled   "Notifications Enabled"     {channel="mqtt:topic:ocpp:grizzle:notifications_enabled"}
```

### 4. Import the Rules File

Copy the provided [ocpp.rules](ocpp.rules) file to your OpenHAB rules directory:

```bash
cp ocpp.rules /etc/openhab/rules/
```

Or import it in the Web UI. The rules handle:

- **Master charging switch**: Enable/disable charging via `Grizzle_charger_charging_enabled`
- **Charger actions**: Remote start/stop, reset, availability changes
- **Energy calculation**: Automatic calculation of energy consumed and cost
- **Notifications**: Email notifications when charging completes
- **Battery percentage**: Calculation based on max battery capacity

### 5. Mail Configuration (Optional)

If you want email notifications, configure the Mail action in OpenHAB:

1. Install the Mail add-on
2. Configure your SMTP server
3. Update the mail action IDs in the rules file

The default notification is sent when a charging session ends, including:
- Energy consumed (kWh)
- Battery percentage
- Total cost
- Timestamp

## Configuration

### Adjust for Your Charger

Edit the rules file to match your setup:

- **MQTT Broker ID**: Update `mqtt:broker:myUnsecureBroker` to match your broker
- **MQTT Topic**: Change `ocpp/charger1` to your topic path
- **Cost per kWh**: Update `kwh_cost = 0.10342` to your local rate
- **Max Battery Capacity**: Update `val maxkwh = 37.3` to your vehicle's capacity
- **Email Address**: Update to your email address
- **ID Tag**: Update `idTag = "uc_default_auth"` to your RFID tag

### Charger Actions

The `Grizzle_charger_action` item supports these commands (case-sensitive):

| Action | Description |
|--------|-------------|
| `remote_start_transaction` | Start charging |
| `remote_stop_transaction` | Stop charging |
| `unlock_connector` | Unlock the charging connector |
| `reset_soft` | Soft reset the charger |
| `reset_hard` | Hard reset the charger |
| `availability_operative` | Enable the charger |
| `availability_inoperative` | Disable the charger |
| `set_charging_profile` | Set charging profile (current limit) |

### Charging Schedule Control

Use the `Grizzle_charger_charging_enabled` switch to control when charging is allowed:

- **ON**: Enables charging
  - Sets charger availability to "Operative"
  - Enables "StartChargingAfterConnect" configuration
  - Allows automatic charging when car is connected

- **OFF**: Disables charging
  - Sets charger availability to "Inoperative"
  - Disables "StartChargingAfterConnect"
  - Stops any active charging

## Rules Explained

### Rule 1: Master Charging Switch
**Triggered**: When `Grizzle_charger_charging_enabled` changes

- **ON**: Enables charging, sets charger operational, activates auto-start
- **OFF**: Disables charging, sets charger non-operational, stops active session

```java
rule "changer logical masterswitch"
when
    Item Grizzle_charger_charging_enabled changed
then
    // Sends MQTT commands to configure charger behavior
end
```

### Rule 2: Charger Actions
**Triggered**: When `Grizzle_charger_action` changes

Sends MQTT commands for:
- Transaction control (start/stop)
- Connector management (unlock)
- Charger state (reset, availability)
- Charging profiles (current limits)

Supports actions like:
- `remote_start_transaction`
- `remote_stop_transaction`
- `unlock_connector`
- `reset_soft` / `reset_hard`
- `availability_operative` / `availability_inoperative`
- `set_charging_profile`

### Rule 3: Energy Calculation
**Triggered**: When `Grizzle_charger_meter_stop` changes

- Calculates total energy consumed (Wh)
- Calculates session cost based on configured rate
- Updates cumulative cost
- Sends email notification if enabled

```java
rule "calculate meter diff.  Ca donne le wh de la dernière transaction."
when
    Item Grizzle_charger_meter_stop changed
then
    val diff = (meter_stop - meter_start)
    postUpdate(Grizzle_charger_meter_diff, diff)
    val cost = diff / 1000 * kwh_cost
    postUpdate(Grizzle_charger_meter_cost, cost)
end
```

### Rule 4: Battery Full Detection
**Triggered**: When status changes to `SuspendedEV`

- Detects when car is fully charged
- Sends email notification with charging statistics
- Updates `charge_completed` switch

Includes in notification:
- Energy imported (kWh)
- Battery percentage
- Timestamp

### Rule 5: Battery Percentage
**Triggered**: When `Grizzle_charger_energy_active_import_register` changes

- Calculates current battery percentage
- Updates `Grizzle_charger_energy_active_import_register_percentage` item

## Dashboard Example

Create a sitemap to visualize and control the charger:

```perl
sitemap ocpp label="EV Charger Dashboard" {
    Frame label="Charger Status" {
        Text item=Grizzle_charger_status
        Text item=Grizzle_charger_error
        Text item=Grizzle_charger_heartbeat
        Text item=Grizzle_charger_last_seen
    }
    
    Frame label="Current Session" {
        Text item=Grizzle_charger_power
        Text item=Grizzle_charger_current
        Text item=Grizzle_charger_voltage
        Text item=Grizzle_charger_energy
        Text item=Grizzle_charger_energy_active_import_register_percentage
    }
    
    Frame label="Charging Control" {
        Switch item=Grizzle_charger_charging_enabled
        Selection item=Grizzle_charger_action mappings={
            "remote_start_transaction"="Start",
            "remote_stop_transaction"="Stop",
            "unlock_connector"="Unlock",
            "reset_soft"="Soft Reset",
            "reset_hard"="Hard Reset",
            "availability_operative"="Enable",
            "availability_inoperative"="Disable"
        }
    }
    
    Frame label="Cost & Energy" {
        Text item=Grizzle_charger_meter_diff
        Text item=Grizzle_charger_meter_cost
        Text item=Grizzle_charger_meter_cost_cumulative
    }
    
    Frame label="Charger Info" {
        Text item=Grizzle_charger_vendor
        Text item=Grizzle_charger_model
        Text item=Grizzle_charger_firmware
    }
    
    Frame label="Notifications" {
        Switch item=Grizzle_charger_notifications_enabled
    }
}
```

## Troubleshooting

1. **Rules not triggering**: Check that items are receiving values from MQTT. View logs with:
   ```
   log:tail org.openhab.core.automation.module.script.rulesupport
   ```

2. **MQTT connection issues**: Verify broker credentials and connection in:
   ```
   log:tail org.openhab.binding.mqtt
   ```

3. **Notifications not sent**: Ensure Mail action is installed and properly configured

4. **Values not updating**: Check MQTT topic paths match your configuration

5. **Email format issues**: Customize the date format by modifying:
   ```
   val dateFormat = "%1$tH:%1$tM %1$tY-%1$tm-%1$td"
   ```

## Advanced: Automations

Create automations for:

- **Time-based charging**: Enable/disable based on off-peak hours
- **Grid load management**: Adjust charging based on home consumption
- **Cost optimization**: Charge only when electricity is cheapest
- **Home integration**: Start charging when car arrives home

Example automation for off-peak charging:

```java
rule "Off-peak charging"
when
    Item Grizzle_charger_heartbeat changed to ON
then
    val hour = now.getHourOfDay()
    if (hour >= 21 || hour < 7) {
        // Off-peak hours: 21:00 - 07:00
        Grizzle_charger_charging_enabled.sendCommand(ON)
    } else {
        Grizzle_charger_charging_enabled.sendCommand(OFF)
    }
end
```

## Files Reference

- **[ocpp.things](ocpp.things)** - Thing definition with all MQTT channels
- **[ocpp.rules](ocpp.rules)** - Complete rule logic with real-world examples
