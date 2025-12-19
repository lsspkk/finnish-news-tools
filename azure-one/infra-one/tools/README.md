# DEVOPS Tools

Utility scripts for managing Azure resources and debugging.

## check-function-logs.sh / check-function-logs.py

Check Azure Function App logs.

**Usage:**
```bash
# Show last 100 lines (default)
./tools/check-function-logs.py

# Show last 50 lines
./tools/check-function-logs.py 50

# Stream logs live
./tools/check-function-logs.py --follow
```

**Note:** For detailed logs, use Azure Portal:
- Function App -> Log stream
- Application Insights (if configured)
- Functions -> Monitor (for individual function invocations)

