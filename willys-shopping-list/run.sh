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

# Debug: visa alla env-variabler (maskat)
echo "[willys] --- ENV DEBUG ---"
echo "[willys] Antal env-variabler: $(env | wc -l)"
echo "[willys] Alla variabelnamn:"
env | cut -d= -f1 | sort
echo "[willys] --- ENV DEBUG END ---"

# Testa supervisor-åtkomst
echo "[willys] Testar supervisor..."
curl -s -o /dev/null -w "supervisor /info: HTTP %{http_code}\n" http://supervisor/info 2>&1 | sed 's/^/[willys] /' || echo "[willys] curl mot supervisor misslyckades"

# Prova olika token-namn
if [ -n "$SUPERVISOR_TOKEN" ]; then
    export HA_TOKEN="$SUPERVISOR_TOKEN"
    echo "[willys] Hittade SUPERVISOR_TOKEN"
elif [ -n "$HASSIO_TOKEN" ]; then
    export HA_TOKEN="$HASSIO_TOKEN"
    echo "[willys] Hittade HASSIO_TOKEN"
else
    echo "[willys] WARNING: Ingen HA-token hittad"
fi

export HA_URL="http://supervisor/core"

mkdir -p "${COOKIE_DIR}"

echo "[willys] Username: ${WILLYS_USERNAME:0:4}***"
echo "[willys] Sync interval: ${SYNC_INTERVAL}s"
if [ -n "$HA_TOKEN" ]; then
    echo "[willys] HA_TOKEN: ja"
else
    echo "[willys] HA_TOKEN: nej"
fi
echo "[willys] Startar Python..."
exec python3 /app/willys_sync.py
