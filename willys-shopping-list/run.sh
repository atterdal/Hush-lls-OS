#!/usr/bin/with-contenv bashio

CONFIG_PATH=/data/options.json

export WILLYS_USERNAME="$(bashio::config 'willys_username')"
export WILLYS_PASSWORD="$(bashio::config 'willys_password')"
export WILLYS_LIST_ID="$(bashio::config 'willys_list_id')"
export SYNC_INTERVAL="$(bashio::config 'sync_interval_seconds')"
export LOG_LEVEL="$(bashio::config 'log_level')"
export HA_TOKEN="${SUPERVISOR_TOKEN}"
export HA_URL="http://supervisor/core"
export COOKIE_DIR="/share/willys"

mkdir -p "${COOKIE_DIR}"

bashio::log.info "Starting Willys Shopping List Sync..."
exec python3 /app/willys_sync.py
