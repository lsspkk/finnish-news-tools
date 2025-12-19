# Local Configuration Setup Guide

This guide helps you fill in the local configuration files with real Azure values for testing.

## Config Files That Need Real Values

### 1. `local.settings.json.local` (Main config file)

**Location:** `azure-one/functions/local.settings.json.local`

**Status:** ✅ Already in `.gitignore` (will not be committed)

**Values to fill:**
- `AZURE_TRANSLATOR_KEY` - Your Translator API key
- `AZURE_TRANSLATOR_RESOURCE_ID` - Full Azure resource ID for Translator
- `AZURE_TRANSLATOR_QUOTA_LIMIT` - Monthly quota limit (default: 2000000 for F0 tier)
- `AZURE_TRANSLATOR_BILLING_CYCLE_START_DAY` - Day of month when billing resets (default: 1)
- `AUTH_SECRET` - Secret for token generation (use a strong random value)

## Quick Setup (Automated)

Run the automated script to fill all values:

```bash
cd azure-one/functions
./tests/fill-local-config.sh [resource-group] [translator-name]
```

Example:
```bash
./tests/fill-local-config.sh rg-placeholder trans-placeholder
```

The script will:
1. ✅ Check Azure CLI login
2. ✅ Get Translator resource ID
3. ✅ Get Translator API key
4. ✅ Verify `.gitignore` includes the config file
5. ✅ Update `local.settings.json.local` with real values

## Manual Setup

If you prefer to set up manually:

### Step 1: Create config file from template

```bash
cd azure-one/functions
cp local.settings.json.template local.settings.json.local
```

### Step 2: Get Azure values

**Get Translator Resource ID:**
```bash
az cognitiveservices account show \
  --name <translator-name> \
  --resource-group <resource-group> \
  --query id -o tsv
```

**Get Translator API Key:**
```bash
az cognitiveservices account keys list \
  --name <translator-name> \
  --resource-group <resource-group> \
  --query key1 -o tsv
```

**Get Subscription ID (if needed):**
```bash
az account show --query id -o tsv
```

### Step 3: Edit `local.settings.json.local`

Update these values in the `Values` section:

```json
{
  "Values": {
    "AZURE_TRANSLATOR_KEY": "your-actual-key-here",
    "AZURE_TRANSLATOR_RESOURCE_ID": "/subscriptions/xxx/resourceGroups/xxx/providers/Microsoft.CognitiveServices/accounts/xxx",
    "AZURE_TRANSLATOR_QUOTA_LIMIT": "2000000",
    "AZURE_TRANSLATOR_BILLING_CYCLE_START_DAY": "1",
    "AUTH_SECRET": "your-random-secret-here"
  }
}
```

## Verify .gitignore

The following files are already in `.gitignore` and will NOT be committed:

✅ `local.settings.json.local` - Main local config
✅ `local.settings.json` - Alternative local config name
✅ `scraper-config.yaml.local` - Scraper config
✅ `authenticate/__init__.py.local` - Production auth config

To verify:
```bash
cd azure-one/functions
git check-ignore local.settings.json.local
```

Should output: `local.settings.json.local`

## Testing After Setup

Once configured, you can test:

```bash
# Start function app
func start

# In another terminal, test translator quota
./tests/test_translator_quota_curl.sh
```

## Security Notes

- ⚠️ **Never commit** `local.settings.json.local` to git
- ⚠️ **Never share** your Translator API key
- ✅ The file is already in `.gitignore`
- ✅ Use different keys for local testing vs production

## Troubleshooting

### "Translator not found"
- Check resource group name: `az group list --query "[].name" -o table`
- Check translator name: `az cognitiveservices account list --query "[].{Name:name, RG:resourceGroup}" -o table`

### "Not logged in"
- Run: `az login`

### "File not in .gitignore"
- Check `.gitignore` contains: `local.settings.json.local`
- If missing, add it manually
