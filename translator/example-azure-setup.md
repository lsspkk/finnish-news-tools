# Azure Translator Setup Guide

This guide will help you set up Azure Translator API for use with the Finnish news translation tool.

## Prerequisites

- An Azure account (you mentioned you already have one)
- Azure CLI installed and configured (recommended) OR access to the Azure Portal

## Step 1: Create a Translator Resource in Azure

You can create the Translator resource using either Azure CLI (faster, scriptable) or Azure Portal (visual interface). Choose the method you prefer.

### Method A: Using Azure CLI (Recommended if you have it)

1. Log in to Azure
    az login
    This will open a browser for authentication.

2. Set your subscription (if you have multiple)
    # List available subscriptions
    az account list --output table
    
    # Set the active subscription
    az account set --subscription "Your Subscription Name or ID"

3. Create a resource group (if you don't have one)
    az group create \
      --name finnish-news-translator-rg \
      --location westeurope
    Replace `finnish-news-translator-rg` with your preferred name and `westeurope` with your preferred region.

4. Create the Translator resource
    az cognitiveservices account create \
      --name finnish-translator \
      --resource-group finnish-news-translator-rg \
      --kind TextTranslation \
      --sku F0 \
      --location westeurope
    
    Parameters:
    - `--name`: Your resource name (must be globally unique, lowercase, alphanumeric, and hyphens only)
    - `--resource-group`: Your resource group name
    - `--kind`: Must be `TextTranslation` for Translator
    - `--sku`: `F0` for Free tier, `S1` for Standard tier
    - `--location`: Azure region (e.g., `westeurope`, `eastus`, `southeastasia`)

5. Wait for deployment (usually takes 1-2 minutes)
    az cognitiveservices account show \
      --name finnish-translator \
      --resource-group finnish-news-translator-rg \
      --query "properties.provisioningState"
    This will show `Succeeded` when ready.

### Method B: Using Azure Portal

1. Log in to Azure Portal
   - Go to [https://portal.azure.com](https://portal.azure.com)
   - Sign in with your Azure account

2. Create a new Translator resource
   - Click on "Create a resource" (or use the search bar)
   - Search for "Translator" and select "Translator" from the results
   - Click "Create"

3. Configure the Translator resource
   - Subscription: Select your Azure subscription
   - Resource Group: 
     - Create a new resource group (recommended for organization)
     - Or select an existing one
   - Region: Choose a region close to you (e.g., "West Europe", "East US")
     - Note: The region affects latency but not functionality
   - Name: Give your resource a unique name (e.g., `finnish-translator`)
   - Pricing Tier: 
     - Free (F0): 2 million characters per month free
     - Standard (S1): Pay-as-you-go pricing
     - For testing, start with Free tier
   - Click "Review + create", then "Create"

4. Wait for deployment
   - Wait for the deployment to complete (usually takes 1-2 minutes)
   - Click "Go to resource" when ready

## Step 2: Get Your API Keys and Endpoint

Once your Translator resource is created, retrieve your credentials:

### Method A: Using Azure CLI (Recommended)

1. Get your API keys
    az cognitiveservices account keys list \
      --name finnish-translator \
      --resource-group finnish-news-translator-rg
    
    This outputs:
    {
      "key1": "your-api-key-here",
      "key2": "your-alternative-key-here"
    }
    
    Either `key1` or `key2` can be used (they're interchangeable).

2. Get your endpoint and region
    az cognitiveservices account show \
      --name finnish-translator \
      --resource-group finnish-news-translator-rg \
      --query "{endpoint:properties.endpoint, location:location}" \
      --output json
    
    This outputs:
    {
      "endpoint": "https://api.cognitive.microsofttranslator.com/",
      "location": "westeurope"
    }

3. Save the information
   - Copy key1 (or key2 - they work the same)
   - The endpoint is always `https://api.cognitive.microsofttranslator.com/`
   - Copy the location (region) name
   - Important: Keep these secure! Don't commit them to version control.

Quick one-liner to get everything:
    # Get key1
    az cognitiveservices account keys list \
      --name finnish-translator \
      --resource-group finnish-news-translator-rg \
      --query "key1" --output tsv

    # Get location/region
    az cognitiveservices account show \
      --name finnish-translator \
      --resource-group finnish-news-translator-rg \
      --query "location" --output tsv

### Method B: Using Azure Portal

1. Navigate to your Translator resource
   - In the Azure Portal, go to your resource group
   - Click on your Translator resource

2. Get your API keys
   - In the left sidebar, click on "Keys and Endpoint" (under "Resource Management")
   - You'll see:
     - KEY 1 and KEY 2: Either key can be used (they're interchangeable)
     - Location/Region: Your resource region (e.g., `westeurope`)
     - Endpoint: Your translation endpoint URL (e.g., `https://api.cognitive.microsofttranslator.com/`)

3. Copy the information
   - Copy KEY 1 (or KEY 2 - they work the same)
   - Copy the Endpoint URL
   - Copy the Location/Region name
   - Important: Keep these secure! Don't commit them to version control.

## View Billing Information

1. View current subscription billing
    # Get billing account info
    az billing account list --output table
    
    # Get current month's usage
    az consumption usage list \
      --start-date $(date +%Y-%m-01) \
      --end-date $(date +%Y-%m-%d) \
      --output table

2. View Translator resource metrics
    # Get character translation metrics (correct metric name)
    # Note: "CharactersTranslated" is deprecated, use "TextCharactersTranslated"
    az monitor metrics list \
      --resource /subscriptions/$(az account show --query id -o tsv)/resourceGroups/finnish-news-translator-rg/providers/Microsoft.CognitiveServices/accounts/finnish-translator \
      --metric TextCharactersTranslated \
      --start-time $(date -d "1 month ago" +%Y-%m-%dT%H:%M:%S) \
      --end-time $(date +%Y-%m-%dT%H:%M:%S) \
      --output table
    
    # View successful API calls
    az monitor metrics list \
      --resource /subscriptions/$(az account show --query id -o tsv)/resourceGroups/finnish-news-translator-rg/providers/Microsoft.CognitiveServices/accounts/finnish-translator \
      --metric SuccessfulCalls \
      --start-time $(date -d "1 month ago" +%Y-%m-%dT%H:%M:%S) \
      --end-time $(date +%Y-%m-%dT%H:%M:%S) \
      --output table
    
    # List all available metrics for your resource
    az monitor metrics list-definitions \
      --resource /subscriptions/$(az account show --query id -o tsv)/resourceGroups/finnish-news-translator-rg/providers/Microsoft.CognitiveServices/accounts/finnish-translator \
      --output table

3. View cost breakdown
    # View costs for your resource group
    az consumption usage list \
      --start-date $(date +%Y-%m-01) \
      --end-date $(date +%Y-%m-%d) \
      --query "[?contains(instanceName, 'finnish-translator')]" \
      --output table

Note: Azure Translator billing is based on characters processed (Unicode code points).
- Each character in the source text counts toward billing
- Translating to multiple languages multiplies the character count
- Example: 1,000 characters translated to 3 languages = 3,000 characters billed
- The API can return character counts per sentence if you use includeSentenceLength=true

Alternative: Check usage in Azure Portal
- Go to Azure Portal → Your Translator resource → Metrics
- Available metrics:
  - TextCharactersTranslated: Total characters translated (standard translation)
  - TextCustomCharactersTranslated: Characters translated using custom models
  - SuccessfulCalls: Number of successful API calls
  - TotalCalls: Total API calls (successful + failed)
  - TotalErrors: Number of failed API calls
  - ClientErrors: Number of client-side errors (HTTP 4xx)
  - ServerErrors: Number of server-side errors (HTTP 5xx)
  - BlockedCalls: Number of calls blocked due to rate/quota limits
  - Latency: Average request latency in milliseconds
- View daily/monthly character counts and API call statistics
- Note: "CharactersTranslated" metric is deprecated (removed Oct 2022), use "TextCharactersTranslated" instead

## Step 3: Configure the Project

### Option A: Update config.yaml (Recommended)

Edit `translator/config.yaml` and add Azure Translator configuration:

    # Translation configuration
    translation:
      provider: azure  # Change from 'libretranslate' to 'azure'
      source_language: fi
      target_languages:
        - en
        - sv
        - es
        - de
        - zh

    # Azure Translator API settings
    azure:
      subscription_key: YOUR_API_KEY_HERE  # Paste your KEY 1 or KEY 2
      endpoint: https://api.cognitive.microsofttranslator.com/  # Your endpoint URL
      region: westeurope  # Your resource region (e.g., westeurope, eastus)
      timeout: 30
      max_retries: 3
      retry_delay: 2

### Option B: Use Environment Variables (More Secure)

For better security, use environment variables instead of storing keys in config files:

1. Set environment variables (in your shell or `.env` file):
    export AZURE_TRANSLATOR_KEY="your-api-key-here"
    export AZURE_TRANSLATOR_ENDPOINT="https://api.cognitive.microsofttranslator.com/"
    export AZURE_TRANSLATOR_REGION="westeurope"

2. Update config.yaml to reference environment variables:
    azure:
      subscription_key: ${AZURE_TRANSLATOR_KEY}  # Will read from environment
      endpoint: ${AZURE_TRANSLATOR_ENDPOINT}
      region: ${AZURE_TRANSLATOR_REGION}

   Note: You may need to update the code to support environment variable substitution, or use a library like `python-dotenv`.

### Option C: Use .env file (Recommended for local development)

1. Create a `.env` file in the project root (add it to `.gitignore`):
    AZURE_TRANSLATOR_KEY=your-api-key-here
    AZURE_TRANSLATOR_ENDPOINT=https://api.cognitive.microsofttranslator.com/
    AZURE_TRANSLATOR_REGION=westeurope

2. Load environment variables from .env file

   Method 1: Using `source` command (bash/zsh)
    # Load all variables from .env file
    set -a  # automatically export all variables
    source .env
    set +a  # stop automatically exporting
    
    # Verify variables are loaded
    echo $AZURE_TRANSLATOR_KEY
    echo $AZURE_TRANSLATOR_REGION

   Method 2: Using `export` with `grep` (one-liner)
    # Export all variables from .env file
    export $(grep -v '^#' .env | xargs)
    
    # Verify
    env | grep AZURE_TRANSLATOR

   Method 3: Using `python-dotenv` in Python code
    from dotenv import load_dotenv
    import os
    
    # Load .env file from project root
    load_dotenv()
    
    # Access variables
    azure_key = os.getenv('AZURE_TRANSLATOR_KEY')
    azure_endpoint = os.getenv('AZURE_TRANSLATOR_ENDPOINT')
    azure_region = os.getenv('AZURE_TRANSLATOR_REGION')

   Method 4: Using `dotenv-cli` (npm package)
    # Install dotenv-cli (if you have Node.js)
    npm install -g dotenv-cli
    
    # Run commands with .env variables loaded
    dotenv python translator/translate_news.py --input path/to/articles.html

   Method 5: Create a helper script to load .env
    # Create load-env.sh
    #!/bin/bash
    if [ -f .env ]; then
        export $(cat .env | grep -v '^#' | xargs)
    fi
    
    # Make it executable
    chmod +x load-env.sh
    
    # Use it
    source load-env.sh
    python translator/translate_news.py --input path/to/articles.html

3. Verify .env is in .gitignore
    # Check if .env is ignored
    git check-ignore .env
    
    # If not, add it to .gitignore
    echo ".env" >> .gitignore

## Step 4: Language Codes

Azure Translator uses specific language codes. Here are common ones:

| Language | Azure Code | Notes |
|----------|------------|-------|
| Finnish | `fi` | Source language |
| English | `en` | |
| Swedish | `sv` | |
| Spanish | `es` | |
| German | `de` | |
| Chinese (Simplified) | `zh-Hans` | Not just `zh` |
| Chinese (Traditional) | `zh-Hant` | |
| French | `fr` | |
| Russian | `ru` | |
| Japanese | `ja` | |

Important: Azure Translator may use different language codes than LibreTranslate. For example:
- Chinese Simplified: Use `zh-Hans` instead of `zh`
- Chinese Traditional: Use `zh-Hant`

You can find the full list of supported languages at:
https://docs.microsoft.com/azure/cognitive-services/translator/language-support

## Step 5: Pricing Information

### Free Tier (F0)
- 2 million characters per month free
- After that, you pay per character
- Good for testing and small projects

### Standard Tier (S1)
- Pay-as-you-go pricing
- Current pricing (as of 2024): ~$10 per million characters
- Check current pricing: https://azure.microsoft.com/pricing/details/cognitive-services/translator/

### Cost Estimation
- Average news article: ~2,000-5,000 characters
- 2 million characters ≈ 400-1,000 articles per month (free tier)
- Note: Translating to multiple languages multiplies character count
  - Example: 1 article (3,000 chars) × 4 languages = 12,000 characters billed
- Monitor usage:
  - Check Azure Portal → Your Translator resource → Metrics
  - View translation statistics log file: `articles_translated_stats.txt` (created after each run)
  - Use Azure CLI commands in "View Billing Information" section

## Step 6: Security Best Practices

1. Never commit API keys to version control
   - Add `config.yaml` to `.gitignore` if it contains keys
   - Or use environment variables / `.env` files (which should be in `.gitignore`)

2. Rotate keys regularly
   - Azure provides KEY 1 and KEY 2 for this purpose
   - If one key is compromised, regenerate it:
     - Azure CLI: `az cognitiveservices account keys regenerate --name <resource-name> --resource-group <rg-name> --key-name key1`
     - Azure Portal: Go to Keys and Endpoint → Regenerate Key

3. Use Azure Key Vault (for production)
   - Store keys in Azure Key Vault
   - Access them programmatically with proper authentication

4. Set up usage alerts
   - In Azure Portal → Your Translator resource → Alerts
   - Set alerts for cost thresholds

5. Restrict access
   - Use Azure Resource Manager to restrict who can access the resource
   - Consider using managed identities for Azure services

## Step 6.5: Translation Statistics Log

After each translation run, a statistics log file is automatically created:
- File name: `articles_translated_stats.txt` (in the same directory as the translated HTML)
- Contains:
  - Characters translated via API vs retrieved from cache
  - Words translated (approximate count)
  - Number of API calls made
  - Number of cache hits
  - Cache hit rate percentage

Example log file:
    Translation Statistics
    ==================================================
    Provider: azure
    
    Characters:
      Translated via API: 45,230
      Retrieved from cache: 12,450
      Total: 57,680
    
    Words (approximate):
      Translated via API: 7,542
      Retrieved from cache: 2,075
      Total: 9,617
    
    API Calls: 126
    Cache Hits: 34
    Cache Hit Rate: 21.6%

This helps you:
- Track usage to stay within free tier (2M characters/month)
- Monitor API costs
- See cache effectiveness
- Estimate future translation costs

## Step 7: Testing Your Setup

Once configured, test your setup:

    # Run the translator with Azure provider
    python translator/translate_news.py \
      --translator azure \
      --languages en sv es \
      --input path/to/articles.html

Or if you've updated `config.yaml`:
    python translator/translate_news.py --input path/to/articles.html

## Troubleshooting

### Error: "Invalid subscription key"
- Verify your API key is correct
- Check that you copied the entire key (no extra spaces)
- Ensure you're using KEY 1 or KEY 2 from the correct resource

### Error: "Invalid region"
- Verify the region name matches your resource region
- Common regions: `westeurope`, `eastus`, `southeastasia`
- Check your resource's "Keys and Endpoint" page for the exact region name

### Error: "Quota exceeded"
- You've exceeded your free tier limit (2M characters/month)
- Wait for the next billing cycle, or upgrade to Standard tier
- Check usage in Azure Portal → Metrics

### Error: "Language not supported"
- Verify the language code is correct for Azure Translator
- Some codes differ from LibreTranslate (e.g., `zh-Hans` vs `zh`)
- Check supported languages: https://docs.microsoft.com/azure/cognitive-services/translator/language-support

### Rate Limiting
- Azure Translator has rate limits based on your tier
- Free tier: ~5 requests/second
- If you hit rate limits, the code should automatically retry with delays

## Additional Resources

- Azure Translator Documentation: https://docs.microsoft.com/azure/cognitive-services/translator/
- REST API Reference: https://docs.microsoft.com/azure/cognitive-services/translator/reference/v3-0-translate
- Language Support: https://docs.microsoft.com/azure/cognitive-services/translator/language-support
- Pricing: https://azure.microsoft.com/pricing/details/cognitive-services/translator/
- Azure Portal: https://portal.azure.com
- Azure CLI Documentation: https://docs.microsoft.com/cli/azure/cognitiveservices/account
- Azure CLI Install: https://docs.microsoft.com/cli/azure/install-azure-cli

## Next Steps

After setting up Azure Translator:

1. Implement the Azure translator class (if not already done)
   - Create `translator/translators/azure.py`
   - Implement `AzureTranslator` class extending `BaseTranslator`
   - Use Azure Translator REST API v3.0

2. Update translate_news.py
   - Add support for `azure` provider in the main function
   - Import and initialize `AzureTranslator` when provider is `azure`

3. Test with a small sample
   - Start with a single article
   - Verify translations are accurate
   - Check Azure Portal metrics to see usage

4. Monitor costs
   - Set up cost alerts in Azure Portal
   - Track usage in the Metrics section
   - Review billing regularly
   - Use the billing commands in View Billing Information section to check usage via CLI

---

Note: This guide assumes you'll need to implement the Azure translator integration code separately. The configuration and setup steps above will prepare your Azure account and provide the necessary credentials.
