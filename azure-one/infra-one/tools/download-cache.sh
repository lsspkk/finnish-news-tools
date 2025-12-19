#!/bin/bash

# DEVOPS
# Download all cache data from Azure Blob Storage to local folder
# Run from infra-one folder

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

# Check for required config file
if [ ! -f "resource-names.env" ]; then
    echo "Error: resource-names.env not found"
    exit 1
fi

# Load resource names from env file
source resource-names.env

# Load Azure settings
if [ ! -f "azure.settings.env" ]; then
    echo "Error: azure.settings.env not found"
    exit 1
fi
source azure.settings.env

# Validate required variables
if [ -z "$STORAGE_ACCOUNT_NAME" ] || [ -z "$RESOURCE_GROUP" ] || [ -z "$STORAGE_CONTAINER" ]; then
    echo "Error: Required variables not set"
    echo "Required: STORAGE_ACCOUNT_NAME, RESOURCE_GROUP, STORAGE_CONTAINER"
    exit 1
fi

# Local cache directory (in .gitignore)
CACHE_DIR="$SCRIPT_DIR/../local-dev/cache-download"
mkdir -p "$CACHE_DIR"

echo "Downloading cache from Azure Blob Storage..."
echo "Storage Account: $STORAGE_ACCOUNT_NAME"
echo "Container: $STORAGE_CONTAINER"
echo "Local directory: $CACHE_DIR"
echo ""

# Get connection string
CONNECTION_STRING=$(az storage account show-connection-string \
    --name "$STORAGE_ACCOUNT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query connectionString -o tsv 2>/dev/null)

if [ -z "$CONNECTION_STRING" ]; then
    echo "Error: Failed to get storage connection string"
    exit 1
fi

# Download all blobs from cache/ directory
echo "Downloading blobs from cache/..."
az storage blob download-batch \
    --source "$STORAGE_CONTAINER" \
    --destination "$CACHE_DIR" \
    --pattern "cache/*" \
    --connection-string "$CONNECTION_STRING" \
    --output table

echo ""
echo "Download complete!"
echo "Cache files saved to: $CACHE_DIR"
echo ""
echo "To view a specific file:"
echo "  cat $CACHE_DIR/cache/yle/articles/74-20200693_fi.json | jq ."

