#!/bin/sh

SPLUNK_REST_BASE_URL="https://localhost:8089"
SERVER_GENERAL_ENDPOINT="/servicesNS/nobody/search/configs/conf-server/general"

echo "Enable remote login for Splunk..."
curl --insecure --user admin:changeme $SPLUNK_REST_BASE_URL$SERVER_GENERAL_ENDPOINT --data allowRemoteLogin=always > /dev/null
