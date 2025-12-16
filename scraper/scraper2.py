#!/usr/bin/env python3
"""
scraper2.py - Scrapes a page, extracts links, and downloads them
"""
import sys
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

# Constants
DEFAULT_URL = "https://yle.fi/uutiset"
RESPONSES_DIR = "responses"
DOWNLOADS_DIR = "downloads"
ARTICLES_DIR = "articles"
TIMEOUT_MAIN = 120000
TIMEOUT_LINK = 30000
FILENAME_MAX_LENGTH = 200
DEFAULT_MIME = "application-octet-stream"
# Only capture text-based content types
TEXT_CONTENT_TYPES = ['text/html', 'text/plain', 'application/json', 'text/xml', 'application/xml']
# Pattern for article links
ARTICLE_LINK_TEXT = "Avaa koko juttu"
MIME_TO_EXT = {
    'text/html': '.html',
    'application/json': '.json',
    'text/javascript': '.js',
    'application/javascript': '.js',
    'text/css': '.css',
    'text/plain': '.txt',
    'application/xml': '.xml',
    'text/xml': '.xml',
    'image/png': '.png',
    'image/jpeg': '.jpg',
    'image/jpg': '.jpg',
    'image/gif': '.gif',
    'image/svg+xml': '.svg',
    'application/pdf': '.pdf',
}
URL_EXTENSIONS = list(set(MIME_TO_EXT.values()))

def get_mime_type_string(content_type):
    """Convert content-type to filename-safe string like 'text-html'"""
    if not content_type:
        return DEFAULT_MIME
    mime_type = content_type.split(';')[0].strip().lower()
    return mime_type.replace('/', '-')

def get_file_extension(content_type, url=""):
    """Get appropriate file extension from content type or URL"""
    if not content_type:
        content_type = ""
    
    content_type_lower = content_type.lower()
    
    mime_base = content_type_lower.split(';')[0].strip()
    if mime_base in MIME_TO_EXT:
        return MIME_TO_EXT[mime_base]
    
    if url:
        url_lower = url.lower()
        for ext in URL_EXTENSIONS:
            if url_lower.endswith(ext):
                return ext
    
    if 'json' in content_type_lower:
        return '.json'
    elif 'javascript' in content_type_lower or 'js' in content_type_lower:
        return '.js'
    elif 'html' in content_type_lower:
        return '.html'
    elif 'css' in content_type_lower:
        return '.css'
    elif 'xml' in content_type_lower:
        return '.xml'
    else:
        return '.bin'

def sanitize_filename(filename):
    """Make filename safe for filesystem"""
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Limit length
    if len(filename) > FILENAME_MAX_LENGTH:
        filename = filename[:FILENAME_MAX_LENGTH]
    return filename

def main():
    print("Starting scraper2...", flush=True)
    
    # Search text is optional
    search_text_str = sys.argv[1] if len(sys.argv) >= 2 else ""
    url_to_open = DEFAULT_URL
    
    if search_text_str:
        print(f"Search text: {search_text_str}", flush=True)
    else:
        print("No search text provided - capturing all responses", flush=True)
    print(f"URL: {url_to_open}", flush=True)
    
    # Create responses directory with timestamp subfolder
    os.makedirs(RESPONSES_DIR, exist_ok=True)
    run_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    responses_dir = os.path.join(RESPONSES_DIR, run_timestamp)
    os.makedirs(responses_dir, exist_ok=True)
    
    # Create downloads subdirectory for linked files
    downloads_dir = os.path.join(responses_dir, DOWNLOADS_DIR)
    os.makedirs(downloads_dir, exist_ok=True)
    
    # Create articles subdirectory for article pages
    articles_dir = os.path.join(responses_dir, ARTICLES_DIR)
    os.makedirs(articles_dir, exist_ok=True)
    
    print(f"Responses will be saved to: {responses_dir}/", flush=True)
    print(f"Articles will be saved to: {articles_dir}/", flush=True)
    
    search_text = search_text_str.encode("utf-8") if search_text_str else b""
    all_links = []
    main_html_content = None
    
    with sync_playwright() as p:
        print("Launching browser...", flush=True)
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        print("Browser launched, setting up response listener...", flush=True)
        
        responses = []
        response_counter = 0
        
        def on_response(response):
            nonlocal response_counter, main_html_content
            content_type = response.headers.get("content-type", "")
            content_type_lower = content_type.lower()
            
            # Only capture text-based responses (HTML, JSON, XML, plain text)
            # Skip JS, CSS, images, fonts, etc.
            is_text_content = any(text_type in content_type_lower for text_type in TEXT_CONTENT_TYPES)
            if not is_text_content:
                return  # Skip non-text responses
            
            try:
                body = response.body()
            except Exception:
                body = b""
            
            has_text = search_text in body if search_text else True
            
            # Store main page HTML for link extraction
            if response.url == url_to_open and 'text/html' in content_type_lower:
                try:
                    main_html_content = body.decode('utf-8', errors='replace')
                except:
                    pass
            
            is_json = "json" in content_type_lower or response.url.endswith(".json")
            is_api = "api" in response.url.lower() or "/v1/" in response.url or "/v2/" in response.url
            
            response_counter += 1
            responses.append({
                "counter": response_counter,
                "url": response.url,
                "status": response.status,
                "resource_type": response.request.resource_type,
                "has_text": has_text,
                "content_type": content_type,
                "is_json": is_json,
                "is_api": is_api,
                "body": body,
            })
        
        page.on("response", on_response)
        print("Loading page...", flush=True)
        page.goto(url_to_open, wait_until="networkidle", timeout=TIMEOUT_MAIN)
        print(f"Page loaded. Captured {len(responses)} responses.", flush=True)
        
        # Save all responses
        print(f"Saving {len(responses)} responses to files...", flush=True)
        for r in responses:
            mime_type_str = get_mime_type_string(r['content_type'])
            extension = get_file_extension(r['content_type'], r['url'])
            filename = f"{r['counter']:03d}-{mime_type_str}{extension}"
            filepath = os.path.join(responses_dir, filename)
            
            try:
                with open(filepath, "wb") as f:
                    f.write(r["body"])
                
                metadata_path = filepath + ".meta"
                with open(metadata_path, "w", encoding="utf-8") as f:
                    f.write(f"URL: {r['url']}\n")
                    f.write(f"Status: {r['status']}\n")
                    f.write(f"Resource Type: {r['resource_type']}\n")
                    f.write(f"Content Type: {r['content_type']}\n")
                    f.write(f"Has Search Text: {r['has_text']}\n")
                    f.write(f"Is JSON: {r['is_json']}\n")
                    f.write(f"Is API: {r['is_api']}\n")
            except Exception as e:
                print(f"Error saving response {filename}: {e}", flush=True)
        
        # Extract links from main HTML using Beautiful Soup
        if main_html_content:
            print("\nExtracting links from main page...", flush=True)
            soup = BeautifulSoup(main_html_content, 'html.parser')
            
            # Find all links (you can customize selectors here)
            # Example: find all <a> tags with href
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                if href:
                    # Convert relative URLs to absolute
                    absolute_url = urljoin(url_to_open, href)
                    link_text = link.get_text(strip=True)
                    all_links.append({
                        'url': absolute_url,
                        'text': link_text,
                        'href': href
                    })
            
            # You can also find other types of links, e.g., <link> tags for CSS, etc.
            for link_tag in soup.find_all('link', href=True):
                href = link_tag.get('href')
                if href:
                    absolute_url = urljoin(url_to_open, href)
                    rel = link_tag.get('rel', [''])[0] if link_tag.get('rel') else ''
                    all_links.append({
                        'url': absolute_url,
                        'text': f"Link ({rel})",
                        'href': href
                    })
            
            print(f"Found {len(all_links)} links", flush=True)
            
            # Filter for "Avaa koko juttu" links
            article_links = []
            for link in all_links:
                if ARTICLE_LINK_TEXT in link.get('text', ''):
                    href = link.get('href', '')
                    # Extract shortcode from href (e.g., /a/74-20199909 -> 74-20199909)
                    if '/a/' in href:
                        shortcode = href.split('/a/')[-1].rstrip('/')
                        article_links.append({
                            'url': link['url'],
                            'shortcode': shortcode,
                            'href': href
                        })
            
            print(f"Found {len(article_links)} article links to download", flush=True)
            
            # Download article pages
            if article_links:
                print(f"\nDownloading article pages...", flush=True)
                download_counter = 0
                
                for article_link in article_links:
                    link_url = article_link['url']
                    shortcode = article_link['shortcode']
                    
                    try:
                        print(f"  Downloading: {link_url[:80]}...", flush=True)
                        link_page = browser.new_page()
                        link_response = link_page.goto(link_url, wait_until="networkidle", timeout=TIMEOUT_LINK)
                        
                        if link_response:
                            body = link_response.body()
                            content_type = link_response.headers.get("content-type", "")
                            
                            # Generate filename: 001-<shortcode>.html
                            download_counter += 1
                            filename = f"{download_counter:03d}-{shortcode}.html"
                            filepath = os.path.join(articles_dir, filename)
                            
                            with open(filepath, "wb") as f:
                                f.write(body)
                            
                            # Save metadata
                            metadata_path = filepath + ".meta"
                            with open(metadata_path, "w", encoding="utf-8") as f:
                                f.write(f"URL: {link_url}\n")
                                f.write(f"Shortcode: {shortcode}\n")
                                f.write(f"Status: {link_response.status}\n")
                                f.write(f"Content Type: {content_type}\n")
                        
                        link_page.close()
                        
                    except Exception as e:
                        print(f"  Error downloading {link_url}: {e}", flush=True)
                        try:
                            link_page.close()
                        except:
                            pass
                
                print(f"Downloaded {download_counter} article pages to {articles_dir}/", flush=True)
        
        browser.close()
    
    print(f"\nScraping complete!")
    print(f"Responses saved to: {responses_dir}/")
    if main_html_content and all_links:
        article_count = len([l for l in all_links if ARTICLE_LINK_TEXT in l.get('text', '')])
        if article_count > 0:
            print(f"Downloaded {article_count} article pages to {articles_dir}/")

if __name__ == "__main__":
    main()

