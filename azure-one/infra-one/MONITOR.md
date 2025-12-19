# DEVOPS
# Monitoring Guide

## Overview

Tools and procedures for monitoring Azure resources, checking logs, and troubleshooting issues.

## Check Function App Logs

### Using Script

Check recent logs:

    ./tools/check-function-logs.py

Show last 50 lines:

    ./tools/check-function-logs.py 50

Stream logs live:

    ./tools/check-function-logs.py --follow

### Using Azure CLI

Show last logs:

    az functionapp log show \
      --name func-placeholder \
      --resource-group rg-placeholder \
      --output table

Stream logs live:

    az functionapp log tail \
      --name func-placeholder \
      --resource-group rg-placeholder

### Using Azure Portal

For detailed logs, use Azure Portal:

1. Navigate to Function App in Azure Portal
2. Go to **Log stream** for live logs
3. Go to **Functions** -> **Monitor** for individual function invocations
4. Go to **Application Insights** (if configured) for advanced analytics

## Test Backend Endpoints

Test all backend endpoints:

    ./test-azure-backend.sh

This script tests:
- Authentication
- RSS feed parser
- Article scraper
- Translation
- Rate limits

Logs are saved to `logs/test-azure-backend-YYYYMMDD-HHMMSS.log`.

## Check Resource Status

### Function App Status

    az functionapp show \
      --name func-placeholder \
      --resource-group rg-placeholder \
      --query "{Name:name, State:state, HostNames:defaultHostName}" \
      --output table

### Static Web App Status

    az staticwebapp show \
      --name web-placeholder \
      --resource-group rg-placeholder \
      --query "{Name:name, DefaultHostname:defaultHostname, Location:location}" \
      --output table

### Storage Account Status

    az storage account show \
      --name stplaceholder \
      --resource-group rg-placeholder \
      --query "{Name:name, Location:location, ProvisioningState:provisioningState}" \
      --output table

### Translator Service Status

    az cognitiveservices account show \
      --name trans-placeholder \
      --resource-group rg-placeholder \
      --query "{Name:name, Kind:kind, ProvisioningState:provisioningState}" \
      --output table

## Check Deployment Logs

All deployment scripts log to `logs/` directory:

- `logs/deploy-1-register-resource-providers-YYYYMMDD-HHMMSS.log`
- `logs/deploy-2-setup-azure-resources-YYYYMMDD-HHMMSS.log`
- `logs/deploy-3-deploy-functions-YYYYMMDD-HHMMSS.log`
- `logs/deploy-4-setup-static-site-config-YYYYMMDD-HHMMSS.log`
- `logs/deploy-5-configure-function-app-settings-YYYYMMDD-HHMMSS.log`
- `logs/deploy-6-deploy-static-site-YYYYMMDD-HHMMSS.log`
- `logs/deploy-7-configure-cors-YYYYMMDD-HHMMSS.log`
- `logs/update-backend-YYYYMMDD-HHMMSS.log`
- `logs/update-frontend-YYYYMMDD-HHMMSS.log`
- `logs/update-all-YYYYMMDD-HHMMSS.log`

View recent logs:

    ls -lt logs/ | head -10

## Check Function App Settings

List all settings:

    az functionapp config appsettings list \
      --name func-placeholder \
      --resource-group rg-placeholder \
      --output table

Get specific setting (replace SETTING_NAME with the setting you want):

    az functionapp config appsettings list \
      --name func-placeholder \
      --resource-group rg-placeholder \
      --query "[?name=='SETTING_NAME'].value" \
      --output tsv

## Check CORS Configuration

    az functionapp cors show \
      --name func-placeholder \
      --resource-group rg-placeholder \
      --query allowedOrigins \
      --output table

## Monitor Function Invocations

### Using Azure Portal

1. Navigate to Function App
2. Go to **Functions**
3. Click on a function name
4. Go to **Monitor** tab
5. View invocation history, success/failure rates, and execution times

### Using Azure CLI

List functions:

    az functionapp function list \
      --name func-placeholder \
      --resource-group rg-placeholder \
      --output table

## Check Storage Account Usage

Check blob storage:

    az storage blob list \
      --account-name stplaceholder \
      --container-name placeholder-container \
      --output table

Check table storage:

    az storage table list \
      --account-name stplaceholder \
      --output table

## Monitor Costs

View resource costs in Azure Portal:

1. Navigate to **Cost Management + Billing**
2. Go to **Cost analysis**
3. Filter by resource group: `rg-placeholder`

Or use Azure CLI:

    az consumption usage list \
      --start-date $(date -d '1 month ago' +%Y-%m-%d) \
      --end-date $(date +%Y-%m-%d) \
      --query "[?instanceName=='rg-placeholder']" \
      --output table

## Troubleshooting Common Issues

### Function App Not Responding

1. Check Function App status (see above)
2. Check logs: `./tools/check-function-logs.py`
3. Verify settings: Check Function App settings
4. Test endpoints: `./test-azure-backend.sh`

### CORS Errors

1. Check CORS configuration (see above)
2. Reconfigure CORS: `./deploy-7-configure-cors.sh`
3. Verify Static Web App URL matches CORS allowed origins

### Storage Access Issues

1. Check storage account status (see above)
2. Verify connection string in Function App settings
3. Verify storage configuration in Function App settings

### Translation Service Issues

1. Check translator service status (see above)
2. Verify service configuration in Function App settings
3. Check usage limits in Azure Portal

## Tools Directory

Additional monitoring tools are in `tools/` directory:

- `check-function-logs.py` / `check-function-logs.sh` - Check Function App logs
- `download-cache.py` / `download-cache.sh` - Download cache from blob storage

See `tools/README.md` for details.
