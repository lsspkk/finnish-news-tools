# DEVOPS
# Infrastructure

## Summary

Azure infrastructure deployment and management scripts for fnt-news-v1 project. All deployment scripts are numbered (deploy-1-*, deploy-2-*, etc.) to indicate execution order.

## Resource Names

Default placeholder names (customize in resource-names.env):

- Resource Group: rg-placeholder
- Function App: func-placeholder (https://func-placeholder.azurewebsites.net)
- Static Web App: web-placeholder (https://web-placeholder.azurestaticapps.net)
- Storage Account: stplaceholder
- Storage Container: placeholder-container
- Translator: trans-placeholder

All scripts use these names by default. To customize, copy resource-names.env.template to resource-names.env and edit.

## Documentation

- [INSTALL.md](INSTALL.md) - Install required software (Azure CLI, Functions Core Tools, Python, etc.)
- [DEPLOY.md](DEPLOY.md) - Initial deployment guide
- [REDEPLOY.md](REDEPLOY.md) - Redeployment and update guide
- [MONITOR.md](MONITOR.md) - Monitoring and troubleshooting guide
- [AZURE_CONFIG_README.md](AZURE_CONFIG_README.md) - Azure configuration details

## Quick Links

### First Time Setup
1. Install software: See [INSTALL.md](INSTALL.md)
2. Configure resources: Copy `resource-names.env.template` to `resource-names.env`
3. Deploy: See [DEPLOY.md](DEPLOY.md)

### Updates
- After code changes: See [REDEPLOY.md](REDEPLOY.md)

### Monitoring
- Check logs and status: See [MONITOR.md](MONITOR.md)

## Deployment Scripts

All scripts log to `logs/` directory with timestamps.

1. `deploy-1-register-resource-providers.sh` - Register Azure resource providers (first time only)
2. `deploy-2-setup-azure-resources.sh` - Create Azure resources (resource group, storage, translator)
3. `deploy-3-deploy-functions.sh` - Deploy Azure Functions
4. `deploy-4-setup-static-site-config.sh` - Setup static site configuration
5. `deploy-5-configure-function-app-settings.sh` - Configure Function App settings
6. `deploy-6-deploy-static-site.sh` - Deploy static web app
7. `deploy-7-configure-cors.sh` - Configure CORS (optional, auto-configured by deploy-6)

See [DEPLOY.md](DEPLOY.md) for detailed deployment steps.

## Update Scripts

- `update-backend.sh` - Update backend functions only
- `update-frontend.sh` - Update frontend static site only
- `update-all.sh` - Update both backend and frontend

See [REDEPLOY.md](REDEPLOY.md) for update procedures.

## Other Scripts

- `find-translator.sh` - Find existing translator service
- `teardown-azure-resources.sh` - Delete all Azure resources
- `test-azure-backend.sh` - Test backend endpoints
