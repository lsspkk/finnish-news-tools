#!/bin/bash

# DEVOPS
# Update All (Backend + Frontend) Script
# Deploys updated backend and frontend code to Azure
# Run from infra-one folder

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Setup logging
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/update-all-$(date +%Y%m%d-%H%M%S).log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "Starting full update (backend + frontend)"
log "Log file: $LOG_FILE"

# Update backend
log ""
log "=== Updating Backend ==="
if ! "$SCRIPT_DIR/update-backend.sh" >> "$LOG_FILE" 2>&1; then
    log "Backend update failed. Check log file: $LOG_FILE"
    exit 1
fi

# Update frontend
log ""
log "=== Updating Frontend ==="
if ! "$SCRIPT_DIR/update-frontend.sh" >> "$LOG_FILE" 2>&1; then
    log "Frontend update failed. Check log file: $LOG_FILE"
    exit 1
fi

log ""
log "=== Full Update Complete ==="
log "Both backend and frontend have been updated successfully"
log ""
log "Log saved to: $LOG_FILE"
