# Storage Configuration Inconsistency

## Problem

The backend code expected different environment variable names for the same connection string value:

1. **Blob Storage**: Expected `AZURE_STORAGE_CONNECTION_STRING`
2. **Table Storage**: Expected `AZURE_STORAGE_TABLE_CONNECTION_STRING`
3. **Azure Functions Standard**: Uses `AzureWebJobsStorage` for both

## Root Cause

Azure Functions uses `AzureWebJobsStorage` as the standard environment variable name for the storage account connection string. This same connection string is used for:
- Blob storage (for function app state, logs, etc.)
- Table storage (if needed)
- Queue storage (if needed)

The backend developer created custom environment variable names instead of using the Azure Functions standard, causing:
- Configuration confusion
- Extra environment variables needed
- Potential for mismatched values

## What Was Fixed

Updated `shared/storage_factory.py` to:
1. Check `AzureWebJobsStorage` first (Azure Functions standard)
2. Fall back to custom names (`AZURE_STORAGE_CONNECTION_STRING`, `AZURE_STORAGE_TABLE_CONNECTION_STRING`) for backward compatibility
3. Use the same connection string for both blob and table storage

## Lesson Learned

**Always use platform-standard environment variable names when possible.**

For Azure Functions:
- Use `AzureWebJobsStorage` for storage connection string
- Don't create custom names unless there's a specific reason
- Document why custom names are needed if used

## Current State

The code now works with:
- `AzureWebJobsStorage` (preferred, Azure Functions standard)
- `AZURE_STORAGE_CONNECTION_STRING` (fallback for blob)
- `AZURE_STORAGE_TABLE_CONNECTION_STRING` (fallback for table, but can use same as blob)

This maintains backward compatibility while supporting the standard Azure Functions configuration.

