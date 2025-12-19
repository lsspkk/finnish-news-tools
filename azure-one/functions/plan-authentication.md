# Authentication Plan

## Overview

HTTP trigger function for user authentication. Returns token for API access.

## Function: authenticate

HTTP POST endpoint that validates username/password and returns token.

### Request

    POST /api/authenticate
    {
        "username": "user",
        "password": "Hello world!"
    }

### Response

    {
        "success": true,
        "token": "abc123...",
        "username": "user",
        "issued_at": "2025-12-18T10:00:00Z",
        "expires_at": "2025-12-25T10:00:00Z"
    }

Note: expires_at is example value showing recommended refresh time. Actual token validation allows 30 days from issued_at.

## Password Validation

Local testing: password is "Hello world!"

Production: use authenticate/__init__.py.local with month-based password.

## Rate Limiting

IP-based rate limiting: 5 attempts per 15 minutes per IP.

Uses Azure Table Storage, same table as other rate limits.

## Token Generation

Token generated using HMAC-SHA256 with AUTH_SECRET.

Token valid for 30 days from issued date.

The expires_at field in response is example value showing recommended refresh time (e.g., 7 days). Actual validation allows full 30 days from issued_at.

## Configuration

Required environment variables:

    AUTH_SECRET - Secret for token generation
    RATE_LIMIT_TABLE_NAME - Table name for rate limits (default: rateLimits)
    AUTH_RATE_LIMIT_PER_WINDOW - Attempts per window (default: 5)
    AUTH_RATE_LIMIT_WINDOW_MINUTES - Window size in minutes (default: 15)

## Cost

Azure Table Storage: ~$0.01/month for rate limit data.

No additional services needed.

## Security

All security details stored in azure-one/infra-one/security/ folder.

Only public info: username/password auth returns token, valid token required for API calls.

## Logging

Simple logging for:
- Authentication attempts
- Rate limit violations
- Errors

Logs go to Application Insights (shared with Function App).

## Deployment

Function deployed as part of consolidated Function App.

No separate deployment needed.

