#!/bin/bash

# DEVOPS
# Azure Static Web App Deployment and CORS Configuration Script
# Run from infra-one folder
# This script deploys the static site and configures CORS automatically

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Setup logging
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/deploy-static-site-$(date +%Y%m%d-%H%M%S).log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "Starting Azure Static Web App deployment and CORS configuration"
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
if [ -z "$STATIC_WEB_APP_NAME" ] || [ -z "$RESOURCE_GROUP" ] || [ -z "$LOCATION" ] || [ -z "$FUNCTION_APP_NAME" ]; then
    log "Error: Required variables not set in resource-names.env"
    log "Required: STATIC_WEB_APP_NAME, RESOURCE_GROUP, LOCATION, FUNCTION_APP_NAME"
    exit 1
fi

log "Static Web App: $STATIC_WEB_APP_NAME"
log "Resource Group: $RESOURCE_GROUP"
log "Location: $LOCATION"
log "Function App: $FUNCTION_APP_NAME"

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

# Check if Static Web Apps CLI is available BEFORE creating resources
if ! command -v swa &> /dev/null; then
    log "Error: Static Web Apps CLI (swa) not found"
    log "Install it with: npm install -g @azure/static-web-apps-cli"
    log "Then run this script again"
    exit 1
fi

log "Static Web Apps CLI found: $(swa --version)"

# Change to static-site directory
STATIC_SITE_DIR="$SCRIPT_DIR/../static-site-one"
if [ ! -d "$STATIC_SITE_DIR" ]; then
    log "Error: Static site directory not found: $STATIC_SITE_DIR"
    exit 1
fi

cd "$STATIC_SITE_DIR"
log "Changed to static site directory: $STATIC_SITE_DIR"

# Check if config.js.azure exists
if [ ! -f "config.js.azure" ]; then
    log "Error: config.js.azure not found in static-site-one folder"
    log "Create it by running: ./deploy-4-setup-static-site-config.sh"
    exit 1
fi

# Backup existing config.js if it exists
if [ -f "config.js" ]; then
    log "Backing up existing config.js to config.js.local"
    cp config.js config.js.local
fi

# Copy Azure config to config.js for deployment
log "Copying config.js.azure to config.js for deployment..."
cp config.js.azure config.js
log "Configuration file prepared for deployment"

# Check if Static Web App exists
if ! az staticwebapp show --name "$STATIC_WEB_APP_NAME" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
    log "Static Web App does not exist. Creating..."
    log "Creating Static Web App without repository connection..."
    az staticwebapp create \
        --name "$STATIC_WEB_APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --location "$LOCATION" \
        --sku Free >> "$LOG_FILE" 2>&1
    
    if [ $? -ne 0 ]; then
        log "Error: Failed to create Static Web App"
        log "Check log file for details: $LOG_FILE"
        # Restore config.js if creation failed
        if [ -f "config.js.local" ]; then
            mv config.js.local config.js
        fi
        exit 1
    fi
    
    log "Static Web App created."
else
    log "Static Web App already exists."
fi

# Get deployment token
log "Getting deployment token..."
DEPLOYMENT_TOKEN=$(az staticwebapp secrets list \
    --name "$STATIC_WEB_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.apiKey" -o tsv 2>> "$LOG_FILE")

if [ -z "$DEPLOYMENT_TOKEN" ]; then
    log "Error: Failed to get deployment token"
    log "Check log file for details: $LOG_FILE"
    # Restore config.js if token retrieval failed
    if [ -f "config.js.local" ]; then
        mv config.js.local config.js
    fi
    exit 1
fi

log "Deployment token retrieved. Deploying files..."

# Change back to infra-one directory to avoid "current directory" error
cd "$SCRIPT_DIR"
log "Changed to infra-one directory for deployment"

# Deploy using Static Web Apps CLI from parent directory
# Use --app-location and --output-location to specify the static site folder
STATIC_SITE_RELATIVE_PATH="../static-site-one"
if swa deploy \
    --app-location "$STATIC_SITE_RELATIVE_PATH" \
    --output-location "$STATIC_SITE_RELATIVE_PATH" \
    --deployment-token "$DEPLOYMENT_TOKEN" \
    --env production >> "$LOG_FILE" 2>&1; then
    log "Deployment successful!"
else
    log "Error: Deployment failed"
    log "Check log file for details: $LOG_FILE"
    # Restore config.js if deployment failed
    cd "$STATIC_SITE_DIR"
    if [ -f "config.js.local" ]; then
        log "Restoring config.js from backup..."
        mv config.js.local config.js
    fi
    exit 1
fi

# Change back to static site directory for config restore
cd "$STATIC_SITE_DIR"

# Restore local config.js if backup exists
if [ -f "config.js.local" ]; then
    log "Restoring local config.js..."
    mv config.js.local config.js
    log "Local configuration restored"
fi

# Get Static Web App URL
log "Getting Static Web App URL..."
STATIC_WEB_APP_URL=$(az staticwebapp show \
    --name "$STATIC_WEB_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "defaultHostname" -o tsv 2>> "$LOG_FILE")

if [ -z "$STATIC_WEB_APP_URL" ]; then
    log "Warning: Failed to get Static Web App URL"
    log "CORS configuration will be skipped"
else
    STATIC_WEB_APP_FULL_URL="https://$STATIC_WEB_APP_URL"
    log "Static Web App URL: $STATIC_WEB_APP_FULL_URL"
    
    # Configure CORS
    log ""
    log "Configuring CORS on Function App..."
    cd "$SCRIPT_DIR"
    
    EXISTING_CORS=$(az functionapp cors show \
        --name "$FUNCTION_APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --query "allowedOrigins" -o tsv 2>> "$LOG_FILE" || echo "")
    
    if echo "$EXISTING_CORS" | grep -q "$STATIC_WEB_APP_FULL_URL"; then
        log "CORS origin already configured: $STATIC_WEB_APP_FULL_URL"
    else
        log "Adding CORS origin: $STATIC_WEB_APP_FULL_URL"
        if az functionapp cors add \
            --name "$FUNCTION_APP_NAME" \
            --resource-group "$RESOURCE_GROUP" \
            --allowed-origins "$STATIC_WEB_APP_FULL_URL" >> "$LOG_FILE" 2>&1; then
            log "CORS configuration successful!"
        else
            log "Warning: Failed to configure CORS"
            log "You can configure it manually later with: ./deploy-7-configure-cors.sh"
        fi
    fi
fi

log ""
log "Deployment and CORS configuration complete!"
log "Static Web App URL: https://$STATIC_WEB_APP_URL"
log ""
log "Next steps:"
log "1. Wait a few minutes for deployment to propagate"
log "2. Test the deployment at: https://$STATIC_WEB_APP_URL"
log ""
log "Log saved to: $LOG_FILE"
