#!/bin/bash

# DEVOPS
# Setup Azure Resources for fnt-news-v1
# Creates: Resource Group, Storage Account, Blob Container, Table Storage, Translator

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Setup logging
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/setup-azure-resources-$(date +%Y%m%d-%H%M%S).log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "Starting Azure resources setup"
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
if [ -z "$RESOURCE_GROUP" ] || [ -z "$STORAGE_ACCOUNT_NAME" ] || [ -z "$STORAGE_CONTAINER" ] || [ -z "$TRANSLATOR_NAME" ] || [ -z "$LOCATION" ] || [ -z "$RATE_LIMIT_TABLE_NAME" ]; then
    log "Error: Required variables not set in resource-names.env"
    log "Required: RESOURCE_GROUP, STORAGE_ACCOUNT_NAME, STORAGE_CONTAINER, TRANSLATOR_NAME, LOCATION, RATE_LIMIT_TABLE_NAME"
    exit 1
fi

# Use translator resource group if specified, otherwise use main resource group
TRANSLATOR_RG="${TRANSLATOR_RESOURCE_GROUP:-$RESOURCE_GROUP}"
if [ "$TRANSLATOR_RG" != "$RESOURCE_GROUP" ]; then
    log "Note: Translator is in different resource group: $TRANSLATOR_RG"
fi

log "Azure Resources Setup for fnt-news-v1"
log "======================================"
log ""
log "Resource Group: $RESOURCE_GROUP"
log "Storage Account: $STORAGE_ACCOUNT_NAME"
log "Storage Container: $STORAGE_CONTAINER"
log "Translator: $TRANSLATOR_NAME"
TRANSLATOR_RG="${TRANSLATOR_RESOURCE_GROUP:-$RESOURCE_GROUP}"
if [ "$TRANSLATOR_RG" != "$RESOURCE_GROUP" ]; then
    log "Translator Resource Group: $TRANSLATOR_RG (different from main resource group)"
else
    log "Translator Resource Group: $TRANSLATOR_RG (same as main resource group)"
fi
log "Location: $LOCATION"
log "Rate Limit Table: $RATE_LIMIT_TABLE_NAME"
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

# Create Resource Group
log "Creating resource group..."
if az group show --name "$RESOURCE_GROUP" &>/dev/null; then
    log "Resource group '$RESOURCE_GROUP' already exists."
else
    az group create \
        --name "$RESOURCE_GROUP" \
        --location "$LOCATION" >> "$LOG_FILE" 2>&1
    log "Resource group created."
fi
log ""

# Create Storage Account
log "Creating storage account..."
if az storage account show --name "$STORAGE_ACCOUNT_NAME" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
    log "Storage account '$STORAGE_ACCOUNT_NAME' already exists."
else
    az storage account create \
        --name "$STORAGE_ACCOUNT_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --location "$LOCATION" \
        --sku Standard_LRS >> "$LOG_FILE" 2>&1
    log "Storage account created."
fi
log ""

# Get storage account key
STORAGE_KEY=$(az storage account keys list \
    --account-name "$STORAGE_ACCOUNT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "[0].value" -o tsv)

# Create Blob Container
log "Creating blob container..."
if az storage container show --name "$STORAGE_CONTAINER" --account-name "$STORAGE_ACCOUNT_NAME" --account-key "$STORAGE_KEY" &>/dev/null; then
    log "Blob container '$STORAGE_CONTAINER' already exists."
else
    az storage container create \
        --name "$STORAGE_CONTAINER" \
        --account-name "$STORAGE_ACCOUNT_NAME" \
        --account-key "$STORAGE_KEY" \
        --public-access off >> "$LOG_FILE" 2>&1
    log "Blob container '$STORAGE_CONTAINER' created."
fi
log ""

# Create Table Storage for rate limits
log "Creating table storage for rate limits..."
if az storage table show --name "$RATE_LIMIT_TABLE_NAME" --account-name "$STORAGE_ACCOUNT_NAME" --account-key "$STORAGE_KEY" &>/dev/null; then
    log "Table '$RATE_LIMIT_TABLE_NAME' already exists."
else
    az storage table create \
        --name "$RATE_LIMIT_TABLE_NAME" \
        --account-name "$STORAGE_ACCOUNT_NAME" \
        --account-key "$STORAGE_KEY" >> "$LOG_FILE" 2>&1
    log "Table '$RATE_LIMIT_TABLE_NAME' created."
fi
log ""

# Create Translator Cognitive Service
# Commented out - user already has translator service
# Uncomment if you need to create a new translator service
# log "Creating translator cognitive service..."
# if az cognitiveservices account show --name "$TRANSLATOR_NAME" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
#     log "Translator '$TRANSLATOR_NAME' already exists."
# else
#     az cognitiveservices account create \
#         --name "$TRANSLATOR_NAME" \
#         --resource-group "$RESOURCE_GROUP" \
#         --kind TextTranslation \
#         --sku F0 \
#         --location "$LOCATION" >> "$LOG_FILE" 2>&1
#     log "Translator created."
# fi
# log ""

# Get connection string
CONNECTION_STRING=$(az storage account show-connection-string \
    --name "$STORAGE_ACCOUNT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query connectionString -o tsv)

# Get translator key
# Note: Translator service should already exist
# If translator is in different resource group, set TRANSLATOR_RESOURCE_GROUP in resource-names.env
if az cognitiveservices account show --name "$TRANSLATOR_NAME" --resource-group "$TRANSLATOR_RG" &>/dev/null; then
    TRANSLATOR_KEY=$(az cognitiveservices account keys list \
        --name "$TRANSLATOR_NAME" \
        --resource-group "$TRANSLATOR_RG" \
        --query key1 -o tsv)
    log "Translator key retrieved from existing service in resource group '$TRANSLATOR_RG'."
else
    log "Warning: Translator '$TRANSLATOR_NAME' not found in resource group '$TRANSLATOR_RG'"
    log "Run ./find-translator.sh to find your translator service"
    log "Then update TRANSLATOR_NAME and TRANSLATOR_RESOURCE_GROUP in resource-names.env"
    TRANSLATOR_KEY="UPDATE_MANUALLY"
fi

log "Setup Complete!"
log "==============="
log ""
log "Resource Group: $RESOURCE_GROUP"
log "Storage Account: $STORAGE_ACCOUNT_NAME"
log "Storage Container: $STORAGE_CONTAINER"
log "Table Storage: $RATE_LIMIT_TABLE_NAME"
log "Translator: $TRANSLATOR_NAME"
log ""
log "Connection String (for AzureWebJobsStorage):"
log "$CONNECTION_STRING"
log ""
log "Translator Key:"
log "$TRANSLATOR_KEY"
log ""
log "Next steps:"
log "1. Save the connection string and translator key securely"
log "2. Configure Function App settings with these values"
log "3. Deploy functions using: ./deploy-3-deploy-functions.sh"
log ""
log "Log saved to: $LOG_FILE"
