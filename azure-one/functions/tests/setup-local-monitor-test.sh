#!/bin/bash

echo "=== Setting up local Azure Monitor testing ==="
echo ""

RESOURCE_GROUP="${1:-rg-placeholder}"
TRANSLATOR_NAME="${2:-trans-placeholder}"

echo "Resource Group: $RESOURCE_GROUP"
echo "Translator Name: $TRANSLATOR_NAME"
echo ""

echo "1. Checking Azure CLI login..."
az account show > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "✗ Not logged in to Azure CLI"
    echo "Please run: az login"
    exit 1
fi

SUBSCRIPTION_ID=$(az account show --query id -o tsv)
echo "✓ Logged in (Subscription: $SUBSCRIPTION_ID)"
echo ""

echo "2. Getting Translator resource ID..."
RESOURCE_ID=$(az cognitiveservices account show \
    --name "$TRANSLATOR_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query id -o tsv 2>/dev/null)

if [ -z "$RESOURCE_ID" ]; then
    echo "✗ Translator resource not found"
    echo "Please check resource group and name"
    echo ""
    echo "To find your resources:"
    echo "  az cognitiveservices account list --output table"
    exit 1
fi

echo "✓ Found Translator resource: $RESOURCE_ID"
echo ""

echo "3. Checking Monitoring Reader role..."
CURRENT_USER=$(az account show --query user.name -o tsv)
echo "Current user: $CURRENT_USER"

HAS_ROLE=$(az role assignment list \
    --assignee "$CURRENT_USER" \
    --scope "$RESOURCE_ID" \
    --query "[?roleDefinitionName=='Monitoring Reader']" -o tsv 2>/dev/null)

if [ -z "$HAS_ROLE" ]; then
    echo "⚠ Monitoring Reader role not assigned"
    echo "Assigning Monitoring Reader role..."
    az role assignment create \
        --assignee "$CURRENT_USER" \
        --role "Monitoring Reader" \
        --scope "$RESOURCE_ID" > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo "✓ Monitoring Reader role assigned"
    else
        echo "✗ Failed to assign role (you may need admin permissions)"
        echo "You can assign it manually in Azure Portal or ask an admin"
    fi
else
    echo "✓ Monitoring Reader role already assigned"
fi
echo ""

echo "4. Creating/updating local.settings.json.local..."
SETTINGS_FILE="local.settings.json.local"
TEMPLATE_FILE="local.settings.json.template"

if [ ! -f "$SETTINGS_FILE" ]; then
    echo "Creating $SETTINGS_FILE from template..."
    cp "$TEMPLATE_FILE" "$SETTINGS_FILE"
fi

echo "Updating AZURE_TRANSLATOR_RESOURCE_ID..."
if command -v python3 > /dev/null 2>&1; then
    python3 << EOF
import json
import sys

try:
    with open('$SETTINGS_FILE', 'r') as f:
        settings = json.load(f)
    
    settings['Values']['AZURE_TRANSLATOR_RESOURCE_ID'] = '$RESOURCE_ID'
    
    with open('$SETTINGS_FILE', 'w') as f:
        json.dump(settings, f, indent=2)
    
    print("✓ Updated $SETTINGS_FILE")
except Exception as e:
    print(f"✗ Error updating settings: {e}")
    sys.exit(1)
EOF
else
    echo "⚠ Python3 not found, please manually update $SETTINGS_FILE:"
    echo "  Set AZURE_TRANSLATOR_RESOURCE_ID to: $RESOURCE_ID"
fi
echo ""

echo "5. Testing Azure credentials..."
python3 << 'PYTHON_EOF'
import sys
try:
    from azure.identity import DefaultAzureCredential
    credential = DefaultAzureCredential()
    token = credential.get_token("https://monitor.azure.com/.default")
    print("✓ Azure credentials working")
except Exception as e:
    print(f"✗ Azure credentials error: {e}")
    print("Make sure you're logged in: az login")
    sys.exit(1)
PYTHON_EOF

if [ $? -ne 0 ]; then
    exit 1
fi

echo ""
echo "=== Setup complete! ==="
echo ""
echo "You can now test the translator quota function:"
echo "  1. Start function app: func start"
echo "  2. In another terminal: ./tests/test_translator_quota_curl.sh"
echo ""
echo "Or run Python test:"
echo "  python tests/test_translator_quota.py"
