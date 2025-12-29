#!/bin/bash
# Set Static IP Address Script for macOS
# Run with sudo

if [ "$EUID" -ne 0 ]
  then echo "Please run as root (sudo ./set_static_ip_mac.sh)"
  exit
fi

echo "============================================="
echo "   GoGospelNow - Static IP Setup Tool (Mac)"
echo "============================================="
echo ""

# Get list of network services
echo "Available Network Services:"
networksetup -listallnetworkservices | grep -v "*" | nl -w2 -s") "

echo ""
read -p "Enter number of service to configure (e.g. 1): " SERVICE_NUM

# Get the service name from the number
SERVICE_NAME=$(networksetup -listallnetworkservices | grep -v "*" | sed -n "${SERVICE_NUM}p")

if [ -z "$SERVICE_NAME" ]; then
    echo "Invalid selection."
    exit 1
fi

echo "Selected: $SERVICE_NAME"
echo ""

# Defaults
DEFAULT_IP="192.168.1.100"
DEFAULT_MASK="255.255.255.0"
DEFAULT_ROUTER="192.168.1.1"
DEFAULT_DNS="8.8.8.8"

read -p "Enter desired IP Address [$DEFAULT_IP]: " IP_ADDR
IP_ADDR=${IP_ADDR:-$DEFAULT_IP}

read -p "Enter Subnet Mask [$DEFAULT_MASK]: " SUBNET
SUBNET=${SUBNET:-$DEFAULT_MASK}

read -p "Enter Router (Gateway) [$DEFAULT_ROUTER]: " ROUTER
ROUTER=${ROUTER:-$DEFAULT_ROUTER}

read -p "Enter DNS Server [$DEFAULT_DNS]: " DNS
DNS=${DNS:-$DEFAULT_DNS}

echo ""
echo "Summary:"
echo "Service: $SERVICE_NAME"
echo "IP: $IP_ADDR"
echo "Mask: $SUBNET"
echo "Router: $ROUTER"
echo "DNS: $DNS"
echo ""

read -p "Apply these settings? (y/n) " CONFIRM
if [ "$CONFIRM" != "y" ]; then
    echo "Cancelled."
    exit 0
fi

echo "Setting static IP..."
networksetup -setmanual "$SERVICE_NAME" "$IP_ADDR" "$SUBNET" "$ROUTER"

echo "Setting DNS..."
networksetup -setdnsservers "$SERVICE_NAME" "$DNS"

echo "Done! Verifying configuration:"
networksetup -getinfo "$SERVICE_NAME"
