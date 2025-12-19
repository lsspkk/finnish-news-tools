#!/bin/bash

# DEVOPS
# Test Deployment Script
# Tests that Azure resources exist and basic functionality works
# Does NOT use translation quota - only tests authentication and query-rate-limits

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

# Setup logging
LOG_DIR="$SCRIPT_DIR/../logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/test-deployment-$(date +%Y%m%d-%H%M%S).log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "Starting deployment tests"
log "Log file: $LOG_FILE"

# Check for required config file
if [ ! -f "resource-names.env" ]; then
    log "Error: resource-names.env not found"
    log "Create it by copying: cp resource-names.env.template resource-names.env"
    exit 1
fi

# Load resource names from env file
source resource-names.env
log "Loaded resource names from resource-names.env"

# Validate required variables
if [ -z "$FUNCTION_APP_NAME" ] || [ -z "$RESOURCE_GROUP" ] || [ -z "$STATIC_WEB_APP_NAME" ]; then
    log "Error: Required variables not set in resource-names.env"
    log "Required: FUNCTION_APP_NAME, RESOURCE_GROUP, STATIC_WEB_APP_NAME"
    exit 1
fi

# Check if Azure CLI is available
if ! command -v az &> /dev/null; then
    log "Error: Azure CLI not found"
    exit 1
fi

# Check if logged in
if ! az account show &> /dev/null; then
    log "Error: Not logged in to Azure. Run 'az login' first."
    exit 1
fi

# Check if curl is available
if ! command -v curl &> /dev/null; then
    log "Error: curl not found"
    exit 1
fi

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TOKEN=""

test_result() {
    local test_name="$2"
    if [ $1 -eq 0 ]; then
        log "PASS: $test_name"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        log "FAIL: $test_name"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

log ""
log "=========================================="
log "Testing Azure Resources Existence"
log "=========================================="
log ""

# Test 1: Function App exists
log "Test 1: Function App exists"
log "Checking: $FUNCTION_APP_NAME"
if az functionapp show --name "$FUNCTION_APP_NAME" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
    FUNCTION_APP_URL="https://${FUNCTION_APP_NAME}.azurewebsites.net"
    log "Function App URL: $FUNCTION_APP_URL"
    test_result 0 "Function App '$FUNCTION_APP_NAME' exists"
else
    test_result 1 "Function App '$FUNCTION_APP_NAME' not found"
fi
log ""

# Test 2: Static Web App exists
log "Test 2: Static Web App exists"
log "Checking: $STATIC_WEB_APP_NAME"
STATIC_WEB_APP_URL=$(az staticwebapp show \
    --name "$STATIC_WEB_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "defaultHostname" -o tsv 2>/dev/null || echo "")

if [ -n "$STATIC_WEB_APP_URL" ]; then
    STATIC_WEB_APP_FULL_URL="https://$STATIC_WEB_APP_URL"
    log "Static Web App URL: $STATIC_WEB_APP_FULL_URL"
    test_result 0 "Static Web App '$STATIC_WEB_APP_NAME' exists"
else
    test_result 1 "Static Web App '$STATIC_WEB_APP_NAME' not found"
fi
log ""

# Test 3: Function App is running
log "Test 3: Function App is running"
log "Checking: $FUNCTION_APP_URL"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$FUNCTION_APP_URL" || echo "000")
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "404" ] || [ "$HTTP_CODE" = "403" ]; then
    test_result 0 "Function App responds to HTTP requests (HTTP $HTTP_CODE)"
else
    test_result 1 "Function App not responding (HTTP $HTTP_CODE)"
fi
log ""

log ""
log "=========================================="
log "Testing Backend Functions"
log "=========================================="
log ""

FUNCTION_API_URL="${FUNCTION_APP_URL}/api"

# Get username and password from command line arguments or use defaults
TEST_USERNAME="${1:-test}"
TEST_PASSWORD="${2:-Hello world!}"

log "Using credentials: username='$TEST_USERNAME', password='***'"
log ""

# Test 4: Authentication endpoint
log "Test 4: Authentication endpoint"
log "POST $FUNCTION_API_URL/authenticate"
AUTH_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$FUNCTION_API_URL/authenticate" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"$TEST_USERNAME\",\"password\":\"$TEST_PASSWORD\"}" 2>&1 || echo "ERROR\n000")

HTTP_CODE=$(echo "$AUTH_RESPONSE" | tail -n1)
AUTH_BODY=$(echo "$AUTH_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    # Extract token using jq if available, otherwise use sed
    if command -v jq &> /dev/null; then
        TOKEN=$(echo "$AUTH_BODY" | jq -r '.token // empty' 2>/dev/null || echo "")
    else
        TOKEN=$(echo "$AUTH_BODY" | sed -n 's/.*"token":"\([^"]*\)".*/\1/p' || echo "")
    fi
    if [ -n "$TOKEN" ] && [ "$TOKEN" != "null" ]; then
        test_result 0 "Authentication endpoint works, token received"
    else
        test_result 1 "Authentication response missing token"
        log "Response body: $AUTH_BODY"
        TOKEN=""
    fi
else
    test_result 1 "Authentication endpoint failed (HTTP $HTTP_CODE)"
    log "Response: $AUTH_BODY"
    TOKEN=""
fi
log ""

# Test 5: Query rate limits (no quota used)
if [ -n "$TOKEN" ]; then
    log "Test 5: Query rate limits endpoint"
    log "GET $FUNCTION_API_URL/query-rate-limits"
    
    RATE_LIMIT_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$FUNCTION_API_URL/query-rate-limits" \
        -H "X-Token: $TOKEN" \
        -H "X-Username: $TEST_USERNAME" \
        -H "X-Issued-Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)" 2>&1 || echo "ERROR\n000")
    
    HTTP_CODE=$(echo "$RATE_LIMIT_RESPONSE" | tail -n1)
    RATE_LIMIT_BODY=$(echo "$RATE_LIMIT_RESPONSE" | sed '$d')
    
    if [ "$HTTP_CODE" = "200" ]; then
        test_result 0 "Query rate limits endpoint works (HTTP $HTTP_CODE)"
    else
        test_result 1 "Query rate limits endpoint failed (HTTP $HTTP_CODE)"
        log "Response: $RATE_LIMIT_BODY"
    fi
else
    log "Test 5: Query rate limits endpoint"
    test_result 1 "Query rate limits skipped - no authentication token"
fi
log ""

log ""
log "=========================================="
log "Testing Frontend"
log "=========================================="
log ""

# Test 6: Frontend login page exists
if [ -n "$STATIC_WEB_APP_FULL_URL" ]; then
    log "Test 6: Frontend login page exists"
    log "Checking: $STATIC_WEB_APP_FULL_URL"
    
    FRONTEND_RESPONSE=$(curl -s -w "\n%{http_code}" "$STATIC_WEB_APP_FULL_URL" 2>&1 || echo "ERROR\n000")
    HTTP_CODE=$(echo "$FRONTEND_RESPONSE" | tail -n1)
    FRONTEND_BODY=$(echo "$FRONTEND_RESPONSE" | sed '$d')
    
    if [ "$HTTP_CODE" = "200" ]; then
        if echo "$FRONTEND_BODY" | grep -q "Finnish News Reader" && echo "$FRONTEND_BODY" | grep -q "login"; then
            test_result 0 "Frontend login page exists and contains login form"
        else
            test_result 1 "Frontend page exists but doesn't contain login form"
        fi
    else
        test_result 1 "Frontend not accessible (HTTP $HTTP_CODE)"
    fi
else
    log "Test 6: Frontend login page exists"
    test_result 1 "Frontend login page check skipped - Static Web App URL not available"
fi
log ""

log ""
log "=========================================="
log "Test Summary"
log "=========================================="
log "Tests passed: $TESTS_PASSED"
log "Tests failed: $TESTS_FAILED"
log ""

if [ $TESTS_FAILED -eq 0 ]; then
    log "All tests passed!"
    exit 0
else
    log "Some tests failed. Check log file: $LOG_FILE"
    exit 1
fi
