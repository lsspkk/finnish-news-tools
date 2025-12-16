import sys
import os
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright

# Constants
DEFAULT_URL = "https://yle.fi/uutiset"
# Get the project root (parent of scraper directory)
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
RESPONSES_DIR = str(PROJECT_ROOT / "responses")
TIMEOUT = 120000
DEFAULT_MIME = "application-octet-stream"
API_VERSION_PATTERNS = ["/v1/", "/v2/", "/v3/", "/v4/"]
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
    
    # Remove charset and other parameters, keep only type/subtype
    mime_type = content_type.split(';')[0].strip().lower()
    # Replace / with - for filename
    return mime_type.replace('/', '-')

def get_file_extension(content_type, url=""):
    """Get appropriate file extension from content type or URL"""
    if not content_type:
        content_type = ""
    
    content_type_lower = content_type.lower()
    
    # Check content type
    mime_base = content_type_lower.split(';')[0].strip()
    if mime_base in MIME_TO_EXT:
        return MIME_TO_EXT[mime_base]
    
    # Check URL extension as fallback
    if url:
        url_lower = url.lower()
        for ext in URL_EXTENSIONS:
            if url_lower.endswith(ext):
                return ext
    
    # Default based on content type pattern
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

def main():
    print("Starting script...", flush=True)
    
    # Search text is optional - default to empty string (capture all responses)
    search_text_str = sys.argv[1] if len(sys.argv) >= 2 else ""
    search_text = search_text_str.encode("utf-8")
    url_to_open = DEFAULT_URL
    
    if search_text_str:
        print(f"Search text: {search_text_str}", flush=True)
    else:
        print("No search text provided - capturing all responses", flush=True)
    print(f"URL: {url_to_open}", flush=True)
    
    # Create responses directory with timestamp subfolder
    os.makedirs(RESPONSES_DIR, exist_ok=True)
    
    # Generate timestamp-based folder name for this run (yyyy-mm-ddThh-mm-ss)
    run_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    responses_dir = os.path.join(RESPONSES_DIR, run_timestamp)
    os.makedirs(responses_dir, exist_ok=True)
    print(f"Responses will be saved to: {responses_dir}/", flush=True)

    with sync_playwright() as p:
        print("Launching browser...", flush=True)
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        print("Browser launched, setting up response listener...", flush=True)

        responses = []

        def on_response(response):
            try:
                body = response.body()
            except Exception:
                body = b""
            has_text = search_text in body
            
            # Get content type
            content_type = response.headers.get("content-type", "")
            
            # Check if it's a JSON API response
            is_json = "json" in content_type.lower() or response.url.endswith(".json")
            is_api = "api" in response.url.lower() or any(pattern in response.url for pattern in API_VERSION_PATTERNS)
            
            responses.append(
                {
                    "url": response.url,
                    "status": response.status,
                    "resource_type": response.request.resource_type,
                    "has_text": has_text,
                    "content_type": content_type,
                    "is_json": is_json,
                    "is_api": is_api,
                    "body": body,
                    "body_preview": body[:200] if body else b"",
                }
            )

        page.on("response", on_response)
        print("Loading page...", flush=True)
        page.goto(url_to_open, wait_until="networkidle", timeout=TIMEOUT)
        print(f"Page loaded. Captured {len(responses)} responses.", flush=True)
        
        # Save all responses to files
        print(f"Saving {len(responses)} responses to files...", flush=True)
        for counter, r in enumerate(responses, start=1):
            # Generate filename: counter-mimetype.extension
            mime_type_str = get_mime_type_string(r['content_type'])
            extension = get_file_extension(r['content_type'], r['url'])
            filename = f"{counter:03d}-{mime_type_str}{extension}"
            filepath = os.path.join(responses_dir, filename)
            
            # Save main response file
            try:
                with open(filepath, "wb") as f:
                    f.write(r["body"])
            except Exception as e:
                print(f"Error saving response file {filename}: {e}", flush=True)
            
            # Save metadata file
            metadata_path = filepath + ".meta"
            try:
                with open(metadata_path, "w", encoding="utf-8") as f:
                    f.write(f"URL: {r['url']}\n")
                    f.write(f"Status: {r['status']}\n")
                    f.write(f"Resource Type: {r['resource_type']}\n")
                    f.write(f"Content Type: {r['content_type']}\n")
                    f.write(f"Has Search Text: {r['has_text']}\n")
                    f.write(f"Is JSON: {r['is_json']}\n")
                    f.write(f"Is API: {r['is_api']}\n")
            except Exception as e:
                print(f"Error saving metadata file {filename}.meta: {e}", flush=True)
        print(f"Saved all responses to {responses_dir}/", flush=True)

        print(f"Scanned responses for: {url_to_open}")
        if search_text_str:
            print(f"Search text: {search_text_str}")
        print()

        print("=== ALL REQUESTS ===")
        for r in responses:
            print(f"{r['status']} {r['resource_type']:10} {r['url']}")

        print()
        print("=== RESPONSES CONTAINING THE TEXT ===")
        for r in responses:
            if r["has_text"]:
                print(f"{r['status']} {r['resource_type']:10} {r['url']}")
        
        print()
        print("=== API/JSON ENDPOINTS ===")
        for r in responses:
            if r["is_api"] or r["is_json"]:
                print(f"{r['status']} {r['resource_type']:10} {r['content_type']:30} {r['url']}")
                if r["has_text"]:
                    print(f"  -> Contains search text!")
                    try:
                        preview = r["body_preview"].decode('utf-8', errors='ignore')
                        print(f"  -> Preview: {preview[:150]}...")
                    except:
                        pass

        browser.close()

if __name__ == "__main__":
    main()
