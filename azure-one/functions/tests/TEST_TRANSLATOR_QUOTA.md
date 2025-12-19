# Testing Translator Quota Function Locally with Real Azure Monitor

This guide explains how to test the translator quota function locally using the real Azure Monitor API (without mocking).

## Prerequisites

1. **Azure CLI installed and logged in**
   ```bash
   az login
   ```

2. **Azure Translator resource exists**
   - You should have a Translator resource in Azure
   - Know the resource group and resource name

3. **Python dependencies installed**
   ```bash
   cd azure-one/functions
   pip install -r requirements.txt
   ```

## Quick Setup

Run the setup script to configure everything automatically:

```bash
cd azure-one/functions
./tests/setup-local-monitor-test.sh [resource-group] [translator-name]
```

Example:
```bash
./tests/setup-local-monitor-test.sh rg-placeholder trans-placeholder
```

The script will:
1. Verify Azure CLI login
2. Get the Translator resource ID
3. Assign Monitoring Reader role (if needed)
4. Update `local.settings.json.local` with the resource ID
5. Test Azure credentials

## Manual Setup

If you prefer to set up manually:

### 1. Get Translator Resource ID

```bash
az cognitiveservices account show \
  --name <translator-name> \
  --resource-group <resource-group> \
  --query id -o tsv
```

### 2. Assign Monitoring Reader Role

```bash
CURRENT_USER=$(az account show --query user.name -o tsv)
RESOURCE_ID="/subscriptions/.../providers/Microsoft.CognitiveServices/accounts/..."

az role assignment create \
  --assignee "$CURRENT_USER" \
  --role "Monitoring Reader" \
  --scope "$RESOURCE_ID"
```

### 3. Update local.settings.json.local

Copy template if needed:
```bash
cp local.settings.json.template local.settings.json.local
```

Edit `local.settings.json.local` and set:
```json
{
  "Values": {
    "AZURE_TRANSLATOR_RESOURCE_ID": "/subscriptions/.../providers/Microsoft.CognitiveServices/accounts/...",
    "AZURE_TRANSLATOR_QUOTA_LIMIT": "2000000",
    "AZURE_TRANSLATOR_BILLING_CYCLE_START_DAY": "1"
  }
}
```

## Testing

### Option 1: Python Test Script

```bash
cd azure-one/functions
source ../../venv/bin/activate  # or your venv
python tests/test_translator_quota.py
```

When prompted:
- Username: any value (e.g., `test_user`)
- Password: `Hello world!`

The script will automatically use real Azure Monitor API if configured, otherwise fall back to mocked test.

### Option 2: Test with Running Function App

1. **Start the function app:**
   ```bash
   cd azure-one/functions
   func start
   ```

2. **In another terminal, run the curl test:**
   ```bash
   cd azure-one/functions
   ./tests/test_translator_quota_curl.sh
   ```

### Option 3: Manual curl Test

1. **Authenticate:**
   ```bash
   AUTH=$(curl -s -X POST "http://localhost:7071/api/authenticate" \
     -H "Content-Type: application/json" \
     -d '{"username":"test_user","password":"Hello world!"}')
   
   TOKEN=$(echo $AUTH | grep -o '"token":"[^"]*' | cut -d'"' -f4)
   USERNAME=$(echo $AUTH | grep -o '"username":"[^"]*' | cut -d'"' -f4)
   ISSUED_DATE=$(echo $AUTH | grep -o '"issued_at":"[^"]*' | cut -d'"' -f4)
   ```

2. **Query quota:**
   ```bash
   curl -X GET "http://localhost:7071/api/translator-quota" \
     -H "X-Token: $TOKEN" \
     -H "X-Username: $USERNAME" \
     -H "X-Issued-Date: $ISSUED_DATE" | python3 -m json.tool
   ```

## Expected Response

```json
{
  "total_characters_translated": 1250000,
  "quota_limit": 2000000,
  "remaining_quota": 750000,
  "percentage_used": 62.5,
  "billing_period_start": "2025-12-01T00:00:00+00:00",
  "billing_period_end": "2025-12-18T10:30:00+00:00",
  "next_reset_time": "2026-01-01T00:00:00+00:00",
  "next_reset_date": "2026-01-01T00:00:00+00:00"
}
```

## Troubleshooting

### "Authentication required" (401)
- Make sure you're using the correct password (`Hello world!` by default)
- Check that `AUTH_SECRET` matches in your settings

### "Translator resource ID not configured" (500)
- Make sure `AZURE_TRANSLATOR_RESOURCE_ID` is set in `local.settings.json.local`
- Run the setup script: `./tests/setup-local-monitor-test.sh`

### "Failed to query quota" (500)
- Check Azure CLI login: `az account show`
- Verify Monitoring Reader role: `az role assignment list --assignee $(az account show --query user.name -o tsv) --scope <resource-id>`
- Check resource ID is correct
- Verify the Translator resource exists and is accessible

### Azure credentials error
- Make sure you're logged in: `az login`
- DefaultAzureCredential will use Azure CLI credentials automatically when running locally
- For other credential types, see [Azure Identity documentation](https://learn.microsoft.com/en-us/python/api/azure-identity/azure.identity.defaultazurecredential)

## Notes

- **DefaultAzureCredential** automatically uses Azure CLI credentials when running locally
- No need to set environment variables for credentials - Azure CLI handles it
- The function app will use the same credentials when deployed to Azure (via managed identity)
- Monitoring Reader role is required to query metrics from Azure Monitor
