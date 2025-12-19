


Backend-agentti teki v1 modelin, mutta ei lisännyt function.json tiedostoja. Eikä kysynyt että tehdäänkö v2 vai v1.







# DEVOPS
# Azure Functions Python Version Analysis

## Current Situation

Your functions use Python Azure Functions v1 programming model:
- Uses azure.functions as func with func.HttpRequest pattern
- Requires function.json files for HTTP triggers (currently missing)
- Host version is 2.0 (runtime host, not programming model)
- Python 3.11 runtime

## Version Comparison

### Python Azure Functions v1 (Current)

Pros:
- Simple, explicit structure
- Works well for small projects
- Well-documented
- No code changes needed if you add function.json files

Cons:
- Requires function.json for each function
- More verbose configuration
- Older model (still fully supported)

### Python Azure Functions v2 (Alternative)

Pros:
- No function.json files needed
- Decorator-based (@app.route())
- Cleaner code structure
- Modern approach

Cons:
- Requires rewriting all functions
- More migration work
- Learning curve if team is unfamiliar

## Local Development Considerations

### v1 Programming Model (Current)

Local development with `func start`:
- Requires function.json files for each function
- Functions discovered via function.json files
- Works with Azure Functions Core Tools v4
- Uses local.settings.json for configuration
- Local HTTP port: 7071 (configurable in local.settings.json)

Current setup:
- local.settings.json.template exists
- CORS configured for local development (*)
- Local storage support (USE_LOCAL_STORAGE=true)
- Missing function.json files prevents local development

### v2 Programming Model

Local development with `func start`:
- No function.json files needed
- Functions discovered via decorators (@app.route)
- Works with Azure Functions Core Tools v4
- Uses local.settings.json for configuration
- Same local HTTP port: 7071

Benefits for local dev:
- Cleaner project structure
- Less configuration files
- Easier to add new functions

## Recommendation

For a small-scale, simple project: stick with v1 and add missing function.json files.

Reasons:
1. Minimal changes - just add config files
2. Code already written for v1
3. Simple and cheap - aligns with project goals
4. Faster to fix - no code rewrites
5. v1 is still fully supported
6. Local development works the same way once function.json files are added

## Alternatives for Fixing

### Option 1: Add function.json Files (Recommended)

Effort: Low (5 minutes per function)
Risk: Low
Impact: Immediate fix

Create function.json for each HTTP function:
- authenticate
- rss_feed_parser
- article_scraper
- translate_article
- query_rate_limits

Pros:
- Quick fix
- No code changes
- Works immediately
- Enables local development with func start
- Same local development experience as v2

Cons:
- More config files to maintain

### Option 2: Migrate to v2 Programming Model

Effort: High (2-4 hours)
Risk: Medium
Impact: Cleaner long-term

Rewrite functions using v2 decorators:

    from azure import functions as func
    import azure.functions as func
    
    app = func.FunctionApp()
    
    @app.route(route="authenticate", auth_level=func.AuthLevel.ANONYMOUS, methods=["POST"])
    def authenticate(req: func.HttpRequest) -> func.HttpResponse:
        # existing code

Pros:
- No function.json files
- Modern approach
- Cleaner structure
- Same local development experience (func start works the same)

Cons:
- Significant code changes
- Testing required
- Higher risk
- Need to test local development after migration

### Option 3: Use Azure Functions Core Tools v4 with Auto-Detection

Effort: Medium (30 minutes)
Risk: Low
Impact: May not work without function.json

Try deployment without explicit --python flag, but v1 model typically requires function.json files.

## Recommendation

Choose Option 1: add function.json files. This is the fastest path to a working deployment with minimal risk.

## Next Steps

1. Create all missing function.json files
2. Test deployment
3. Verify functions work
4. Consider v2 migration later if needed

## Function.json Template

Example for authenticate function:

    {
      "scriptFile": "__init__.py",
      "bindings": [
        {
          "authLevel": "anonymous",
          "type": "httpTrigger",
          "direction": "in",
          "name": "req",
          "methods": [
            "post"
          ],
          "route": "authenticate"
        },
        {
          "type": "http",
          "direction": "out",
          "name": "$return"
        }
      ]
    }

## Documentation Links

Azure Functions Python v2 Programming Model:
- Main documentation: https://learn.microsoft.com/en-us/azure/azure-functions/functions-reference-python
- v2 Programming Model guide: https://learn.microsoft.com/en-us/azure/azure-functions/functions-reference-python?tabs=asgi%2Capplication-level
- Migration guide: https://learn.microsoft.com/en-us/azure/azure-functions/functions-reference-python?tabs=asgi%2Capplication-level#migrating-from-v1-to-v2

Azure Functions Python v1 Programming Model:
- v1 Documentation: https://learn.microsoft.com/en-us/azure/azure-functions/functions-reference-python?tabs=asgi%2Capplication-level#programming-model

## Local Development Summary

Both v1 and v2 work identically for local development:
- Use `func start` command
- Use local.settings.json for configuration
- Same local HTTP port (7071)
- Same CORS configuration
- Same local storage support

Difference:
- v1: Needs function.json files (currently missing)
- v2: No function.json files needed

Current status:
- Cannot run locally because function.json files are missing
- Once function.json files are added, local development works immediately
- Same local development experience regardless of v1/v2 choice

## Notes

- Host version 2.0 in host.json is correct (runtime host version)
- Programming model v1 vs v2 is separate from host version
- Both v1 and v2 work with Python 3.11
- v1 is still fully supported and recommended for simple projects
- Local development works the same way for both v1 and v2 once configured
