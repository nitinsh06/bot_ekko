#!/bin/bash

# Wait for NetworkManager to attempt connections
sleep 20

# Check for internet connectivity
if ! ping -c1 -W5 8.8.8.8 &>/dev/null; then
    echo "$(date): No internet — launching Ekko setup portal"
    wifi-connect --portal-ssid "Ekko-WiFi-Setup" --portal-passphrase "ekko1234" --ui-directory /usr/local/share/wifi-connect/ui
else
    echo "$(date): Network OK, skipping setup portal"
fi