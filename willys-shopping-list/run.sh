#!/bin/bash
set -e

echo "[willys] run.sh startar..."

CONFIG_PATH=/data/options.json

if [ ! -f "$CONFIG_PATH" ]; then
    echo "[willys] FATAL: $CONFIG_PATH saknas"
    exit 1
fi

echo "[willys] Läser konfiguration..."
export WILLYS_USERNAME="$(jq -r '.willys_username' $CONFIG_PATH)"
export WILLYS_PASSWORD="$(jq -r '.willys_password' $CONFIG_PATH)"
export WILLYS_LIST_ID="$(jq -r '.willys_list_id // empty' $CONFIG_PATH)"
export SYNC_INTERVAL="$(jq -r '.sync_interval_seconds // 30' $CONFIG_PATH)"
export LOG_LEVEL="$(jq -r '.log_level // "info"' $CONFIG_PATH)"
export COOKIE_DIR="/share/willys"

# Debug: dump alla token-relaterade env-variabler
echo "[willys] --- ENV DEBUG START ---"
env | grep -iE 'TOKEN|SUPERVISOR|HASSIO|HOME_ASSISTANT' | sed 's/=.\{4\}/=XXXX.../' || true
echo "[willys] --- ENV DEBUG END ---"

# Prova olika token-namn
if [ -n "$SUPERVISOR_TOKEN" ]; then
    export HA_TOKEN="${SUPERVISOR_TOKEN}"
elif [ -n "$HASSIO_TOKEN" ]; then
    export HA_TOKEN="${HASSIO_TOKEN}"
else
    echo "[willys] WARNING: Ingen HA-token hittad"
    echo "[willys] Tips: Avinstallera och installera om add-on:et"
    export HA_TOKEN=""
fi

export HA_URL="http://supervisor/core"

mkdir -p "${COOKIE_DIR}"

echo "[willys] Username: ${WILLYS_USERNAME:0:4}***"
echo "[willys] Sync interval: ${SYNC_INTERVAL}s"
echo "[willys] HA_TOKEN set: $([ -n \"$HA_TOKEN\" ] && echo 'yes' || echo 'no')"
echo "[willys] Startar Python..."
exec python3 /app/willys_sync.py
