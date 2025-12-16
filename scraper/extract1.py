#!/usr/bin/env python3
import os
import sys
import json
from pathlib import Path
from bs4 import BeautifulSoup

# Constants
DEFAULT_RESPONSES_DIR = "responses"
SKIP_CONTENT_TYPES = ['javascript', 'application/javascript', 'image/', 'font/', 'video/', 'audio/', 'application/octet-stream', 'text/css']
PRIORITY_SEARCH_TEXT = 10
PRIORITY_API_JSON = 5

def extract_text_from_html(content):
    """Extract text from HTML content using Beautiful Soup"""
    try:
        soup = BeautifulSoup(content, 'html.parser')
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        # Get text and clean it up
        text = soup.get_text(separator=' ', strip=True)
        # Collapse multiple whitespace
        import re
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    except Exception as e:
        print(f"Error parsing HTML: {e}", file=sys.stderr)
        return ""

def extract_text_from_json(content):
    """Extract text from JSON content"""
    try:
        data = json.loads(content)
        # Recursively extract all string values
        texts = []
        
        def extract_strings(obj):
            if isinstance(obj, dict):
                for value in obj.values():
                    extract_strings(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract_strings(item)
            elif isinstance(obj, str):
                if obj.strip():
                    texts.append(obj)
        
        extract_strings(data)
        return ' '.join(texts)
    except Exception as e:
        print(f"Error parsing JSON: {e}", file=sys.stderr)
        return ""

def read_metadata(filepath):
    """Read metadata from .meta file"""
    meta_path = filepath + '.meta'
    metadata = {}
    if os.path.exists(meta_path):
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        metadata[key.strip()] = value.strip()
        except Exception as e:
            print(f"Error reading metadata {meta_path}: {e}", file=sys.stderr)
    return metadata

def should_skip_file(metadata):
    """Check if file should be skipped based on content type"""
    content_type = metadata.get('Content Type', '').lower()
    
    # Skip files matching skip patterns
    if any(skip_type in content_type for skip_type in SKIP_CONTENT_TYPES):
        return True
    
    return False

def extract_text_from_file(filepath, metadata=None):
    """Extract text from a file based on its content"""
    try:
        with open(filepath, 'rb') as f:
            content_bytes = f.read()
        
        # Try to decode as UTF-8
        try:
            content = content_bytes.decode('utf-8', errors='replace')
        except:
            # Fallback to latin-1
            content = content_bytes.decode('latin-1', errors='replace')
        
        # Check if it's JSON
        content_stripped = content.strip()
        if content_stripped.startswith('{') or content_stripped.startswith('['):
            text = extract_text_from_json(content)
            if text:
                return text
        
        # Check if it's HTML
        if '<html' in content.lower() or '<!doctype' in content.lower() or content.strip().startswith('<'):
            text = extract_text_from_html(content)
            if text:
                return text
        
        # Otherwise, return as plain text (filter out binary/non-printable)
        # Keep only printable characters and common whitespace
        printable_text = ''.join(c if c.isprintable() or c in '\n\r\t ' else ' ' for c in content)
        # Collapse multiple whitespace
        import re
        printable_text = re.sub(r'\s+', ' ', printable_text)
        return printable_text.strip()
    
    except Exception as e:
        print(f"Error reading file {filepath}: {e}", file=sys.stderr)
        return ""

def main():
    # Default to 'responses' directory, but allow override
    input_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_RESPONSES_DIR
    
    if not os.path.exists(input_path):
        print(f"Error: Path '{input_path}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    # If the path is a file, use its directory
    if os.path.isfile(input_path):
        responses_dir = os.path.dirname(input_path)
    else:
        responses_dir = input_path
    
    # If this is the base "responses" directory, find and use the most recent subfolder
    # Otherwise, use the provided path as-is (could be a specific subfolder)
    if os.path.basename(responses_dir) == DEFAULT_RESPONSES_DIR and os.path.isdir(responses_dir):
        subdirs = [d for d in os.listdir(responses_dir) 
                   if os.path.isdir(os.path.join(responses_dir, d)) and not d.startswith('.')]
        if subdirs:
            # Sort subdirs (timestamp format yyyy-mm-ddThh-mm-ss allows string sorting)
            subdirs.sort(reverse=True)
            most_recent = subdirs[0]
            responses_dir = os.path.join(responses_dir, most_recent)
            print(f"Using most recent subfolder: {most_recent}", file=sys.stderr)
        else:
            print(f"No subfolders found in {responses_dir}", file=sys.stderr)
    
    print(f"Reading responses from: {responses_dir}/", file=sys.stderr)
    print(f"{'='*80}", file=sys.stderr)
    
    # Get all files in the directory (excluding .meta files)
    response_files = []
    for filename in sorted(os.listdir(responses_dir)):
        filepath = os.path.join(responses_dir, filename)
        if os.path.isfile(filepath) and not filename.endswith('.meta'):
            response_files.append(filepath)
    
    print(f"Found {len(response_files)} response files", file=sys.stderr)
    print(f"{'='*80}\n", file=sys.stderr)
    
    # Extract and print text from each file
    files_with_text = []
    for filepath in response_files:
        filename = os.path.basename(filepath)
        metadata = read_metadata(filepath)
        
        # Skip JavaScript and binary files
        if should_skip_file(metadata):
            continue
        
        text = extract_text_from_file(filepath, metadata)
        
        if text.strip():
            # Prioritize files with search text or API/JSON responses
            priority = 0
            if metadata.get('Has Search Text') == 'True':
                priority += PRIORITY_SEARCH_TEXT
            if metadata.get('Is JSON') == 'True' or metadata.get('Is API') == 'True':
                priority += PRIORITY_API_JSON
            
            files_with_text.append({
                'filepath': filepath,
                'filename': filename,
                'text': text,
                'metadata': metadata,
                'priority': priority
            })
    
    # Sort by priority (highest first), then by filename
    files_with_text.sort(key=lambda x: (-x['priority'], x['filename']))
    
    # Print all text
    for item in files_with_text:
        print(f"\n{'='*80}")
        print(f"File: {item['filename']}")
        if item['metadata'].get('URL'):
            print(f"URL: {item['metadata']['URL']}")
        if item['metadata'].get('Content Type'):
            print(f"Content Type: {item['metadata']['Content Type']}")
        print(f"{'='*80}")
        print(item['text'])
        print()

if __name__ == "__main__":
    main()


