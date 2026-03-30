import os
import json
import time
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") # Updated for 2026 Chrome versions
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Crucial for preventing the 'ReadTimeout' in GitHub Actions
    chrome_options.add_argument("--disable-browser-side-navigation")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)")
    
    chrome_options.binary_location = "/usr/bin/google-chrome"
    service = Service("/usr/bin/chromedriver")
    
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # Increase the timeout limits significantly
    driver.set_page_load_timeout(180) 
    driver.set_script_timeout(180)
    return driver

def scrape_section(url, category):
    driver = get_driver()
    articles = []
    
    try:
        driver.get(url)
        time.sleep(10)
        
        elements = driver.find_elements(By.CSS_SELECTOR, "h3[class*='title'] a")
        links = list(set([el.get_attribute("href") for el in elements if "/article" in el.get_attribute("href")]))

        for link in links[:12]:
            try:
                # Add a timeout catch for individual articles so one slow page doesn't kill the whole run
                driver.get(link)
                
                # Execute stop to prevent infinite ad-loading loops
                driver.execute_script("window.stop();")
                
                # Immediate Paywall/Overlay Removal
                driver.execute_script("""
                    var paywall = document.getElementById('arthardpv');
                    if (paywall) paywall.remove();
                    var ads = document.querySelectorAll('.article-ad, .dfp-ad, .articleblock-container');
                    ads.forEach(ad => ad.remove());
                """)
                
                time.sleep(3)

                # Targeting the schemaDiv as per your provided HTML structure
                body_container = driver.find_element(By.CSS_SELECTOR, 'div.schemaDiv[itemprop="articleBody"]')
                content_elements = body_container.find_elements(By.CSS_SELECTOR, "p, h4.sub_head")
                
                article_content = []
                for el in content_elements:
                    text = el.text.strip()
                    tag = el.tag_name
                    
                    if not text or any(x in text for x in ["Related Stories", "mukunth.v@", "| Photo Credit:"]):
                        continue
                    
                    article_content.append({
                        "type": "heading" if tag == "h4" else "text",
                        "value": text
                    })

                title = driver.find_element(By.CSS_SELECTOR, "h1.title").text.strip()
                
                try:
                    img_el = driver.find_element(By.CSS_SELECTOR, 'div.article-picture img, [itemprop="articleBody"] img')
                    img_url = img_el.get_attribute("data-src-template") or img_el.get_attribute("src")
                except: img_url = None

                if len(article_content) > 1:
                    articles.append({
                        "category": category,
                        "title": title,
                        "url": link,
                        "image": img_url,
                        "content": article_content,
                        "date": datetime.now().strftime("%Y-%m-%d")
                    })
            except Exception as e:
                print(f"Skipping article {link} due to timeout: {e}")
                continue
    finally:
        driver.quit() # Always quit to free up RAM in GitHub Actions
    return articles

targets = {
    "Science": "https://www.thehindu.com/sci-tech/science/",
    "Health": "https://www.thehindu.com/sci-tech/health/",
    "Agriculture": "https://www.thehindu.com/sci-tech/agriculture/",
    "Environment": "https://www.thehindu.com/sci-tech/energy-and-environment/",
    "Internet": "https://www.thehindu.com/sci-tech/technology/internet/"
}

data_file = "data.json"
if os.path.exists(data_file):
    with open(data_file, "r", encoding='utf-8') as f:
        full_db = json.load(f)
else:
    full_db = []

for cat, url in targets.items():
    print(f"Scraping {cat}...")
    new_arts = scrape_section(url, cat)
    
    existing_urls = [a['url'] for a in full_db]
    for art in new_arts:
        if art['url'] not in existing_urls:
            full_db.insert(0, art)

with open(data_file, "w", encoding='utf-8') as f:
    json.dump(full_db[:500], f, ensure_ascii=False, indent=4)
