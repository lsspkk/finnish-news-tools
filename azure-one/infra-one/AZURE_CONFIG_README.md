# DEVOPS
# Azure Configuration for Static Site

## Status

Frontend code is complete and ready for Azure deployment. All required changes from deployment-readiness.md have been implemented.

## Configuration Files

1. config.js.azure.template - Template in static-site-one folder
2. deploy-4-setup-static-site-config.sh - Helper script to create config.js.azure
3. DEPLOY.md - Step-by-step deployment guide
4. deployment-status.md - Verification that all frontend code is complete

## What You Need

To deploy the frontend to Azure, you need:

1. Azure Function App name (where your backend functions are deployed)
2. Azure Static Web App name (or we'll create one)

## Quick Start

### Setup Configuration

Run setup script from infra-one folder:

    ./deploy-4-setup-static-site-config.sh

The script will:
- Check Azure CLI login
- List available Function Apps
- Create config.js.azure in static-site-one folder with correct URLs

### Deploy

Deploy from infra-one folder:

    ./deploy-6-deploy-static-site.sh

## Function App URL Structure

If your Function App name is "func-placeholder", the URLs will be:

- authApiUrl: https://func-placeholder.azurewebsites.net/api
- apiBaseUrl: https://func-placeholder.azurewebsites.net/api
- translatorApiUrl: https://func-placeholder.azurewebsites.net/api

All functions are accessed via the same Function App with different paths:
- /api/authenticate
- /api/rss-feed-parser
- /api/article-scraper
- /api/translate-article

## Deployment

See DEPLOY.md for detailed deployment steps.

## Notes

- config.js.azure is in .gitignore (not committed to git)
- Local development still uses config.js with localhost URLs
- The isLocalDev flag automatically detects environment
- For Azure deployment, replace config.js with config.js.azure
