#!/bin/bash

# DEVOPS
# Configure Azure Function App Settings from local env file
# Run from infra-one folder

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Setup logging
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/configure-function-app-settings-$(date +%Y%m%d-%H%M%S).log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "Starting Function App settings configuration"
log "Log file: $LOG_FILE"

# Check for required config files
if [ ! -f "resource-names.env" ]; then
    log "Error: resource-names.env not found"
    log "Create it by copying: cp resource-names.env.template resource-names.env"
    log "Then edit resource-names.env with your values"
    exit 1
fi

if [ ! -f "azure.settings.env" ]; then
    log "Error: azure.settings.env not found"
    log "Create it by copying: cp azure.settings.env.template azure.settings.env"
    log "Then edit azure.settings.env with your values"
    exit 1
fi

# Load resource names from env file
source resource-names.env
log "Loaded resource names from resource-names.env"

# Validate required variables
if [ -z "$FUNCTION_APP_NAME" ] || [ -z "$RESOURCE_GROUP" ]; then
    log "Error: Required variables not set in resource-names.env"
    log "Required: FUNCTION_APP_NAME, RESOURCE_GROUP"
    exit 1
fi

SETTINGS_FILE="azure.settings.env"

log "Function App: $FUNCTION_APP_NAME"
log "Resource Group: $RESOURCE_GROUP"
log "Settings file: $SETTINGS_FILE"

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


# Check if Function App exists
if ! az functionapp show --name "$FUNCTION_APP_NAME" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
    log "Error: Function App '$FUNCTION_APP_NAME' not found in resource group '$RESOURCE_GROUP'"
    log "Create it first using: ./deploy-3-deploy-functions.sh"
    exit 1
fi

# Read settings file and build settings array
log "Reading settings from $SETTINGS_FILE..."

SETTINGS_ARRAY=()

while IFS='=' read -r key value || [ -n "$key" ]; do
    # Skip empty lines and comments
    [[ -z "$key" || "$key" =~ ^[[:space:]]*# ]] && continue
    
    # Remove leading/trailing whitespace
    key=$(echo "$key" | xargs)
    value=$(echo "$value" | xargs)
    
    # Skip if key or value is empty
    [[ -z "$key" || -z "$value" ]] && continue
    
    # Add to settings array
    SETTINGS_ARRAY+=("$key=$value")
    log "  Found setting: $key"
done < "$SETTINGS_FILE"

if [ ${#SETTINGS_ARRAY[@]} -eq 0 ]; then
    log "Error: No valid settings found in $SETTINGS_FILE"
    exit 1
fi

log ""
log "Configuring ${#SETTINGS_ARRAY[@]} settings..."

# Configure settings
if az functionapp config appsettings set \
    --name "$FUNCTION_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --settings "${SETTINGS_ARRAY[@]}" >> "$LOG_FILE" 2>&1; then
    log "Settings configured successfully!"
else
    log "Error: Failed to configure settings. Check log file: $LOG_FILE"
    exit 1
fi

log ""
log "Configuration complete!"
log "Log saved to: $LOG_FILE"
