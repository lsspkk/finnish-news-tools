# Translation System Plan

## Overview

This document outlines the architecture and implementation plan for a translation system designed to process HTML news articles from articles.html and generate multilingual versions with language toggle functionality. The system will support Finnish, English, and Swedish translations, allowing users to switch between languages seamlessly within the same document.

## Translation API Comparison

### Google Cloud Translation API

- Pros:
  - High quality neural machine translation
  - Supports 100+ languages
  - Good documentation and SDK support
  - Reliable and fast
- Cons:
  - Requires API key and billing account
  - Cost per character translated
  - Requires internet connection
  - Data sent to external service

### LibreTranslate

- Pros:
  - Open source and self-hostable
  - Free to use
  - Can run locally or on own server
  - No API key required for self-hosted
  - Privacy-friendly
- Cons:
  - Translation quality may vary
  - Requires more setup for self-hosting
  - Smaller model compared to commercial services
  - May need more computing resources for local hosting

### DeepL API

- Pros:
  - Excellent translation quality
  - Good support for European languages
  - Clean API
- Cons:
  - Requires API key and subscription
  - Limited free tier
  - Fewer supported languages than Google
  - Cost considerations

### Helsinki-NLP (Hugging Face Transformers)

- Pros:
  - Free and open source
  - Can run completely offline
  - Good quality for specific language pairs
  - No API keys or external dependencies
- Cons:
  - Requires local model downloads
  - Higher computational requirements
  - Setup complexity
  - Slower than API-based solutions

## Recommended Approach

Start with LibreTranslate as the primary translation engine:

- Begin with the public API endpoint at https://libretranslate.com for testing
- Easy to get started without API keys
- Option to self-host for production use
- Good balance between quality and ease of use
- Support architecture that allows switching to other providers later

## System Architecture

### Components

#### HTML Parser

- Parse input articles.html file
- Extract article structure (titles, paragraphs, captions)
- Identify translatable text elements
- Preserve HTML structure and styling

#### Translation Engine

- Interface for translation providers
- LibreTranslate implementation
- Request batching and rate limiting
- Error handling and retry logic
- Caching mechanism to avoid redundant translations

#### HTML Generator

- Generate multilingual HTML output
- Embed translations as data attributes
- Insert language toggle controls
- Preserve original styling and structure
- Generate JavaScript for language switching

#### Configuration Manager

- Load configuration from YAML file
- Manage API credentials
- Define source and target languages
- Control translation options

## File Structure

    translator/
      plan.md                    # This file
      config.yaml               # Configuration file
      translate.py              # Main translation script
      translator/
        __init__.py
        parser.py               # HTML parsing logic
        engine.py               # Translation engine interface
        libretranslate.py       # LibreTranslate implementation
        generator.py            # HTML generation
        config.py               # Configuration handling
      tests/
        test_parser.py
        test_engine.py
        test_generator.py
      examples/
        sample_articles.html    # Sample input
        sample_output.html      # Sample output

## Configuration Format

Example config.yaml:

    translation:
      provider: libretranslate
      source_language: fi
      target_languages:
        - en
        - sv
      
    libretranslate:
      api_url: https://libretranslate.com/translate
      api_key: null  # Optional for public instance
      timeout: 30
      
    input:
      file: ../scraper/responses/latest/articles.html
      
    output:
      file: ../scraper/responses/latest/articles_multilingual.html
      template: template_multilingual.html
      
    options:
      cache_translations: true
      cache_file: .translation_cache.json
      batch_size: 10
      preserve_html: true

## Script Workflow

### Step 1: Load Configuration

- Read config.yaml
- Validate settings
- Initialize translation provider

### Step 2: Parse Input HTML

- Load articles.html
- Extract article structure
- Identify all translatable text elements
- Build internal representation

### Step 3: Translate Content

- For each article:
  - Extract title
  - Extract paragraphs
  - Extract captions
- Batch translation requests
- Check cache for existing translations
- Send requests to translation API
- Handle errors and retries
- Store translations in cache

### Step 4: Generate Output HTML

- Create new HTML structure
- For each article:
  - Insert original content
  - Add translated content as data attributes
  - Add language toggle buttons
- Include JavaScript for language switching
- Write to output file

### Step 5: Verification

- Validate output HTML
- Check all translations are present
- Report statistics
- Log any errors

## HTML Output Structure

Each paragraph will contain multiple language versions:

    <div class="multilingual-paragraph" data-fi="Finnish text" data-en="English text" data-sv="Swedish text">
      <p class="lang-fi">Finnish text</p>
      <p class="lang-en" style="display:none;">English text</p>
      <p class="lang-sv" style="display:none;">Swedish text</p>
    </div>

Article structure with language controls:

    <article>
      <div class="language-selector">
        <button class="lang-btn active" data-lang="fi">Suomi</button>
        <button class="lang-btn" data-lang="en">English</button>
        <button class="lang-btn" data-lang="sv">Svenska</button>
      </div>
      
      <header>
        <h1 class="multilingual-title">
          <span class="lang-fi">Otsikko suomeksi</span>
          <span class="lang-en" style="display:none;">Title in English</span>
          <span class="lang-sv" style="display:none;">Titel på svenska</span>
        </h1>
      </header>
      
      <section>
        <!-- Multilingual paragraphs here -->
      </section>
    </article>

## JavaScript Language Toggle

    <script>
    let currentLanguage = 'fi';
    
    function switchLanguage(lang) {
      if (currentLanguage === lang) return;
      
      currentLanguage = lang;
      
      // Hide all language elements
      document.querySelectorAll('.lang-fi, .lang-en, .lang-sv').forEach(el => {
        el.style.display = 'none';
      });
      
      // Show selected language elements
      document.querySelectorAll('.lang-' + lang).forEach(el => {
        el.style.display = 'block';
      });
      
      // Update button states
      document.querySelectorAll('.lang-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.lang === lang) {
          btn.classList.add('active');
        }
      });
      
      // Store preference
      localStorage.setItem('preferred-language', lang);
    }
    
    // Initialize language buttons
    document.querySelectorAll('.lang-btn').forEach(btn => {
      btn.addEventListener('click', () => switchLanguage(btn.dataset.lang));
    });
    
    // Load saved preference
    const savedLang = localStorage.getItem('preferred-language');
    if (savedLang && ['fi', 'en', 'sv'].includes(savedLang)) {
      switchLanguage(savedLang);
    }
    </script>

CSS for language controls:

    .language-selector {
      margin: 20px 0;
      display: flex;
      gap: 10px;
    }
    
    .lang-btn {
      padding: 8px 16px;
      border: 2px solid #0066cc;
      background: white;
      color: #0066cc;
      border-radius: 4px;
      cursor: pointer;
      font-size: 14px;
      transition: all 0.3s;
    }
    
    .lang-btn:hover {
      background: #e6f2ff;
    }
    
    .lang-btn.active {
      background: #0066cc;
      color: white;
    }
    
    .multilingual-paragraph {
      margin: 10px 0;
    }

## Implementation Todo List

- [ ] Set up project structure
  - [ ] Create translator directory
  - [ ] Create subdirectories (translator, tests, examples)
  - [ ] Initialize Python package
  
- [ ] Implement configuration system
  - [ ] Create config.yaml schema
  - [ ] Implement config loader
  - [ ] Add validation
  
- [ ] Implement HTML parser
  - [ ] Parse article structure
  - [ ] Extract translatable elements
  - [ ] Handle edge cases (empty paragraphs, nested HTML)
  
- [ ] Implement translation engine
  - [ ] Create provider interface
  - [ ] Implement LibreTranslate client
  - [ ] Add caching mechanism
  - [ ] Implement retry logic
  
- [ ] Implement HTML generator
  - [ ] Create multilingual HTML template
  - [ ] Generate language toggle controls
  - [ ] Embed translations
  - [ ] Preserve original styling
  
- [ ] Create main script
  - [ ] Command-line interface
  - [ ] Workflow orchestration
  - [ ] Progress reporting
  - [ ] Error handling
  
- [ ] Add testing
  - [ ] Unit tests for parser
  - [ ] Unit tests for translation engine
  - [ ] Unit tests for generator
  - [ ] Integration tests
  
- [ ] Documentation
  - [ ] README for translator module
  - [ ] API documentation
  - [ ] Usage examples
  
- [ ] Optimization
  - [ ] Batch translation requests
  - [ ] Parallel processing
  - [ ] Memory efficiency

## CLI Usage Examples

Basic usage:

    python translate.py

With custom configuration:

    python translate.py --config custom_config.yaml

Specify input and output files:

    python translate.py --input articles.html --output multilingual.html

Use specific translation provider:

    python translate.py --provider deepl --api-key YOUR_KEY

Translate to specific languages only:

    python translate.py --languages en,sv

Dry run to preview:

    python translate.py --dry-run

Clear cache and retranslate:

    python translate.py --clear-cache

Verbose output:

    python translate.py --verbose

## Next Steps

1. Set up development environment
   - Install required dependencies (beautifulsoup4, requests, pyyaml, jinja2)
   - Set up virtual environment
   - Configure IDE/editor

2. Create initial implementation
   - Start with simple parser
   - Implement basic LibreTranslate integration
   - Create minimal HTML generator

3. Test with sample data
   - Use existing articles.html from scraper
   - Verify translations work correctly
   - Test language toggle functionality

4. Iterate and improve
   - Add error handling
   - Implement caching
   - Optimize performance
   - Add support for additional providers

5. Integration
   - Update scraper workflow to include translation
   - Add translation step to CI/CD if applicable
   - Document integration points

6. Future enhancements
   - Support for additional languages
   - Translation quality assessment
   - User feedback mechanism
   - Export to different formats (PDF, EPUB)
   - Translation memory system
