#!/usr/bin/env python3
import requests
import json
from pathlib import Path

BASE_URL = 'http://localhost:8080'

def test_api_endpoints():
    print("Testing Frontend API Endpoints")
    print("=" * 50)
    
    # Test 1: RSS Feed endpoint
    print("\n1. Testing RSS Feed endpoint...")
    try:
        response = requests.get(f'{BASE_URL}/api/rss-feed')
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ RSS Feed loaded successfully")
            print(f"   - Feed title: {data.get('feed_metadata', {}).get('title', 'N/A')}")
            print(f"   - Items count: {len(data.get('items', []))}")
            if data.get('items'):
                print(f"   - First article: {data['items'][0].get('title', 'N/A')[:60]}...")
        else:
            print(f"   ✗ Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 2: Authentication endpoint
    print("\n2. Testing Authentication endpoint...")
    try:
        response = requests.post(
            f'{BASE_URL}/api/authenticate',
            json={'username': 'testuser', 'password': 'Hello world!'}
        )
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ Authentication successful")
            print(f"   - Username: {data.get('username', 'N/A')}")
            print(f"   - Token received: {bool(data.get('token'))}")
        else:
            print(f"   ✗ Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 3: Check if article exists
    print("\n3. Testing Article endpoint...")
    try:
        # First get RSS feed to find an article
        rss_response = requests.get(f'{BASE_URL}/api/rss-feed')
        if rss_response.status_code == 200:
            rss_data = rss_response.json()
            if rss_data.get('items'):
                shortcode = rss_data['items'][0].get('shortcode')
                if shortcode:
                    print(f"   Testing with article: {shortcode}")
                    
                    # Check if article exists
                    head_response = requests.head(f'{BASE_URL}/api/article/{shortcode}/fi')
                    if head_response.status_code == 200:
                        print(f"   ✓ Article exists in cache")
                        
                        # Get article content
                        article_response = requests.get(f'{BASE_URL}/api/article/{shortcode}/fi')
                        if article_response.status_code == 200:
                            article_data = article_response.json()
                            print(f"   ✓ Article content loaded")
                            print(f"   - Title: {article_data.get('title', 'N/A')[:60]}...")
                            print(f"   - Paragraphs: {len(article_data.get('paragraphs', []))}")
                    else:
                        print(f"   ⚠ Article not found in cache (status: {head_response.status_code})")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 4: Check static files
    print("\n4. Testing static files...")
    files_to_check = ['index.html', 'articles.html', 'article.html', 'styles.css', 'config.js', 'auth.js', 'api.js', 'app.js']
    for filename in files_to_check:
        try:
            response = requests.get(f'{BASE_URL}/{filename}')
            if response.status_code == 200:
                print(f"   ✓ {filename} - {len(response.content)} bytes")
            else:
                print(f"   ✗ {filename} - Status: {response.status_code}")
        except Exception as e:
            print(f"   ✗ {filename} - Error: {e}")
    
    print("\n" + "=" * 50)
    print("API Testing Complete!")
    print("=" * 50)

def check_cached_data():
    print("\n\nChecking Cached Data")
    print("=" * 50)
    
    local_storage = Path(__file__).parent.parent.parent / 'local-dev' / 'storage'
    
    # Check RSS feed
    rss_path = local_storage / 'cache' / 'yle' / 'paauutiset.json'
    if rss_path.exists():
        with open(rss_path, 'r', encoding='utf-8') as f:
            rss_data = json.load(f)
        print(f"\n✓ RSS Feed found:")
        print(f"  - Title: {rss_data.get('feed_metadata', {}).get('title', 'N/A')}")
        print(f"  - Items: {len(rss_data.get('items', []))}")
    else:
        print(f"\n✗ RSS Feed not found at {rss_path}")
    
    # Check articles
    articles_dir = local_storage / 'cache' / 'yle' / 'articles'
    if articles_dir.exists():
        articles = list(articles_dir.glob('*.json'))
        print(f"\n✓ Articles found: {len(articles)}")
        for article in articles[:5]:
            print(f"  - {article.name}")
    else:
        print(f"\n✗ Articles directory not found at {articles_dir}")

if __name__ == '__main__':
    test_api_endpoints()
    check_cached_data()
