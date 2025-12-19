#!/bin/bash

# DEVOPS
# Register Azure Resource Providers
# Required before creating Function Apps and other resources

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Setup logging
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/register-resource-providers-$(date +%Y%m%d-%H%M%S).log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "Registering Azure Resource Providers"
log "Log file: $LOG_FILE"

# Check if Azure CLI is available
if ! command -v az &> /dev/null; then
    log "Error: Azure CLI not found"
    exit 1
fi

# Check if logged in
if ! az account show &> /dev/null; then
    log "Error: Not logged in to Azure. Run 'az login' first."
    exit 1
fi

# Required resource providers
PROVIDERS=(
    "Microsoft.Web"           # Function Apps, App Service
    "Microsoft.Storage"      # Storage Accounts
    "Microsoft.CognitiveServices"  # Translator
)

log ""
log "Registering resource providers..."
log "This may take a few minutes..."
log ""

for provider in "${PROVIDERS[@]}"; do
    log "Registering $provider..."
    if az provider register --namespace "$provider" --wait >> "$LOG_FILE" 2>&1; then
        log "$provider registered successfully."
    else
        log "Warning: Failed to register $provider. Check log file: $LOG_FILE"
    fi
    log ""
done

log "Registration complete!"
log ""
log "Note: Registration can take 1-2 minutes to complete."
log "If you still get errors, wait a minute and try again."
log ""
log "Log saved to: $LOG_FILE"
