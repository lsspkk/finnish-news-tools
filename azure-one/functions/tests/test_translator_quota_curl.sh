#!/bin/bash

BASE_URL="${1:-http://localhost:7071}"
USERNAME="${2:-test_user}"
PASSWORD="${3:-Hello world!}"

echo "=== Translator Quota Test (curl) ==="
echo "Base URL: $BASE_URL"
echo "Username: $USERNAME"
echo ""

AUTH_RESPONSE=$(curl -s -X POST "$BASE_URL/api/authenticate" \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"$USERNAME\", \"password\": \"$PASSWORD\"}")

if [ $? -ne 0 ]; then
    echo "✗ Failed to connect to function app"
    echo "Make sure the function app is running: func start"
    exit 1
fi

TOKEN=$(echo "$AUTH_RESPONSE" | grep -o '"token":"[^"]*' | cut -d'"' -f4)
USERNAME=$(echo "$AUTH_RESPONSE" | grep -o '"username":"[^"]*' | cut -d'"' -f4)
ISSUED_DATE=$(echo "$AUTH_RESPONSE" | grep -o '"issued_at":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo "✗ Authentication failed"
    echo "Response: $AUTH_RESPONSE"
    exit 1
fi

echo "✓ Authenticated"
echo ""

echo "--- Querying Translator Quota ---"
QUOTA_RESPONSE=$(curl -s -X GET "$BASE_URL/api/translator-quota" \
  -H "X-Token: $TOKEN" \
  -H "X-Username: $USERNAME" \
  -H "X-Issued-Date: $ISSUED_DATE")

echo "$QUOTA_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$QUOTA_RESPONSE"

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/api/translator-quota" \
  -H "X-Token: $TOKEN" \
  -H "X-Username: $USERNAME" \
  -H "X-Issued-Date: $ISSUED_DATE")

if [ "$HTTP_CODE" = "200" ]; then
    echo ""
    echo "✓ Quota query successful (HTTP $HTTP_CODE)"
elif [ "$HTTP_CODE" = "500" ]; then
    echo ""
    echo "⚠ Quota query returned error (HTTP $HTTP_CODE)"
    echo "This might be expected if Azure Monitor API is not configured or accessible"
    echo "Check AZURE_TRANSLATOR_RESOURCE_ID and Azure credentials"
else
    echo ""
    echo "✗ Quota query failed (HTTP $HTTP_CODE)"
fi
