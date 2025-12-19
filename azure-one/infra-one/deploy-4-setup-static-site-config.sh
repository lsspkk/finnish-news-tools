#!/bin/bash

# DEVOPS
# Setup Azure configuration for static site deployment
# Run from infra-one folder

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Setup logging
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/setup-static-site-config-$(date +%Y%m%d-%H%M%S).log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "Starting static site configuration setup"
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
if [ -z "$RESOURCE_GROUP" ]; then
    log "Error: Required variables not set in resource-names.env"
    log "Required: RESOURCE_GROUP"
    exit 1
fi

log "Resource Group: $RESOURCE_GROUP"

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

# Change to static-site directory
STATIC_SITE_DIR="$SCRIPT_DIR/../static-site-one"
if [ ! -d "$STATIC_SITE_DIR" ]; then
    log "Error: Static site directory not found: $STATIC_SITE_DIR"
    exit 1
fi

cd "$STATIC_SITE_DIR"
log "Changed to static site directory: $STATIC_SITE_DIR"

# Check if FUNCTION_APP_NAME is set, if not prompt
if [ -z "$FUNCTION_APP_NAME" ]; then
    log "Available Function Apps in resource group '$RESOURCE_GROUP':"
    az functionapp list --resource-group "$RESOURCE_GROUP" --query "[].{Name:name, URL:defaultHostName}" -o table >> "$LOG_FILE" 2>&1
    
    echo ""
    read -p "Enter Function App name: " FUNCTION_APP_NAME
    
    if [ -z "$FUNCTION_APP_NAME" ]; then
        log "Error: Function App name is required"
        exit 1
    fi
else
    log "Using Function App name from resource-names.env: $FUNCTION_APP_NAME"
fi

# Verify Function App exists
if ! az functionapp show --name "$FUNCTION_APP_NAME" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
    log "Error: Function App '$FUNCTION_APP_NAME' not found in resource group '$RESOURCE_GROUP'"
    exit 1
fi

# Get Function App URL
FUNCTION_APP_URL="https://${FUNCTION_APP_NAME}.azurewebsites.net/api"

log "Function App: $FUNCTION_APP_NAME"
log "API Base URL: $FUNCTION_APP_URL"

# Create config.js.azure from template
if [ ! -f "config.js.azure.template" ]; then
    log "Error: config.js.azure.template not found"
    exit 1
fi

log "Creating config.js.azure from template..."
if [ -z "$STORAGE_CONTAINER" ]; then
    log "Warning: STORAGE_CONTAINER not set in resource-names.env, using default"
    STORAGE_CONTAINER="fnt-news-tools"
fi

sed -e "s|PLACEHOLDER_FUNCTION_APP_NAME|$FUNCTION_APP_NAME|g" \
    -e "s|PLACEHOLDER_STORAGE_CONTAINER|$STORAGE_CONTAINER|g" \
    config.js.azure.template > config.js.azure

log "Configuration file created: config.js.azure"
log ""
log "Next steps:"
log "1. Review config.js.azure"
log "2. Deploy using: cd ../infra-one && ./deploy-6-deploy-static-site.sh"
log ""
log "Log saved to: $LOG_FILE"
