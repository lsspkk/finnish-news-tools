#!/bin/bash

# DEVOPS
# Update Frontend (Static Web App) Script
# Deploys updated frontend code to Azure
# Run from infra-one folder

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Setup logging
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/update-frontend-$(date +%Y%m%d-%H%M%S).log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "Starting frontend update"
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
if [ -z "$STATIC_WEB_APP_NAME" ] || [ -z "$RESOURCE_GROUP" ]; then
    log "Error: Required variables not set in resource-names.env"
    log "Required: STATIC_WEB_APP_NAME, RESOURCE_GROUP"
    exit 1
fi

log "Static Web App: $STATIC_WEB_APP_NAME"
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
    log "Error: Static Web App '$STATIC_WEB_APP_NAME' does not exist"
    log "Create it first by running: ./deploy-6-deploy-static-site.sh"
    exit 1
fi

# Deploy updates
log "Getting deployment token..."
DEPLOYMENT_TOKEN=$(az staticwebapp secrets list \
    --name "$STATIC_WEB_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.apiKey" -o tsv 2>> "$LOG_FILE")

if [ -z "$DEPLOYMENT_TOKEN" ]; then
    log "Error: Failed to get deployment token"
    log "Check log file for details: $LOG_FILE"
    # Restore config.js if deployment failed
    if [ -f "config.js.local" ]; then
        log "Restoring config.js from backup..."
        mv config.js.local config.js
    fi
    exit 1
fi

# Verify critical files exist before deploying
log "Verifying critical files exist..."
CRITICAL_FILES=("api.js" "article.html" "app.js" "auth.js" "index.html" "styles.css" "config.js")
MISSING_FILES=()
for file in "${CRITICAL_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        MISSING_FILES+=("$file")
    fi
done

if [ ${#MISSING_FILES[@]} -ne 0 ]; then
    log "Error: Missing critical files: ${MISSING_FILES[*]}"
    # Restore config.js if verification failed
    if [ -f "config.js.local" ]; then
        log "Restoring config.js from backup..."
        mv config.js.local config.js
    fi
    exit 1
fi

log "All critical files verified"

# Verify api.js contains the fix for Azure API response handling
if grep -q "data.results && Array.isArray(data.results)" api.js; then
    log "Verified: api.js contains Azure API response handling fix"
else
    log "Warning: api.js may not contain the Azure API response handling fix"
fi

log "Deploying updated static site..."

# Check if swa CLI is available
if ! command -v swa &> /dev/null; then
    log "Error: Static Web Apps CLI (swa) not found."
    log "Install it with: npm install -g @azure/static-web-apps-cli"
    # Restore config.js if deployment failed
    if [ -f "config.js.local" ]; then
        log "Restoring config.js from backup..."
        mv config.js.local config.js
    fi
    exit 1
fi

log "Using Static Web Apps CLI: $(swa --version)"

# Change back to infra-one directory for consistent deployment (like deploy-6-deploy-static-site.sh)
cd "$SCRIPT_DIR"
log "Changed to infra-one directory for deployment"

# Deploy using Static Web Apps CLI from parent directory
# Use --app-location and --output-location to specify the static site folder (consistent with deploy-6-deploy-static-site.sh)
STATIC_SITE_RELATIVE_PATH="../static-site-one"
if swa deploy \
    --app-location "$STATIC_SITE_RELATIVE_PATH" \
    --output-location "$STATIC_SITE_RELATIVE_PATH" \
    --deployment-token "$DEPLOYMENT_TOKEN" \
    --env production >> "$LOG_FILE" 2>&1; then
    log "Frontend update successful!"
else
    log "Error: Frontend update failed. Check log file: $LOG_FILE"
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
STATIC_WEB_APP_URL=$(az staticwebapp show \
    --name "$STATIC_WEB_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "defaultHostname" -o tsv 2>> "$LOG_FILE")

log ""
log "Frontend update complete!"
log "Static Web App URL: https://$STATIC_WEB_APP_URL"
log ""
log "Verification steps:"
log "1. Wait 1-2 minutes for deployment to propagate"
log "2. Visit: https://$STATIC_WEB_APP_URL/article.html?shortcode=74-20200693"
log "3. Open browser DevTools (F12) and check Console for any errors"
log "4. Verify api.js fix is deployed by checking Network tab -> api.js -> Response"
log ""
log "If changes don't appear:"
log "- Clear browser cache (Ctrl+Shift+Delete) or use Incognito mode"
log "- Check deployment logs in Azure Portal: Static Web App -> Deployment history"
log "- Verify files were uploaded by checking the log file: $LOG_FILE"
log ""
log "Log saved to: $LOG_FILE"
