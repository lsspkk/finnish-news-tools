# News Article Translator

A Python tool for translating HTML news articles to multiple languages using LibreTranslate API.

## Features

- Translate Finnish news articles to English and Swedish
- Support for LibreTranslate API (free and open-source)
- Translation caching to avoid re-translation
- Interactive language switching in output HTML
- Configurable via YAML
- Error handling and retry logic for API calls
- Progress reporting during translation

## Installation

1. Clone the repository and navigate to the translator directory:

```bash
cd translator
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

Edit `config.yaml` to customize translation settings:

```yaml
# Translation settings
translation:
  provider: libretranslate
  source_language: fi
  target_languages:
    - en
    - sv

# LibreTranslate API settings
libretranslate:
  api_url: https://libretranslate.com/translate
  api_key: null  # Optional - set if using API key
  timeout: 30
  max_retries: 3
  retry_delay: 2

# Cache settings
cache:
  enabled: true
  file: cache/translations.json

# Output settings
output:
  add_language_controls: true
  default_language: fi
```

### LibreTranslate Setup

#### Using Public API

The default configuration uses the public LibreTranslate API at `https://libretranslate.com/translate`. This is free to use but:
- Has rate limits
- Sends your data to external servers
- May be slower during high traffic

#### Using API Key

You can get an API key from LibreTranslate for higher rate limits:

1. Visit https://libretranslate.com
2. Get an API key
3. Add it to `config.yaml`:

```yaml
libretranslate:
  api_key: your-api-key-here
```

#### Self-Hosting LibreTranslate

For better privacy and control, you can self-host LibreTranslate:

1. Install LibreTranslate:

```bash
pip install libretranslate
```

2. Run the server:

```bash
libretranslate --host 0.0.0.0 --port 5000
```

3. Update `config.yaml`:

```yaml
libretranslate:
  api_url: http://localhost:5000/translate
  api_key: null
```

## Usage

### Basic Usage

Translate the sample articles:

```bash
python translate_news.py
```

This will:
- Read from `examples/sample_articles.html`
- Translate to English and Swedish
- Save output to `examples/translated_articles.html`

### Custom Input/Output

Specify custom files:

```bash
python translate_news.py --input path/to/articles.html --output path/to/output.html
```

### Custom Configuration

Use a different config file:

```bash
python translate_news.py --config custom_config.yaml
```

### All Options

```bash
python translate_news.py --help
```

Options:
- `--input`, `-i`: Input HTML file path (default: examples/sample_articles.html)
- `--output`, `-o`: Output HTML file path (default: examples/translated_articles.html)
- `--config`, `-c`: Configuration file path (default: config.yaml)

## Output Format

The script generates HTML with:

1. **Language toggle buttons** for each paragraph
2. **Hidden translations** that can be shown/hidden
3. **CSS styling** for buttons and transitions
4. **JavaScript** for interactive language switching

Example output structure:

```html
<div class="article-paragraph">
    <p data-lang="fi">Alkuperäinen teksti suomeksi</p>
    <p data-lang="en" class="hidden">Original text in English</p>
    <p data-lang="sv" class="hidden">Originaltext på svenska</p>
    
    <div class="translation-controls">
        <button class="active" onclick="showLang(this, 'fi')">Suomi</button>
        <button onclick="showLang(this, 'en')">English</button>
        <button onclick="showLang(this, 'sv')">Svenska</button>
    </div>
</div>
```

## Translation Cache

Translations are cached in `cache/translations.json` to:
- Avoid re-translating the same text
- Speed up subsequent runs
- Save API calls and costs

The cache uses MD5 hashes of the original text as keys:

```json
{
  "5d41402abc4b2a76b9719d911017c592": {
    "en": "Translation in English",
    "sv": "Translation in Swedish"
  }
}
```

To clear the cache, delete or empty `cache/translations.json`.

## Error Handling

The script handles various errors gracefully:

- **Network errors**: Retries with exponential backoff
- **Rate limiting**: Automatic retry with increased delay
- **API errors**: Returns original text and continues
- **Timeout errors**: Retries up to max_retries times

## Limitations

- Only translates `<p>` tags in `<section>` elements within `<article>` tags
- Does not translate headings, links, or other HTML elements
- Translation quality depends on the LibreTranslate API/model
- Public API has rate limits

## Troubleshooting

### Rate Limiting

If you see rate limit errors:
1. Increase `retry_delay` in config.yaml
2. Get an API key for higher limits
3. Self-host LibreTranslate

### Poor Translation Quality

- Try a different translation provider (requires code changes)
- Use a self-hosted LibreTranslate instance with better models
- Consider using DeepL or Google Translate APIs (requires implementation)

### Slow Performance

- Translations are cached after first run
- Use a self-hosted LibreTranslate instance
- Reduce number of target languages

## Development

### Project Structure

```
translator/
├── translate_news.py           # Main script
├── config.yaml                 # Configuration file
├── requirements.txt            # Python dependencies
├── README.md                   # This file
├── translators/
│   ├── __init__.py
│   ├── base.py                 # Abstract translator interface
│   └── libretranslate.py       # LibreTranslate implementation
├── cache/
│   └── translations.json       # Translation cache
└── examples/
    ├── sample_articles.html    # Sample input
    └── translated_articles.html # Sample output (generated)
```

### Adding New Translation Providers

To add a new provider:

1. Create a new file in `translators/` (e.g., `deepl.py`)
2. Implement the `BaseTranslator` interface
3. Update `translate_news.py` to support the new provider
4. Add configuration options to `config.yaml`

Example:

```python
from .base import BaseTranslator

class DeepLTranslator(BaseTranslator):
    def translate(self, text: str, target_lang: str) -> str:
        # Implementation here
        pass
```

## License

See the main repository LICENSE file.

## Contributing

Contributions are welcome! Please follow the existing code style and add tests for new features.
