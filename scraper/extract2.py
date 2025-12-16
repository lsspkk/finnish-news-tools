#!/usr/bin/env python3
"""
extract2.py - Extracts articles from scraped HTML into a cleaner, shorter format
"""
import os
import sys
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from jinja2 import Template

# Constants
DEFAULT_RESPONSES_DIR = "responses"
BASE_URL = "https://yle.fi"

def extract_full_article_from_file(article_file_path):
    """Extract full article content from a downloaded article HTML file"""
    try:
        with open(article_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find main tag
        main_tag = soup.find('main')
        if not main_tag:
            return None
        
        article_data = {}
        
        # Extract header with title
        header = main_tag.find('header', class_=lambda x: x and 'yle__article__header' in x)
        if header:
            h1 = header.find('h1', class_=lambda x: x and 'yle__article__heading' in x)
            if h1:
                article_data['full_title'] = h1.get_text(strip=True)
        
        # Extract section with paragraphs
        section = main_tag.find('section', class_=lambda x: x and 'yle__article__content' in x)
        if section:
            # Get all paragraph elements
            paragraphs = section.find_all('p', class_=lambda x: x and 'yle__article__paragraph' in x)
            # Store both text and HTML for each paragraph
            article_data['full_paragraphs'] = []
            for p in paragraphs:
                text = p.get_text(strip=True)
                if text:  # Only include non-empty paragraphs
                    article_data['full_paragraphs'].append(text)
        
        return article_data if article_data.get('full_paragraphs') else None
    except Exception as e:
        print(f"Warning: Could not extract article from {article_file_path}: {e}", file=sys.stderr)
        return None

def extract_articles_from_html(html_content, base_url=BASE_URL):
    """Extract articles from HTML and return simplified HTML"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find all article elements
    articles = soup.find_all('article', class_='yle__article')
    
    extracted_articles = []
    
    for article in articles:
        article_data = {}
        
        # Extract header (title)
        header = article.find('h1', class_=lambda x: x and 'yle__article__heading' in x)
        if header:
            article_data['title'] = header.get_text(strip=True)
        
        # Extract image and caption from figure
        figure = article.find('figure', class_=lambda x: x and 'yle__article__figure' in x)
        if figure:
            # Get image URL from script tag with JSON-LD
            script = figure.find('script', type='application/ld+json')
            image_url = None
            image_description = None
            if script:
                try:
                    import json
                    data = json.loads(script.string)
                    if 'image' in data and isinstance(data['image'], dict):
                        image_url = data['image'].get('url')
                        image_description = data['image'].get('description')
                except:
                    pass
            
            # Fallback: get image from img tag
            if not image_url:
                img = figure.find('img')
                if img:
                    image_url = img.get('src')
                    image_description = img.get('alt', '')
            
            # Get caption
            figcaption = figure.find('figcaption')
            caption_text = ""
            if figcaption:
                caption_text = figcaption.get_text(strip=True)
            
            article_data['image_url'] = image_url
            article_data['image_description'] = image_description or caption_text
            article_data['caption'] = caption_text
        
        # Extract article text
        content_section = article.find('section', class_=lambda x: x and 'yle__article__content' in x)
        if content_section:
            # Get all paragraphs
            paragraphs = content_section.find_all('p', class_=lambda x: x and 'yle__article__paragraph' in x)
            article_data['text'] = '\n\n'.join(p.get_text(strip=True) for p in paragraphs)
        
        # Extract "Avaa koko juttu" link
        full_article_link = content_section.find('a', string=lambda x: x and 'Avaa koko juttu' in x) if content_section else None
        if not full_article_link:
            # Try finding by href pattern
            full_article_link = article.find('a', href=lambda x: x and '/a/' in x)
        
        if full_article_link:
            href = full_article_link.get('href')
            article_data['full_article_url'] = urljoin(base_url, href)
            # Extract shortcode from URL (e.g., /a/74-20199909 -> 74-20199909)
            if '/a/' in href:
                article_data['shortcode'] = href.split('/a/')[-1].rstrip('/')
        
        extracted_articles.append(article_data)
    
    return extracted_articles

# Constants
TEMPLATE_FILE = "extract2-template.html"

def create_articles_html(articles, output_file):
    """Create simplified HTML file with all articles using Jinja2 template"""
    # Prepare articles data for template
    template_articles = []
    for article in articles:
        # Process image URL
        image_url_full = article.get('image_url', '')
        if image_url_full and not image_url_full.startswith('http'):
            image_url_full = urljoin(BASE_URL, image_url_full)
        elif not image_url_full:
            image_url_full = ''
        
        # Process text paragraphs
        text = article.get('text', '')
        paragraphs = []
        if text:
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        template_articles.append({
            'title': article.get('title', ''),
            'image_url': image_url_full,
            'image_description': article.get('image_description', ''),
            'caption': article.get('caption', ''),
            'text': text,  # Keep for conditional check
            'paragraphs': paragraphs,  # Pre-split paragraphs
            'full_article_url': article.get('full_article_url', ''),
            'shortcode': article.get('shortcode', ''),
            'full_title': article.get('full_title', ''),
            'full_paragraphs': article.get('full_paragraphs', [])
        })
    
    # Load and render template
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(script_dir, TEMPLATE_FILE)
    
    if not os.path.exists(template_path):
        print(f"Error: Template file not found: {template_path}", file=sys.stderr)
        sys.exit(1)
    
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()
    
    template = Template(template_content)
    html_output = template.render(
        articles=template_articles,
        base_url=BASE_URL
    )
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_output)

def main():
    # Default to latest responses folder
    input_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_RESPONSES_DIR
    
    if not os.path.exists(input_path):
        print(f"Error: Path '{input_path}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    # If the path is a file, use its directory
    if os.path.isfile(input_path):
        responses_dir = os.path.dirname(input_path)
        html_file = input_path
    else:
        responses_dir = input_path
        
        # If this is the base "responses" directory, find and use the most recent subfolder
        if os.path.basename(responses_dir) == DEFAULT_RESPONSES_DIR and os.path.isdir(responses_dir):
            subdirs = [d for d in os.listdir(responses_dir) 
                       if os.path.isdir(os.path.join(responses_dir, d)) and not d.startswith('.')]
            if subdirs:
                subdirs.sort(reverse=True)
                most_recent = subdirs[0]
                responses_dir = os.path.join(responses_dir, most_recent)
                print(f"Using most recent subfolder: {most_recent}", file=sys.stderr)
        
        # Find HTML file in directory (now in the correct subfolder if applicable)
        html_files = [f for f in os.listdir(responses_dir) 
                     if f.endswith('.html') and not f.endswith('.meta')]
        if not html_files:
            print(f"Error: No HTML file found in {responses_dir}", file=sys.stderr)
            sys.exit(1)
        html_file = os.path.join(responses_dir, sorted(html_files)[0])
    
    print(f"Reading HTML from: {html_file}", file=sys.stderr)
    
    # Read HTML file
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Extract articles
    articles = extract_articles_from_html(html_content)
    print(f"Found {len(articles)} articles", file=sys.stderr)
    
    # Try to load full article content from articles subfolder
    articles_dir = os.path.join(responses_dir, 'articles')
    if os.path.isdir(articles_dir):
        print(f"Loading full articles from: {articles_dir}", file=sys.stderr)
        # Create a mapping of shortcode to article file
        article_files = {}
        for filename in os.listdir(articles_dir):
            if filename.endswith('.html') and not filename.endswith('.meta'):
                # Extract shortcode from filename (e.g., "001-74-20199915.html" -> "74-20199915")
                parts = filename.replace('.html', '').split('-', 1)
                if len(parts) == 2:
                    shortcode = parts[1]
                    article_files[shortcode] = os.path.join(articles_dir, filename)
        
        # Match articles with their full content files
        for article in articles:
            shortcode = article.get('shortcode')
            if shortcode and shortcode in article_files:
                full_content = extract_full_article_from_file(article_files[shortcode])
                if full_content:
                    article['full_title'] = full_content.get('full_title', article.get('title', ''))
                    article['full_paragraphs'] = full_content.get('full_paragraphs', [])
                    print(f"Loaded full content for article: {shortcode}", file=sys.stderr)
    
    # Create output file
    output_file = os.path.join(responses_dir, 'articles.html')
    create_articles_html(articles, output_file)
    print(f"Created articles HTML: {output_file}", file=sys.stderr)

if __name__ == "__main__":
    main()

