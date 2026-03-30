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

        for link in links[:12]: 
            try:
                driver.get(link)
                # Wait for the main container to exist
                time.sleep(5) 
                
                title = driver.find_element("css selector", "h1.title").text.strip()
                
                # Image Scraper
                try:
                    img_el = driver.find_element("css selector", 'div.article-picture img, [itemprop="articleBody"] img')
                    img_url = img_el.get_attribute("data-src-template") or img_el.get_attribute("src")
                except: img_url = None

                # --- FIX: ROBUST CONTENT EXTRACTION VIA JAVASCRIPT ---
                # This script pulls all text/headings inside the body container 
                # before the paywall can strip the DOM.
                js_script = """
                let container = document.querySelector('[itemprop="articleBody"]');
                if (!container) return [];
                let items = container.querySelectorAll('p, h4.sub_head');
                return Array.from(items).map(el => ({
                    type: el.tagName.toLowerCase() === 'p' ? 'text' : 'heading',
                    value: el.innerText.trim()
                }));
                """
                raw_content = driver.execute_script(js_script)
                
                article_content = []
                for item in raw_content:
                    val = item['value']
                    # Preferences: Filter Photo Credits and empty strings
                    if val and "| Photo Credit:" not in val and "mukunth.v@" not in val and "Related Stories" not in val:
                        article_content.append(item)

                articles.append({
                    "category": category,
                    "title": title,
                    "url": link,
                    "image": img_url,
                    "content": article_content,
                    "date": datetime.now().strftime("%Y-%m-%d")
                })
            except Exception as e: 
                print(f"Error scraping {link}: {e}")
                continue
    finally:
        driver.quit()
    return articles

# --- BATCH TARGETS ---
targets = {
    "Science": "https://www.thehindu.com/sci-tech/science/",
    "Health": "https://www.thehindu.com/sci-tech/health/",
    "Agriculture": "https://www.thehindu.com/sci-tech/agriculture/",
    "Environment": "https://www.thehindu.com/sci-tech/energy-and-environment/",
    "Internet": "https://www.thehindu.com/sci-tech/technology/internet/"
}

data_file = "data.json"
if os.path.exists(data_file):
    with open(data_file, "r") as f:
        try: full_db = json.load(f)
        except: full_db = []
else:
    full_db = []

for cat, url in targets.items():
    print(f"Scraping {cat}...")
    new_articles = scrape_section(url, cat)
    existing_urls = [a['url'] for a in full_db]
    for art in new_articles:
        if art['url'] not in existing_urls:
            full_db.insert(0, art)

with open(data_file, "w", encoding='utf-8') as f:
    json.dump(full_db[:500], f, ensure_ascii=False, indent=4)
