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
export HA_TOKEN="${SUPERVISOR_TOKEN}"
export HA_URL="http://supervisor/core"
export COOKIE_DIR="/share/willys"

mkdir -p "${COOKIE_DIR}"

echo "[willys] Username: ${WILLYS_USERNAME:0:4}***"
echo "[willys] Sync interval: ${SYNC_INTERVAL}s"
echo "[willys] Startar Python..."
exec python3 /app/willys_sync.py
