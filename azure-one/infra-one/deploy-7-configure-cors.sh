#!/bin/bash

# DEVOPS
# Configure CORS on Function App to allow Static Web App
# Run from infra-one folder

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Setup logging
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/configure-cors-$(date +%Y%m%d-%H%M%S).log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "Starting CORS configuration"
log "Log file: $LOG_FILE"

# Check for required config file
if [ ! -f "resource-names.env" ]; then
    log "Error: resource-names.env not found"
    log "Create it by copying: cp resource-names.env.template resource-names.env"
    log "Then edit resource-names.env with your values"
    exit 1
fi

# Load resource names from env file
source resource-names.env
log "Loaded resource names from resource-names.env"

# Validate required variables
if [ -z "$FUNCTION_APP_NAME" ] || [ -z "$RESOURCE_GROUP" ] || [ -z "$STATIC_WEB_APP_NAME" ]; then
    log "Error: Required variables not set in resource-names.env"
    log "Required: FUNCTION_APP_NAME, RESOURCE_GROUP, STATIC_WEB_APP_NAME"
    exit 1
fi

log "Function App: $FUNCTION_APP_NAME"
log "Resource Group: $RESOURCE_GROUP"
log "Static Web App: $STATIC_WEB_APP_NAME"

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

# Get Static Web App URL
log "Getting Static Web App URL..."
STATIC_WEB_APP_URL=$(az staticwebapp show \
    --name "$STATIC_WEB_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "defaultHostname" -o tsv 2>> "$LOG_FILE")

if [ -z "$STATIC_WEB_APP_URL" ]; then
    log "Error: Failed to get Static Web App URL"
    log "Make sure Static Web App exists: $STATIC_WEB_APP_NAME"
    exit 1
fi

STATIC_WEB_APP_FULL_URL="https://$STATIC_WEB_APP_URL"
log "Static Web App URL: $STATIC_WEB_APP_FULL_URL"

# Check if CORS origin already exists
log "Checking existing CORS configuration..."
EXISTING_CORS=$(az functionapp cors show \
    --name "$FUNCTION_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "allowedOrigins" -o tsv 2>> "$LOG_FILE" || echo "")

if echo "$EXISTING_CORS" | grep -q "$STATIC_WEB_APP_FULL_URL"; then
    log "CORS origin already configured: $STATIC_WEB_APP_FULL_URL"
    log "No changes needed"
else
    log "Adding CORS origin: $STATIC_WEB_APP_FULL_URL"
    az functionapp cors add \
        --name "$FUNCTION_APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --allowed-origins "$STATIC_WEB_APP_FULL_URL" >> "$LOG_FILE" 2>&1
    
    if [ $? -eq 0 ]; then
        log "CORS configuration successful!"
    else
        log "Error: Failed to configure CORS"
        log "Check log file for details: $LOG_FILE"
        exit 1
    fi
fi

# Show current CORS configuration
log ""
log "Current CORS allowed origins:"
az functionapp cors show \
    --name "$FUNCTION_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "allowedOrigins" -o table >> "$LOG_FILE" 2>&1

log ""
log "CORS configuration complete!"
log "Static Web App can now call Function App APIs"
log ""
log "Log saved to: $LOG_FILE"
