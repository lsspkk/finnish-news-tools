#!/bin/bash

# DEVOPS
# Check Azure Function App Logs
# Fetches recent logs from Azure Function App
# Run from infra-one folder

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

# Check for required config file
if [ ! -f "resource-names.env" ]; then
    echo "Error: resource-names.env not found"
    echo "Create it by copying: cp resource-names.env.template resource-names.env"
    exit 1
fi

# Load resource names from env file
source resource-names.env

# Validate required variables
if [ -z "$FUNCTION_APP_NAME" ] || [ -z "$RESOURCE_GROUP" ]; then
    echo "Error: Required variables not set in resource-names.env"
    echo "Required: FUNCTION_APP_NAME, RESOURCE_GROUP"
    exit 1
fi

# Default to last 100 lines, but allow override
LINES=${1:-100}

echo "Fetching last $LINES lines of logs from Function App: $FUNCTION_APP_NAME"
echo ""

# Fetch logs using Azure CLI
# Note: Azure CLI doesn't support tail directly, so we use log stream and limit output
az functionapp log show \
    --name "$FUNCTION_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --output table 2>&1 | tail -n "$LINES" || \
az monitor app-insights query \
    --app "$FUNCTION_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --analytics-query "traces | order by timestamp desc | take $LINES" \
    --output table 2>&1 | tail -n "$LINES" || \
echo "Note: Log streaming may require Application Insights. Use Azure Portal for detailed logs."

echo ""
echo "Tip: Use 'az functionapp log tail --name $FUNCTION_APP_NAME --resource-group $RESOURCE_GROUP' for live streaming"
echo "Or check logs in Azure Portal: https://portal.azure.com"

