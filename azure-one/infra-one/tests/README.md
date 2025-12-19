# DEVOPS
# Deployment Tests

Test scripts for verifying Azure deployment.

## test-deployment.sh

Simple deployment test that verifies:
- Azure resources exist (Function App, Static Web App)
- Function App is running
- Authentication endpoint works
- Query rate limits endpoint works (no translation quota used)
- Frontend login page exists and is accessible

Does NOT use translation quota - only tests endpoints that don't consume paid services.

## Usage

Run from infra-one folder:

    ./tests/test-deployment.sh [username] [password]

Or from tests folder:

    cd tests
    ./test-deployment.sh [username] [password]

Arguments:
- username (optional): Username for authentication test (default: "test")
- password (optional): Password for authentication test (default: "Hello world!")

Examples:

    # Use default credentials
    ./tests/test-deployment.sh

    # Use custom username and password
    ./tests/test-deployment.sh myuser "My Password"

## Requirements

- Azure CLI installed and logged in
- resource-names.env configured
- curl installed
- Function App and Static Web App deployed

## Output

Test results are logged to:
- Console output
- logs/test-deployment-YYYYMMDD-HHMMSS.log

Exit code:
- 0 if all tests pass
- 1 if any test fails

## What It Tests

1. Function App exists in Azure
2. Static Web App exists in Azure
3. Function App responds to HTTP requests
4. Authentication endpoint works (POST /api/authenticate)
5. Query rate limits endpoint works (GET /api/query-rate-limits)
6. Frontend login page exists and contains login form

## Notes

- Default credentials: username="test", password="Hello world!"
- Can override with command-line arguments: ./tests/test-deployment.sh [username] [password]
- Does not call RSS feed parser, article scraper, or translation endpoints
- These endpoints consume quota/rate limits
- Only tests authentication and rate limit queries
