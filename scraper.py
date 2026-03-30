import os
import json
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

def scrape_section(url, category):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.binary_location = "/usr/bin/google-chrome"
    
    service = Service("/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    articles = []
    try:
        driver.get(url)
        time.sleep(8)
        
        elements = driver.find_elements("css selector", "h3[class*='title'] a")
        links = list(set([el.get_attribute("href") for el in elements if "/article" in el.get_attribute("href")]))

        for link in links[:10]:
            try:
                driver.get(link)
                time.sleep(4)
                
                title = driver.find_element("css selector", "h1.title").text.strip()
                
                # Image Scraper
                try:
                    img_el = driver.find_element("css selector", 'div.article-picture img, [itemprop="articleBody"] img')
                    img_url = img_el.get_attribute("data-src-template") or img_el.get_attribute("src")
                except: img_url = None

                # --- NEW SELECTOR LOGIC ---
                # We target the specific itemprop container
                body_container = driver.find_element("css selector", '[itemprop="articleBody"]')
                
                # We grab only p, h1, h2, h3, h4 tags that are DIRECT children or 
                # inside the schemaDiv, effectively skipping the ad divs.
                text_elements = body_container.find_elements("css selector", "p, h1, h2, h3, h4")
                
                article_content = []
                for el in text_elements:
                    tag = el.tag_name
                    text = el.text.strip()
                    
                    # 1. Skip empty tags
                    # 2. Skip the "Related Stories" title and lines
                    # 3. Skip the specific Photo Credit lines from your preferences
                    if not text or "Related Stories" in text or "mukunth.v@" in text:
                        continue
                    if "| Photo Credit:" in text:
                        continue
                    
                    # Determine type for the frontend
                    # 'heading' for sub_heads, 'text' for paragraphs
                    el_type = "heading" if tag.startswith("h") else "text"
                    
                    article_content.append({
                        "type": el_type,
                        "value": text
                    })

                articles.append({
                    "category": category,
                    "title": title,
                    "url": link,
                    "image": img_url,
                    "content": article_content,
                    "date": datetime.now().strftime("%Y-%m-%d")
                })
            except: continue
    finally:
        driver.quit()
    return articles

# (Rest of your batch target and save logic remains the same)
