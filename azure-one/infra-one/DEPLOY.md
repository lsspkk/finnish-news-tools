# DEVOPS
# Deployment Guide

## Prerequisites

- Azure CLI installed and logged in (see [INSTALL.md](INSTALL.md))
- Azure Functions Core Tools installed (see [INSTALL.md](INSTALL.md))
- Static Web Apps CLI installed: `npm install -g @azure/static-web-apps-cli`
- Python 3.11 installed (see [INSTALL.md](INSTALL.md))

## Step 1: Configure Resource Names

Copy template and edit with your values:

    cp resource-names.env.template resource-names.env

Edit `resource-names.env` with your Azure resource names.

### Find Existing Translator Service

If you already have a translator service and forgot its name:

    ./find-translator.sh

This lists all translator services in your subscription. Update `TRANSLATOR_NAME` and `TRANSLATOR_RESOURCE_GROUP` in `resource-names.env`.

Note: Translator can be in a different resource group. Set `TRANSLATOR_RESOURCE_GROUP` if different from `RESOURCE_GROUP`. If empty, uses `RESOURCE_GROUP`.

## Step 2: Register Resource Providers

Before first deployment, register Azure resource providers:

    ./deploy-1-register-resource-providers.sh

This registers:
- Microsoft.Web (for Function Apps)
- Microsoft.Storage (for Storage Accounts)
- Microsoft.CognitiveServices (for Translator)

Registration may take 1-2 minutes. Only needed once per subscription.

## Step 3: Create Azure Resources

Run the setup script to create all required Azure resources:

    ./deploy-2-setup-azure-resources.sh

This creates:
- Resource Group
- Storage Account
- Blob Storage Container
- Table Storage (for rate limits)
- Translator Cognitive Service (if needed)

The script is idempotent - safe to rerun. It checks if resources exist before creating them.

## Step 4: Setup Production Authentication (Optional)

For production authentication configuration:

    cd ../functions
    cp authenticate/__init__.py.local.template authenticate/__init__.py.local

The file `authenticate/__init__.py.local` is in `.gitignore` and will not be committed. Deployment scripts automatically use this file for production deployment.

## Step 5: Deploy Function App

Deploy from infra-one folder:

    ./deploy-3-deploy-functions.sh

This creates Function App if it doesn't exist and deploys functions.

## Step 6: Configure Function App Settings

Configure settings from infra-one folder:

1. Copy template:
   cp azure.settings.env.template azure.settings.env

2. Edit `azure.settings.env` with your values.

3. Apply settings:
   ./deploy-5-configure-function-app-settings.sh

The `azure.settings.env` file is in `.gitignore` and will not be committed.

## Step 7: Setup Function App Permissions

Setup managed identity and role assignments:

    ./deploy-8-setup-permissions.sh

This script:
- Enables managed identity on Function App (if not already enabled)
- Assigns Monitoring Reader role to Function App's managed identity
  on the Translator resource (for quota monitoring)

Idempotent - safe to rerun. Requires `TRANSLATOR_NAME` in `resource-names.env`.

## Step 8: Setup Static Site Configuration

Setup configuration for static site:

    ./deploy-4-setup-static-site-config.sh

This creates `config.js.azure` in the static-site-one folder with correct Function App URLs.

## Step 9: Deploy Static Web App

Deploy static site:

    ./deploy-6-deploy-static-site.sh

This script:
- Creates Static Web App if it doesn't exist
- Deploys static site files
- Configures CORS on Function App automatically
- Logs to `logs/deploy-static-site-YYYYMMDD-HHMMSS.log`

Requires Static Web Apps CLI: `npm install -g @azure/static-web-apps-cli`

## Step 10: Configure CORS (Optional)

CORS is automatically configured when deploying Static Web App with `./deploy-6-deploy-static-site.sh`.

To configure CORS separately (if needed):

    ./deploy-7-configure-cors.sh

This automatically gets the Static Web App URL and configures CORS on Function App.

## Verification

### Verify Function App

Check Function App URL:

    az functionapp show \
      --name func-placeholder \
      --resource-group rg-placeholder \
      --query defaultHostname -o tsv

Visit: `https://func-placeholder.azurewebsites.net`

### Verify Static Web App

Check Static Web App URL:

    az staticwebapp show \
      --name web-placeholder \
      --resource-group rg-placeholder \
      --query defaultHostname -o tsv

Visit the URL and test:
1. Login page loads
2. Can authenticate
3. Articles list loads
4. Article content loads
5. Translation works
