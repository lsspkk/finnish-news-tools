# News Article Translator

Translates HTML news articles using LibreTranslate or Azure Translator API.

## Key Features

- Supports LibreTranslate and Azure Translator providers
- Default languages: `sv es de zh` (Swedish, Spanish, German, Chinese)
- Auto-finds newest `articles.html` in `responses/` directory
- Service-specific cache: `cache/libretranslate/` and `cache/azure/` with per-language-pair JSON files
- Cache enabled by default if cache files exist (disable with `--no-cache`)
- Generates translation statistics log: `{output}_stats.txt` with API usage, cache hits, character counts

## Configuration

Edit `translator/config.yaml`:

    translation:
      provider: libretranslate  # or 'azure'
      target_languages: [sv, es, de, zh]

    azure:
      subscription_key: YOUR_KEY  # Or use .env: AZURE_TRANSLATOR_KEY1
      region: westeurope # Or use .env: AZURE_TRANSLATOR_REGION

## Usage

    python translator/translate_news.py [--translator azure] [--languages en sv] [--no-cache]

Options override config.yaml. Default input: newest folder in `responses/` containing `articles.html`.

## Important Notes

- Azure language codes differ: use `zh-Hans` not `zh` for Chinese Simplified
- Cache structure: `cache/{provider}/translations_{source}_{target}.json` (MD5 hash keys)
- See [azure-translator-setup.md](azure-translator-setup.md) for Azure setup details
