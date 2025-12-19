#!/bin/bash

# DEVOPS
# Azure Functions Deployment Script
# Run from infra-one folder

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Setup logging
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/deploy-functions-$(date +%Y%m%d-%H%M%S).log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "Starting Azure Functions deployment"
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
if [ -z "$FUNCTION_APP_NAME" ] || [ -z "$RESOURCE_GROUP" ] || [ -z "$LOCATION" ] || [ -z "$STORAGE_ACCOUNT_NAME" ]; then
    log "Error: Required variables not set in resource-names.env"
    log "Required: FUNCTION_APP_NAME, RESOURCE_GROUP, LOCATION, STORAGE_ACCOUNT_NAME"
    exit 1
fi

log "Function App: $FUNCTION_APP_NAME"
log "Resource Group: $RESOURCE_GROUP"
log "Location: $LOCATION"
log "Storage Account: $STORAGE_ACCOUNT_NAME"

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

# Check if func command is available
if ! command -v func &> /dev/null; then
    log "Error: Azure Functions Core Tools not found. Install with: npm install -g azure-functions-core-tools@4"
    exit 1
fi

# Check if function app exists
if ! az functionapp show --name "$FUNCTION_APP_NAME" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
    log "Function app does not exist. Creating..."
    az functionapp create \
        --name "$FUNCTION_APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --consumption-plan-location "$LOCATION" \
        --runtime python \
        --runtime-version 3.11 \
        --functions-version 4 \
        --os-type Linux \
        --storage-account "$STORAGE_ACCOUNT_NAME" >> "$LOG_FILE" 2>&1
    
    log "Function app created. Configure settings before deploying functions."
    log "See DEPLOY.md for required settings."
    exit 0
fi

# Change to functions directory
FUNCTIONS_DIR="$SCRIPT_DIR/../functions"
if [ ! -d "$FUNCTIONS_DIR" ]; then
    log "Error: Functions directory not found: $FUNCTIONS_DIR"
    exit 1
fi

cd "$FUNCTIONS_DIR"
log "Changed to functions directory: $FUNCTIONS_DIR"

# Use production authenticator (month-based password) for deployment
AUTH_FILE="$FUNCTIONS_DIR/authenticate/__init__.py"
AUTH_LOCAL="$FUNCTIONS_DIR/authenticate/__init__.py.local"
AUTH_TEMPLATE="$FUNCTIONS_DIR/authenticate/__init__.py.local.template"
AUTH_BACKUP="$FUNCTIONS_DIR/authenticate/__init__.py.deploy-backup"

# Ensure production authenticator file exists (copy from template if needed)
if [ ! -f "$AUTH_LOCAL" ] && [ -f "$AUTH_TEMPLATE" ]; then
    log "Creating __init__.py.local from template (month-based password)..."
    cp "$AUTH_TEMPLATE" "$AUTH_LOCAL"
    log "Production authenticator file created: $AUTH_LOCAL"
fi

if [ -f "$AUTH_LOCAL" ]; then
    log "Using production authenticator from __init__.py.local (month-based password)..."
    if [ -f "$AUTH_FILE" ]; then
        log "Backing up current authenticate/__init__.py..."
        cp "$AUTH_FILE" "$AUTH_BACKUP"
    fi
    cp "$AUTH_LOCAL" "$AUTH_FILE"
    log "Production authenticator copied for deployment"
elif [ -f "$AUTH_TEMPLATE" ]; then
    log "Using production authenticator from template (month-based password)..."
    if [ -f "$AUTH_FILE" ]; then
        log "Backing up current authenticate/__init__.py..."
        cp "$AUTH_FILE" "$AUTH_BACKUP"
    fi
    cp "$AUTH_TEMPLATE" "$AUTH_FILE"
    log "Production authenticator from template copied for deployment"
else
    log "Warning: Production authenticator not found, using default authenticator"
    log "Template file not found: $AUTH_TEMPLATE"
fi

# Deploy functions
log "Deploying functions..."
log "Using Python runtime..."
if func azure functionapp publish "$FUNCTION_APP_NAME" --python >> "$LOG_FILE" 2>&1; then
    log "Deployment successful!"
    
    # Restore original authenticate file if backup exists
    if [ -f "$AUTH_BACKUP" ]; then
        log "Restoring original authenticate/__init__.py..."
        mv "$AUTH_BACKUP" "$AUTH_FILE"
        log "Original authenticator restored"
    fi
else
    log "Deployment failed. Check log file: $LOG_FILE"
    
    # Restore original authenticate file if backup exists
    if [ -f "$AUTH_BACKUP" ]; then
        log "Restoring original authenticate/__init__.py after failed deployment..."
        mv "$AUTH_BACKUP" "$AUTH_FILE"
        log "Original authenticator restored"
    fi
    
    exit 1
fi

log ""
log "Deployment complete!"
log "Function App URL: https://$FUNCTION_APP_NAME.azurewebsites.net"
log ""
log "Don't forget to configure Azure Function App settings:"
log "  - AzureWebJobsStorage (storage connection string)"
log "  - STORAGE_CONTAINER (fnt-news-tools)"
log "  - AZURE_TRANSLATOR_KEY"
log "  - AUTH_SECRET"
log "  - And other settings from local.settings.json.template"
log ""
log "Log saved to: $LOG_FILE"
