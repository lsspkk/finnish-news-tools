# DEVOPS
# Redeployment and Update Guide

## Overview

After making code changes to backend (Azure Functions) or frontend (Static Web App), use these scripts to deploy updates.

All scripts are idempotent and safe to rerun.

## Update Scripts

Three scripts are available for updating code:

### update-backend.sh

Updates backend Azure Functions code only.

    ./update-backend.sh

This script:
- Validates Function App exists
- Deploys updated function code from `azure-one/functions/`
- Updates existing Function App deployment
- Logs to `logs/update-backend-YYYYMMDD-HHMMSS.log`

### update-frontend.sh

Updates frontend Static Web App code only.

    ./update-frontend.sh

This script:
- Validates Static Web App exists
- Backs up local `config.js` (if exists)
- Copies `config.js.azure` to `config.js` for deployment
- Deploys updated static site code from `azure-one/static-site-one/`
- Restores local `config.js` after deployment
- Logs to `logs/update-frontend-YYYYMMDD-HHMMSS.log`

### update-all.sh

Updates both backend and frontend in one command.

    ./update-all.sh

This script:
- Runs `update-backend.sh`
- Runs `update-frontend.sh`
- Logs to `logs/update-all-YYYYMMDD-HHMMSS.log`

## When to Use Update Scripts

Use update scripts when:
- Code changes in functions (backend)
- Code changes in static-site-one (frontend)
- Bug fixes
- Feature additions
- Configuration changes in code

Do NOT use update scripts when:
- Changing Azure resource names (use deploy scripts)
- First-time deployment (use deploy scripts from [DEPLOY.md](DEPLOY.md))
- Changing Function App settings (use `deploy-5-configure-function-app-settings.sh`)

## Prerequisites

Before running update scripts:

1. Ensure Azure CLI is installed and logged in:
   az login

2. Ensure `resource-names.env` exists with correct values:
   cp resource-names.env.template resource-names.env
   # Edit resource-names.env

3. For backend updates, ensure Azure Functions Core Tools installed:
   npm install -g azure-functions-core-tools@4

4. For frontend updates, ensure `config.js.azure` exists:
   ./deploy-4-setup-static-site-config.sh

## Redeployment Scenarios

### Partial Redeployment

You can redeploy individual components:

- Functions only: `./update-backend.sh`
- Static site only: `./update-frontend.sh`
- Settings only: `./deploy-5-configure-function-app-settings.sh`

No need to recreate resources unless changing names or locations.

### Full Redeployment

To redeploy everything:

    ./update-all.sh

Or update individually:

    ./update-backend.sh
    ./update-frontend.sh

### When to Teardown and Recreate

Teardown and recreate when:
- Changing resource names
- Changing resource group
- Starting fresh
- Testing deployment process

Use teardown script:

    ./teardown-azure-resources.sh

Then rerun setup from [DEPLOY.md](DEPLOY.md):

    ./deploy-2-setup-azure-resources.sh
    # ... continue with deployment steps

## Script Idempotency

All scripts are safe to rerun:

### deploy-2-setup-azure-resources.sh

Safe to rerun. The script:
- Checks if resource group exists before creating
- Checks if storage account exists before creating
- Checks if blob container exists before creating
- Checks if table exists before creating
- Checks if translator exists before creating

If resources exist, it skips creation and continues.

### deploy-3-deploy-functions.sh

Safe to rerun. The script:
- Checks if Function App exists, creates if not
- Deploys functions (updates existing deployment)

### deploy-6-deploy-static-site.sh

Safe to rerun. The script:
- Checks if Static Web App exists, creates if not
- Deploys updates if exists

### deploy-5-configure-function-app-settings.sh

Safe to rerun. Updates Function App settings (overwrites existing).

## Verification

After updating, verify deployment:

### Backend Verification

Test RSS feed parser endpoint:

    curl -X GET "https://FUNCTION_APP_NAME.azurewebsites.net/api/rss-feed-parser?force_reload=true" \
      -H "X-Token: <token>" \
      -H "X-Issued-Date: <date>" \
      -H "X-Username: <username>"

Should return full feed data with items array.

### Frontend Verification

1. Visit Static Web App URL
2. Login and navigate to articles page
3. Check RSS load date format: "Ladattu klo HH:MM - DD.MM.YYYY"
4. If feed is 8+ hours old, verify "Päivitä" button appears
5. Click "Päivitä" button and verify feed reloads

## Troubleshooting

### Backend Update Fails

- Check Function App exists: `az functionapp show --name FUNCTION_APP_NAME --resource-group RESOURCE_GROUP`
- Check Azure Functions Core Tools installed: `func --version`
- Check log file: `logs/update-backend-*.log`

### Frontend Update Fails

- Check Static Web App exists: `az staticwebapp show --name STATIC_WEB_APP_NAME --resource-group RESOURCE_GROUP`
- Check `config.js.azure` exists: `ls static-site-one/config.js.azure`
- Check Static Web Apps CLI installed: `swa --version`
- If missing, install: `npm install -g @azure/static-web-apps-cli`
- Check log file: `logs/update-frontend-*.log`

### Azure DevOps Authentication Error

If you see an error about Azure DevOps authentication when deploying Static Web App:

- This happens when Azure CLI tries to connect to a repository
- The updated scripts use deployment authentication instead
- Make sure Static Web Apps CLI is installed: `npm install -g @azure/static-web-apps-cli`
- The scripts will automatically handle deployment authentication

### Config.js Issues

If `config.js` is overwritten incorrectly:

- Local dev config is in `config.js.local` (backup)
- Azure config is in `config.js.azure`
- Restore local: `cp config.js.local config.js` (if backup exists)

## Logs

All update scripts log to `logs/` directory:
- `logs/update-backend-YYYYMMDD-HHMMSS.log`
- `logs/update-frontend-YYYYMMDD-HHMMSS.log`
- `logs/update-all-YYYYMMDD-HHMMSS.log`

Check logs for detailed error messages if updates fail.
