# DEVOPS
# Code Changes Summary - RSS Feed Load Date Feature

## Changes Made

### Backend Changes

File: azure-one/functions/rss_feed_parser/__init__.py

- Added force_reload query parameter support
- When force_reload=true, bypasses cache and fetches fresh RSS feed
- Returns full feed data (with items array) instead of metadata only
- Both cached and fresh responses now return complete feed data

### Frontend Changes

Files modified:
- azure-one/static-site-one/app.js
- azure-one/static-site-one/articles.html
- azure-one/static-site-one/api.js
- azure-one/static-site-one/styles.css

Changes:
- Added formatRSSLoadDate() function for Finnish date format
- Added isRSSFeedOld() function to check if feed is 8+ hours old
- Updated articles.html to display "Ladattu klo HH:MM - DD.MM.YYYY"
- Added gray "Päivitä" button when feed is 8+ hours old
- Added forceReloadRSS() function to trigger feed reload
- Updated fetchRSSFeed() to support force_reload parameter
- Added CSS styles for feed-load-info section

## Deployment Required

Yes, you need to deploy these changes to Azure.

### Backend Deployment

Run from infra-one folder:

    ./update-backend.sh

This deploys the updated rss_feed_parser function with force_reload support.

### Frontend Deployment

Run from infra-one folder:

    ./update-frontend.sh

This deploys the updated frontend code with RSS load date display and refresh button.

### Deploy Both

Run from infra-one folder:

    ./update-all.sh

This deploys both backend and frontend updates.

## Prerequisites

Before running update scripts:

1. Ensure Azure CLI is logged in:
   az login

2. Ensure resource-names.env exists:
   cp resource-names.env.template resource-names.env
   # Edit with your values

3. For backend: Azure Functions Core Tools installed:
   npm install -g azure-functions-core-tools@4

4. For frontend: config.js.azure exists:
   ./setup-static-site-config.sh

## Verification

After deployment:

1. Visit Static Web App URL
2. Login and go to articles page
3. Verify RSS load date shows: "Ladattu klo HH:MM - DD.MM.YYYY"
4. If feed is old, verify "Päivitä" button appears
5. Click "Päivitä" and verify feed reloads

## Scripts Created

New update scripts created:
- update-backend.sh - Update backend only
- update-frontend.sh - Update frontend only
- update-all.sh - Update both

These scripts are safe to rerun and log all operations.

## Notes

- Existing deploy-functions.sh and deploy-static-site.sh scripts also support updates
- Update scripts are convenience wrappers that assume resources already exist
- All scripts log to logs/ directory with timestamps
- Config.js is automatically backed up and restored during frontend deployment
