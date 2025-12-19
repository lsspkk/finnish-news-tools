#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright
import json

async def test_frontend():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        print("Testing frontend...")
        
        # Test 1: Navigate to login page
        print("\n1. Navigating to login page...")
        await page.goto('http://localhost:8080/index.html')
        await page.wait_for_load_state('networkidle')
        print("   ✓ Login page loaded")
        
        # Test 2: Check if already authenticated redirects
        print("\n2. Checking authentication state...")
        title = await page.title()
        print(f"   Page title: {title}")
        
        # Test 3: Login
        print("\n3. Attempting login...")
        await page.fill('#username', 'testuser')
        await page.fill('#password', 'Hello world!')
        await page.click('button[type="submit"]')
        
        # Wait for redirect to articles page
        await page.wait_for_url('**/articles.html', timeout=5000)
        print("   ✓ Login successful, redirected to articles page")
        
        # Test 4: Check articles page
        print("\n4. Checking articles page...")
        await page.wait_for_load_state('networkidle')
        
        # Check if username is displayed
        username_element = await page.query_selector('.username')
        if username_element:
            username_text = await username_element.text_content()
            print(f"   ✓ Username displayed: {username_text}")
        
        # Check if feed info is displayed
        feed_info = await page.query_selector('#feedInfo')
        if feed_info:
            feed_text = await feed_info.text_content()
            print(f"   Feed info: {feed_text[:100]}...")
        
        # Check if articles are listed
        article_list = await page.query_selector('#articleList')
        if article_list:
            articles = await article_list.query_selector_all('.article-item')
            print(f"   ✓ Found {len(articles)} articles")
            
            if len(articles) > 0:
                # Get first article title
                first_article = articles[0]
                title_element = await first_article.query_selector('.article-title')
                if title_element:
                    article_title = await title_element.text_content()
                    print(f"   First article: {article_title[:60]}...")
        
        # Test 5: Click on first article
        if len(articles) > 0:
            print("\n5. Clicking on first article...")
            first_link = await articles[0].query_selector('a')
            if first_link:
                await first_link.click()
                await page.wait_for_url('**/article.html**', timeout=5000)
                await page.wait_for_load_state('networkidle')
                print("   ✓ Article page loaded")
                
                # Check article header
                article_header = await page.query_selector('#articleHeader')
                if article_header:
                    header_text = await article_header.text_content()
                    print(f"   Article header loaded: {header_text[:80]}...")
                
                # Test 6: Click "Näytä" button
                print("\n6. Testing 'Näytä' button...")
                nayta_button = await page.query_selector('button:has-text("Näytä")')
                if nayta_button:
                    await nayta_button.click()
                    await asyncio.sleep(1)  # Wait for content to load
                    
                    article_content = await page.query_selector('#articleContent')
                    if article_content:
                        content_classes = await article_content.get_attribute('class')
                        if 'hidden' not in content_classes:
                            content_text = await article_content.text_content()
                            print(f"   ✓ Article content displayed: {len(content_text)} characters")
                            print(f"   First paragraph: {content_text[:100]}...")
                        else:
                            print("   ⚠ Article content is hidden")
                    else:
                        print("   ⚠ Article content element not found")
                else:
                    print("   ⚠ 'Näytä' button not found")
                
                # Test 7: Check language buttons
                print("\n7. Checking language buttons...")
                lang_buttons = await page.query_selector_all('.btn-language')
                print(f"   Found {len(lang_buttons)} language buttons")
                for btn in lang_buttons:
                    btn_text = await btn.text_content()
                    print(f"   - {btn_text}")
        
        # Test 8: Check logout
        print("\n8. Testing logout...")
        logout_button = await page.query_selector('.logout-btn')
        if logout_button:
            await logout_button.click()
            await page.wait_for_url('**/index.html', timeout=5000)
            print("   ✓ Logout successful, redirected to login page")
        
        print("\n" + "="*50)
        print("Frontend test completed!")
        print("="*50)
        
        # Keep browser open for a moment to see results
        await asyncio.sleep(2)
        await browser.close()

if __name__ == '__main__':
    asyncio.run(test_frontend())
