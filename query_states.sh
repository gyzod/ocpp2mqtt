#!/bin/bash

# Script to query MQTT states and Home Assistant states for the Grizzl-E charger

if [ -f .env ]; then
    set -a
    source .env
    set +a  
else
    echo "Error : file .env not found"
    exit 1
fi

mosquitto_sub -v -h $MQTT_HOSTNAME -t "$MQTT_BASEPATH/#" -W 1 -C 1
curl -s -H "Authorization: Bearer $HA_TOKEN" $HA_URL/api/states | jq '.[] | select(.entity_id | contains("grizzl_e_charger")) | {id: .entity_id, etat: .state, attrs: .attributes}'