#!/bin/bash
# Set Static IP Address Script for Linux
# Uses nmcli (NetworkManager) - works on Ubuntu, Fedora, Arch GNOME/KDE, etc.
# Run with sudo

if [ "$EUID" -ne 0 ]
  then echo "Please run as root (sudo ./set_static_ip_linux.sh)"
  exit
fi

if ! command -v nmcli &> /dev/null
then
    echo "nmcli could not be found. This script requires NetworkManager."
    exit 1
fi

echo "============================================="
echo "   GoGospelNow - Static IP Setup Tool (Linux)"
echo "============================================="
echo ""

# Get list of connections
echo "Available Network Connections:"
mapfile -t CONNS < <(nmcli -g NAME,TYPE,DEVICE connection show --active)

if [ ${#CONNS[@]} -eq 0 ]; then
    echo "No active connections found."
    # Try inactive
    mapfile -t CONNS < <(nmcli -g NAME,TYPE,DEVICE connection show)
fi

i=1
for line in "${CONNS[@]}"; do
    echo "[$i] $line"
    ((i++))
done

echo ""
read -p "Enter number of connection to configure: " CONN_NUM
INDEX=$((CONN_NUM-1))

if [ $INDEX -lt 0 ] || [ $INDEX -ge ${#CONNS[@]} ]; then
    echo "Invalid selection."
    exit 1
fi

# Extract Connection Name (handles spaces)
# Format of nmcli -g line is NAME:TYPE:DEVICE
RAW_LINE="${CONNS[$INDEX]}"
CONN_NAME=$(echo "$RAW_LINE" | cut -d: -f1)

echo "Selected: $CONN_NAME"
echo ""

# Defaults
DEFAULT_IP="192.168.1.100"
DEFAULT_CIDR="24"
DEFAULT_GW="192.168.1.1"
DEFAULT_DNS="8.8.8.8"

read -p "Enter desired IP Address [$DEFAULT_IP]: " IP_ADDR
IP_ADDR=${IP_ADDR:-$DEFAULT_IP}

read -p "Enter CIDR (e.g. 24 for /24) [$DEFAULT_CIDR]: " CIDR
CIDR=${CIDR:-$DEFAULT_CIDR}

read -p "Enter Gateway [$DEFAULT_GW]: " GW
GW=${GW:-$DEFAULT_GW}

read -p "Enter DNS Server [$DEFAULT_DNS]: " DNS
DNS=${DNS:-$DEFAULT_DNS}

echo ""
echo "Summary:"
echo "Connection: $CONN_NAME"
echo "IP: $IP_ADDR/$CIDR"
echo "Gateway: $GW"
echo "DNS: $DNS"
echo ""

read -p "Apply (y/n)? " CONFIRM
if [ "$CONFIRM" != "y" ]; then
    echo "Cancelled."
    exit 0
fi

echo "applying settings..."

# Set IPv4 to manual
nmcli con mod "$CONN_NAME" ipv4.method manual
nmcli con mod "$CONN_NAME" ipv4.addresses "$IP_ADDR/$CIDR"
nmcli con mod "$CONN_NAME" ipv4.gateway "$GW"
nmcli con mod "$CONN_NAME" ipv4.dns "$DNS"

echo "Restarting connection..."
nmcli con down "$CONN_NAME"
nmcli con up "$CONN_NAME"

echo "Done! Current Check:"
ip addr show | grep "$IP_ADDR"
