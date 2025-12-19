#!/bin/bash

# DEVOPS
# Teardown Azure Resources for fnt-news-v1
# Deletes: Resource Group (and all resources in it)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Setup logging
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/teardown-azure-resources-$(date +%Y%m%d-%H%M%S).log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "Starting Azure resources teardown"
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
log ""
log "WARNING: This will delete the entire resource group and ALL resources in it!"
log "This includes:"
log "  - Storage Account ($STORAGE_ACCOUNT_NAME)"
log "  - Translator ($TRANSLATOR_NAME)"
log "  - Function App (if exists)"
log "  - Static Web App (if exists)"
log "  - All other resources in the resource group"
log ""

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

# Check if resource group exists
if ! az group show --name "$RESOURCE_GROUP" &>/dev/null; then
    log "Resource group '$RESOURCE_GROUP' does not exist. Nothing to delete."
    exit 0
fi

# Confirm deletion
echo ""
read -p "Type 'yes' to confirm deletion of resource group '$RESOURCE_GROUP': " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    log "Deletion cancelled."
    exit 0
fi

# Delete resource group
log "Deleting resource group '$RESOURCE_GROUP'..."
log "This may take a few minutes..."

if az group delete --name "$RESOURCE_GROUP" --yes --no-wait >> "$LOG_FILE" 2>&1; then
    log "Resource group deletion initiated."
    log "Deletion is running in background. Check Azure Portal for status."
else
    log "Error: Failed to delete resource group. Check log file: $LOG_FILE"
    exit 1
fi

log ""
log "Teardown complete!"
log "Log saved to: $LOG_FILE"
