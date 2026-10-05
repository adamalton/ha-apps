#!/usr/bin/with-contenv bashio
# ==============================================================================
# Start Powersmarts
# ==============================================================================

declare log_level
log_level="$(bashio::config 'log_level')"

export POWERSMARTS_LOG_LEVEL="${log_level:-info}"
export POWERSMARTS_HA_URL="http://supervisor/core/api"
export POWERSMARTS_DATA_FILE="/data/powersmarts.json"
export POWERSMARTS_HOST="0.0.0.0"
export POWERSMARTS_PORT="8099"
export POWERSMARTS_INGRESS_ONLY="1"

bashio::log.info "Starting Powersmarts"

exec python3 -m powersmarts
