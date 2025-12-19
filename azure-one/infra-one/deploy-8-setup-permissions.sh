#!/bin/bash

# DEVOPS
# Setup Function App Permissions for Azure Monitor
# Run from infra-one folder
#
# This script:
# 1. Enables managed identity on Function App
# 2. Assigns Monitoring Reader role to Function App's managed identity
#    on the Translator resource (for quota monitoring)
#
# Idempotent - safe to rerun

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Setup logging
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/setup-permissions-$(date +%Y%m%d-%H%M%S).log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "Starting Function App permissions setup"
log "Log file: $LOG_FILE"

# Check for required config files
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
if [ -z "$FUNCTION_APP_NAME" ] || [ -z "$RESOURCE_GROUP" ]; then
    log "Error: Required variables not set in resource-names.env"
    log "Required: FUNCTION_APP_NAME, RESOURCE_GROUP"
    exit 1
fi

# Determine translator resource group
TRANSLATOR_RG="${TRANSLATOR_RESOURCE_GROUP:-$RESOURCE_GROUP}"
if [ -z "$TRANSLATOR_NAME" ]; then
    log "Warning: TRANSLATOR_NAME not set in resource-names.env"
    log "Skipping Monitoring Reader role assignment"
    TRANSLATOR_NAME=""
fi

log "Function App: $FUNCTION_APP_NAME"
log "Resource Group: $RESOURCE_GROUP"
if [ -n "$TRANSLATOR_NAME" ]; then
    log "Translator Name: $TRANSLATOR_NAME"
    log "Translator Resource Group: $TRANSLATOR_RG"
fi

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

# Step 1: Enable managed identity on Function App
log ""
log "Step 1: Enabling managed identity on Function App..."

IDENTITY_INFO=$(az functionapp identity show \
    --name "$FUNCTION_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "{principalId:principalId, type:type}" -o json 2>/dev/null || echo "{}")

PRINCIPAL_ID=$(echo "$IDENTITY_INFO" | grep -o '"principalId": "[^"]*"' | cut -d'"' -f4 || echo "")

if [ -z "$PRINCIPAL_ID" ]; then
    log "Managed identity not enabled. Enabling..."
    IDENTITY_RESULT=$(az functionapp identity assign \
        --name "$FUNCTION_APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --query "{principalId:principalId, type:type}" -o json 2>&1)
    
    PRINCIPAL_ID=$(echo "$IDENTITY_RESULT" | grep -o '"principalId": "[^"]*"' | cut -d'"' -f4 || echo "")
    
    if [ -z "$PRINCIPAL_ID" ]; then
        log "Error: Failed to enable managed identity"
        log "Output: $IDENTITY_RESULT"
        exit 1
    fi
    
    log "Managed identity enabled successfully"
    log "Principal ID: $PRINCIPAL_ID"
else
    log "Managed identity already enabled"
    log "Principal ID: $PRINCIPAL_ID"
fi

# Step 2: Assign Monitoring Reader role at subscription level
log ""
log "Step 2: Assigning Monitoring Reader role at subscription level..."

SUBSCRIPTION_ID=$(az account show --query id -o tsv 2>/dev/null || echo "")
if [ -z "$SUBSCRIPTION_ID" ]; then
    log "Warning: Could not get subscription ID. Skipping subscription-level role assignment."
else
    log "Subscription ID: $SUBSCRIPTION_ID"
    
    SUBSCRIPTION_SCOPE="/subscriptions/$SUBSCRIPTION_ID"
    
    log "Checking for existing Monitoring Reader role assignment at subscription level..."
    EXISTING_SUB_ROLE=$(az role assignment list \
        --assignee "$PRINCIPAL_ID" \
        --scope "$SUBSCRIPTION_SCOPE" \
        --query "[?roleDefinitionName=='Monitoring Reader'].id" -o tsv 2>/dev/null || echo "")
    
    if [ -n "$EXISTING_SUB_ROLE" ]; then
        log "Monitoring Reader role already assigned at subscription level"
        log "Role assignment ID: $EXISTING_SUB_ROLE"
    else
        log "Assigning Monitoring Reader role at subscription level..."
        SUB_ROLE_RESULT=$(az role assignment create \
            --assignee-object-id "$PRINCIPAL_ID" \
            --assignee-principal-type ServicePrincipal \
            --role "Monitoring Reader" \
            --scope "$SUBSCRIPTION_SCOPE" \
            --query "{id:id, principalId:principalId, roleDefinitionName:roleDefinitionName}" -o json 2>&1)
        
        if [ $? -eq 0 ]; then
            log "Monitoring Reader role assigned successfully at subscription level"
            SUB_ROLE_ID=$(echo "$SUB_ROLE_RESULT" | grep -o '"id": "[^"]*"' | cut -d'"' -f4 || echo "")
            if [ -n "$SUB_ROLE_ID" ]; then
                log "Role assignment ID: $SUB_ROLE_ID"
            fi
        else
            log "Warning: Failed to assign Monitoring Reader role at subscription level"
            log "Output: $SUB_ROLE_RESULT"
            log "You may need to assign it manually in Azure Portal"
            log "Or ensure you have sufficient permissions"
        fi
    fi
fi

# Step 3: Assign Monitoring Reader role to Translator resource (if translator configured)
if [ -z "$TRANSLATOR_NAME" ]; then
    log ""
    log "Step 3: Skipping Monitoring Reader role assignment on Translator resource (TRANSLATOR_NAME not configured)"
    log ""
    log "Setup complete!"
    log "Log saved to: $LOG_FILE"
    exit 0
fi

log ""
log "Step 3: Assigning Monitoring Reader role on Translator resource..."

# Get translator resource ID
log "Getting translator resource ID..."
TRANSLATOR_RESOURCE_ID=$(az cognitiveservices account show \
    --name "$TRANSLATOR_NAME" \
    --resource-group "$TRANSLATOR_RG" \
    --query id -o tsv 2>&1 || echo "")

if [ -z "$TRANSLATOR_RESOURCE_ID" ]; then
    log "Warning: Translator resource '$TRANSLATOR_NAME' not found in resource group '$TRANSLATOR_RG'"
    log "Skipping Monitoring Reader role assignment"
    log ""
    log "Setup complete (managed identity enabled, but role assignment skipped)"
    log "Log saved to: $LOG_FILE"
    exit 0
fi

log "Translator resource ID: $TRANSLATOR_RESOURCE_ID"

# Check if role assignment already exists
log "Checking for existing Monitoring Reader role assignment..."
EXISTING_ROLE=$(az role assignment list \
    --assignee "$PRINCIPAL_ID" \
    --scope "$TRANSLATOR_RESOURCE_ID" \
    --query "[?roleDefinitionName=='Monitoring Reader'].id" -o tsv 2>/dev/null || echo "")

if [ -n "$EXISTING_ROLE" ]; then
    log "Monitoring Reader role already assigned"
    log "Role assignment ID: $EXISTING_ROLE"
else
    log "Assigning Monitoring Reader role..."
    ROLE_RESULT=$(az role assignment create \
        --assignee-object-id "$PRINCIPAL_ID" \
        --assignee-principal-type ServicePrincipal \
        --role "Monitoring Reader" \
        --scope "$TRANSLATOR_RESOURCE_ID" \
        --query "{id:id, principalId:principalId, roleDefinitionName:roleDefinitionName}" -o json 2>&1)
    
    if [ $? -eq 0 ]; then
        log "Monitoring Reader role assigned successfully"
        ROLE_ID=$(echo "$ROLE_RESULT" | grep -o '"id": "[^"]*"' | cut -d'"' -f4 || echo "")
        if [ -n "$ROLE_ID" ]; then
            log "Role assignment ID: $ROLE_ID"
        fi
    else
        log "Warning: Failed to assign Monitoring Reader role"
        log "Output: $ROLE_RESULT"
        log "You may need to assign it manually in Azure Portal"
        log "Or ensure you have sufficient permissions"
    fi
fi

log ""
log "Setup complete!"
log ""
log "Summary:"
log "  - Managed identity enabled: $PRINCIPAL_ID"
if [ -n "$SUBSCRIPTION_ID" ]; then
    if [ -n "$EXISTING_SUB_ROLE" ] || [ -n "$SUB_ROLE_ID" ]; then
        log "  - Monitoring Reader role (subscription): Assigned"
    else
        log "  - Monitoring Reader role (subscription): Failed (check logs above)"
    fi
fi
if [ -n "$TRANSLATOR_RESOURCE_ID" ]; then
    log "  - Translator resource: $TRANSLATOR_RESOURCE_ID"
    if [ -n "$EXISTING_ROLE" ] || [ -n "$ROLE_ID" ]; then
        log "  - Monitoring Reader role (resource): Assigned"
    else
        log "  - Monitoring Reader role (resource): Failed (check logs above)"
    fi
fi
log ""
log "Log saved to: $LOG_FILE"
